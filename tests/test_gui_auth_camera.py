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
    assert "/api/v1/system/info" in paths
