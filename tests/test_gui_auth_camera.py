import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import camera, gui_auth
from app import system_info


WEB_DIR = Path(__file__).resolve().parents[1] / "web"


def test_manufacturer_model_previews_are_local_and_model_specific():
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    camera_js = (WEB_DIR / "device_extensions.js").read_text(encoding="utf-8")
    expected = {
        "mars-hydro-fc3000.webp": "fc[- _]?3000",
        "mars-hydro-df150-m.webp": "df[- _]?150",
        "logitech-c920.webp": "c920",
        "fritz-dect-210.webp": "210",
    }
    for filename, model_token in expected.items():
        image = WEB_DIR / "device-images" / filename
        assert image.is_file()
        assert image.stat().st_size < 100_000
        assert filename in app_js or filename in camera_js
        assert model_token in app_js
    assert "MODELL NOCH NICHT EINDEUTIG" in app_js
    assert "https://" not in app_js


def test_manufacturer_image_sources_are_documented():
    sources = (WEB_DIR / "device-images" / "SOURCES.md").read_text(encoding="utf-8")
    for domain in ("mars-hydro.com", "logitech.com", "avm.de"):
        assert domain in sources


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


def test_camera_mjpeg_modes_exclude_uncompressed_formats():
    output = """
        [0]: 'MJPG' (Motion-JPEG, compressed)
            Size: Discrete 640x480
                Interval: Discrete 0.033s (30.000 fps)
                Interval: Discrete 0.100s (10.000 fps)
            Size: Discrete 1920x1080
                Interval: Discrete 0.200s (5.000 fps)
        [1]: 'YUYV' (YUYV 4:2:2)
            Size: Discrete 320x240
                Interval: Discrete 0.033s (30.000 fps)
    """
    assert camera._parse_mjpeg_modes(output) == [
        {"width": 640, "height": 480, "fps": [10.0, 30.0], "label": "640 × 480"},
        {"width": 1920, "height": 1080, "fps": [5.0], "label": "1920 × 1080"},
    ]


def test_camera_capture_mode_is_advertised_and_pi_friendly(monkeypatch):
    devices = [{
        "id": "cam0", "device": "/dev/video0",
        "mjpeg_modes": [
            {"width": 640, "height": 480, "fps": [5.0, 10.0, 30.0], "label": "640 × 480"},
            {"width": 1920, "height": 1080, "fps": [5.0, 30.0], "label": "1920 × 1080"},
        ],
    }]
    monkeypatch.setattr(camera, "_discover_devices_sync", lambda: (devices, 0))
    _, _, default_mode = camera._resolve_capture_mode("cam0", None, None)
    assert (default_mode["width"], default_mode["height"], default_mode["selected_fps"]) == (640, 480, 10.0)
    _, _, full_hd = camera._resolve_capture_mode("cam0", 1920, 1080)
    assert full_hd["selected_fps"] == 5.0
    with pytest.raises(ValueError):
        camera._resolve_capture_mode("cam0", 1280, 720)


def test_manual_focus_disables_autofocus_and_reads_back(monkeypatch):
    calls = []
    states = [
        {"camera_id": "cam0", "device": "/dev/video0", "controls": [
            {"name": "focus_auto", "writable": True, "value": 1, "menu": []},
            {"name": "focus_absolute", "writable": False, "value": 0, "min": 0, "max": 250, "step": 5, "menu": []},
        ]},
        {"camera_id": "cam0", "device": "/dev/video0", "controls": [
            {"name": "focus_auto", "writable": True, "value": 0, "menu": []},
            {"name": "focus_absolute", "writable": True, "value": 0, "min": 0, "max": 250, "step": 5, "menu": []},
        ]},
        {"camera_id": "cam0", "device": "/dev/video0", "controls": [
            {"name": "focus_absolute", "writable": True, "value": 125, "min": 0, "max": 250, "step": 5, "menu": []},
        ]},
    ]
    monkeypatch.setattr(camera, "_controls_sync", lambda _camera_id: states.pop(0))
    monkeypatch.setattr(camera, "_run", lambda args, **_kwargs: (calls.append(args) or SimpleNamespace(returncode=0, stdout=b"", stderr=b"")))
    result = camera._set_control_sync(camera.CameraControlRequest(camera_id="cam0", control="focus_absolute", value=125))
    assert calls[-2][-1] == "focus_auto=0"
    assert calls[-1][-1] == "focus_absolute=125"
    assert result["auto_focus_disabled"] is True
    assert result["control"]["value"] == 125


def test_system_interface_parser_exposes_ipv4_and_ipv6():
    rows = system_info._parse_interfaces('[{"ifname":"eth0","operstate":"UP","address":"dc:a6:32:00:00:01","mtu":1500,"addr_info":[{"family":"inet","local":"192.168.178.65","prefixlen":24,"scope":"global"},{"family":"inet6","local":"fe80::1","prefixlen":64,"scope":"link"}]}]')
    assert rows[0]["name"] == "eth0"
    assert [row["family"] for row in rows[0]["addresses"]] == ["IPv4", "IPv6"]
    assert rows[0]["addresses"][0]["address"] == "192.168.178.65"


def test_entrypoint_exposes_camera_and_login_sources():
    entrypoint = (__import__("pathlib").Path(__file__).parents[1] / "app" / "entrypoint.py").read_text(encoding="utf-8")
    assert "GuiAuthMiddleware" in entrypoint
    assert "camera_router" in entrypoint
    assert "include_router(camera_router)" in entrypoint


def test_build65_gui_groups_system_data_and_compacts_camera():
    page = (__import__("pathlib").Path(__file__).parents[1] / "web" / "index.html").read_text(encoding="utf-8")
    assert 'data-view="network"' not in page
    assert page.index('id="system"') < page.index('id="networkStatus"')
    assert page.index('id="devices"') < page.index('id="fritzPresence"') < page.index('id="camera"')
    assert 'id="dashboardPrimaryIp"' in page
    assert 'id="dashboardHostInterfaces"' in page
    assert 'id="cameraResolutionSelect"' in page
    assert 'class="camera-command-pad"' in page


def test_build66_gui_shows_complete_fritz_identity_and_temperature():
    script = (__import__("pathlib").Path(__file__).parents[1] / "web" / "app.js").read_text(encoding="utf-8")
    for label in ("UMGEBUNG", "Modell", "AIN", "Firmware", "Funktionsbitmaske", "Gerätesperre"):
        assert label in script
    assert "temperature_c" in script
    assert "temperature_offset_c" in script
    assert "Strom${s.current_source?\" (berechnet)\"" in script


def test_build69_gui_uses_encrypted_reusable_fritz_login_and_two_decimals():
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    extensions = (WEB_DIR / "device_extensions.js").read_text(encoding="utf-8")
    assert "lokal verschlüsselt gespeichert" in page
    assert 'id="fritzManualBtn"' in page
    assert 'id="fritzChangeBtn"' in page
    assert 'id="fritzDeleteBtn"' in page
    assert 'id="registeredDeviceList"' in page
    assert 'id="plugTemperatureGrid"' in page
    assert 'id="automationCreateForm"' in page
    assert "toFixed(2)" in script
    assert "gcManualFritzDevices" in script
    assert "/onboarding/fritz/credentials" in extensions
    assert "/api/v1/smarthome/devices" in extensions
    assert "Anmeldung geprüft und verschlüsselt gespeichert" in extensions
    assert "Passwort" in extensions


def test_build68_camera_and_product_previews_are_compact():
    app_css = (WEB_DIR / "app.css").read_text(encoding="utf-8")
    camera_css = (WEB_DIR / "device_extensions.css").read_text(encoding="utf-8")
    assert ".device-preview{width:96px;height:68px" in app_css
    assert ".camera-layout{display:grid;grid-template-columns:118px" in camera_css
    assert ".camera-device{min-height:84px" in camera_css


def test_build70_gui_keeps_off_plug_costs_and_checks_pi_on_navigation():
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    extensions = (WEB_DIR / "device_extensions.js").read_text(encoding="utf-8")
    assert 'id="powerSummaryCost"' in page
    assert "Kosten gesamt" in script
    assert 'id="piOfflineOverlay"' in page
    assert "/api/health?live=" in script
    assert "refreshAll(true)" in script
    assert "/onboarding/tapo/login" in extensions
    assert "/onboarding/tapo/credentials" in extensions
    assert "Raum nicht vom Gerät gemeldet" in extensions


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
