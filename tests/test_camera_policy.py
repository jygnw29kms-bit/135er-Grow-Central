from types import SimpleNamespace

import pytest

from app import camera


def test_camera_policy_allows_full_support_1080p():
    sample = """
[0]: 'MJPG'
    Size: Discrete 640x480
        Interval: Discrete 0.033s (30.000 fps)
    Size: Discrete 1280x720
        Interval: Discrete 0.033s (30.000 fps)
    Size: Discrete 1920x1080
        Interval: Discrete 0.033s (30.000 fps)
"""
    modes = camera._parse_mjpeg_modes(sample)
    assert {(row["width"], row["height"]) for row in modes} == {(640, 480), (1280, 720), (1920, 1080)}


def test_camera_policy_allows_direct_1080p_on_full_support(monkeypatch):
    devices=[{"id":"cam0","device":"/dev/video0","mjpeg_modes":[{"width":1920,"height":1080,"fps":[30.0],"label":"1920 × 1080"}]}]
    monkeypatch.setattr(camera,"_discover_devices_sync",lambda:(devices,0))
    _,_,mode=camera._resolve_capture_mode("cam0",1920,1080)
    assert (mode["width"],mode["height"])==(1920,1080)


def test_camera_policy_is_installed_once():
    assert getattr(camera, "_GC_POLICY_INSTALLED", False) is True
