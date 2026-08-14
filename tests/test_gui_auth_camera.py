import asyncio
from types import SimpleNamespace

import pytest

from app import camera, gui_auth
from app import system_info


def test_gui_password_hash_roundtrip():
    encoded = gui_auth.hash_password("ein-sehr-sicheres-gui-passwort")
    assert encoded.startswith("pbkdf2_sha256$")
    assert "ein-sehr-sicheres-gui-passwort" not in encoded
    assert gui_auth.verify_password("ein-sehr-sicheres-gui-passwort", encoded)
    assert not gui_auth.verify_password("falsches-passwort", encoded)


def test_camera_control_parser_reads_ranges_and_menus(monkeypatch):
    monkeypatch.setattr(camera, "_resolve_camera", lambda _camera_id: ("cam0", "/dev/video0"))
    output = b"""
                     brightness 0x00980900 (int)    : min=0 max=255 step=1 default=128 value=140
                   power_line_frequency 0x00980918 (menu)   : min=0 max=2 default=1 value=1
                                0: Disabled
                                1: 50 Hz
                                2: 60 Hz
                        focus_auto 0x009a090c (bool)   : default=1 value=1
"""
    monkeypatch.setattr(camera, "_run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=output, stderr=b""))
    result = camera._controls_sync("cam0")
    rows = {row["name"]: row for row in result["controls"]}
    assert rows["brightness"]["min"] == 0
    assert rows["brightness"]["max"] == 255
    assert rows["brightness"]["value"] == 140
    assert rows["power_line_frequency"]["menu"][1] == {"value": 1, "label": "50 Hz"}
    assert rows["focus_auto"]["type"] == "bool"


def test_camera_control_write_rejects_unknown_control(monkeypatch):
    monkeypatch.setattr(camera, "_controls_sync", lambda _camera_id: {"device": "/dev/video0", "controls": []})
    request = camera.CameraControlRequest(camera_id="cam0", control="shell_command", value=1)
    with pytest.raises(ValueError):
        camera._set_control_sync(request)


def test_camera_control_write_checks_range(monkeypatch):
    monkeypatch.setattr(camera, "_controls_sync", lambda _camera_id: {
        "device": "/dev/video0",
        "controls": [{"name": "brightness", "writable": True, "min": 0, "max": 255, "menu": [], "value": 128}],
    })
    request = camera.CameraControlRequest(camera_id="cam0", control="brightness", value=999)
    with pytest.raises(ValueError):
        camera._set_control_sync(request)


def test_entrypoint_exposes_camera_and_login_sources():
    entrypoint = (__import__("pathlib").Path(__file__).parents[1] / "app" / "entrypoint.py").read_text(encoding="utf-8")
    assert "GuiAuthMiddleware" in entrypoint
    assert "camera_router" in entrypoint
    assert "include_router(camera_router)" in entrypoint


def test_system_identity_reads_detected_model_and_build(monkeypatch, tmp_path):
    model = tmp_path / "model"
    model.write_bytes(b"Raspberry Pi 4 Model B Rev 1.4\x00")
    assert system_info._text(model, "fallback") == "Raspberry Pi 4 Model B Rev 1.4"
    missing = tmp_path / "missing"
    assert system_info._text(missing, "fallback") == "fallback"


def test_camera_stream_route_is_exposed():
    paths = (__import__("app.entrypoint", fromlist=["app"]).app.openapi()["paths"])
    assert "/api/v1/camera/stream" in paths
    assert "/api/v1/camera/stream/stop" in paths
    assert "/api/v1/system/info" in paths


def test_camera_discovery_hides_pi_codec_and_metadata_nodes(monkeypatch):
    monkeypatch.setattr(camera, "_DISCOVERY_CACHE", None)
    monkeypatch.setattr(camera, "_candidate_devices", lambda: ["/dev/video0", "/dev/video1", "/dev/video10"])

    rows = {
        "/dev/video0": {"device": "/dev/video0", "capture_capable": True, "stream_capable": True, "readable": True, "bus_info": "usb-1.4", "driver": "uvcvideo", "c920_match": True},
        "/dev/video1": {"device": "/dev/video1", "capture_capable": False, "stream_capable": False, "readable": True, "bus_info": "usb-1.4", "driver": "uvcvideo", "c920_match": True},
        "/dev/video10": {"device": "/dev/video10", "capture_capable": True, "stream_capable": True, "readable": True, "bus_info": "platform:bcm2835-codec", "driver": "bcm2835-codec", "c920_match": False},
    }
    monkeypatch.setattr(camera, "_device_info", lambda _camera_id, device: dict(rows[device]))

    devices, ignored = camera._discover_devices_sync(force=True)
    assert [(row["id"], row["device"]) for row in devices] == [("cam0", "/dev/video0")]
    assert ignored == 2


def test_new_camera_stream_replaces_old_process(monkeypatch):
    class Process:
        def __init__(self):
            self.returncode = None
            self.terminated = False

        def terminate(self):
            self.terminated = True
            self.returncode = 0

        async def wait(self):
            return self.returncode

    async def scenario():
        first_token = object()
        second_token = object()
        first_process = Process()
        await camera._claim_stream(first_token)
        assert await camera._register_stream_process(first_token, first_process)
        await camera._claim_stream(second_token)
        assert first_process.terminated
        assert camera._ACTIVE_STREAM_TOKEN is second_token
        await camera._stop_active_stream("test")

    asyncio.run(scenario())
