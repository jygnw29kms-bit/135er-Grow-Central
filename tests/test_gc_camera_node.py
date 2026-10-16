from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import app.devices.gc_esp32 as gc_esp32
from app.devices.catalog import provider_by_id
from app.devices.gc_esp32_protocol import parse_announcement
from app.devices.models import Capability, DeviceClass


def test_native_esp32_provider_advertises_camera_support():
    provider = provider_by_id("growcentral_esp32")
    assert provider is not None
    assert DeviceClass.CAMERA in provider.device_classes
    assert Capability.SNAPSHOT in provider.capabilities
    assert Capability.STREAM in provider.capabilities


def test_camera_announcement_is_valid_native_gc_protocol():
    announce = parse_announcement(
        json.dumps(
            {
                "schema": "gc-device-v1",
                "protocol": "gc-esp32-mqtt-v1",
                "id": "gc-cam-a1b2c3",
                "name": "135er-GC-Cam",
                "device_class": "camera",
                "model": "GC-CAM-AI-THINKER-ESP32",
                "firmware": "0.1.0",
                "hardware_uid": "0011223344556677",
                "capabilities": ["snapshot", "stream"],
            }
        )
    )
    assert announce.device_class is DeviceClass.CAMERA
    assert announce.name == "135er-GC-Cam"
    assert announce.capabilities == (Capability.SNAPSHOT, Capability.STREAM)


def test_camera_state_never_requires_soil_calibration(monkeypatch):
    class Trust:
        def require_trusted(self, native_id):
            assert native_id == "gc-cam-a1b2c3"
            return {
                "fingerprint": "abc",
                "metadata": {"capabilities": ["snapshot", "stream"]},
            }

        def receive(self, message):
            return None

    class Calibration:
        def require_valid(self, *args, **kwargs):
            raise AssertionError("camera state must not enter soil calibration")

    monkeypatch.setattr(gc_esp32, "TrustStore", lambda: Trust())
    monkeypatch.setattr(gc_esp32, "CalibrationStore", lambda: Calibration())
    provider = gc_esp32.GrowCentralEsp32Provider()

    async def prove_identity(native_id):
        assert native_id == "gc-cam-a1b2c3"
        return SimpleNamespace(
            public_key="public-key",
            body={
                "hardware_uid": "0011223344556677",
                "state": {
                    "snapshot": "http://192.0.2.40/snapshot.jpg?token=abc",
                    "stream": "http://192.0.2.40/stream.mjpeg?token=abc",
                    "meta": {
                        "hostname": "135er-gc-cam",
                        "ip": "192.0.2.40",
                        "camera_ready": True,
                        "sd_ready": True,
                        "sd_total_mb": 30436,
                        "sd_free_mb": 30300,
                        "resolution": "800x600",
                        "rssi_dbm": -48,
                        "firmware": "0.1.0",
                        "not_allowed": "drop-me",
                    },
                },
            },
        )

    monkeypatch.setattr(provider, "prove_identity", prove_identity)
    state = asyncio.run(provider.state("gc-cam-a1b2c3"))

    assert state["snapshot"].startswith("http://192.0.2.40/")
    assert state["stream"].startswith("http://192.0.2.40/")
    assert state["online"] is True
    assert state["meta"]["hostname"] == "135er-gc-cam"
    assert state["meta"]["camera_ready"] is True
    assert state["meta"]["sd_ready"] is True
    assert "calibration_status" not in state["meta"]
    assert "not_allowed" not in state["meta"]
