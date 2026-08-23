from types import SimpleNamespace

import pytest

from app import camera


def test_camera_policy_limits_modes_to_720p():
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
    assert {(row["width"], row["height"]) for row in modes} == {(640, 480), (1280, 720)}


def test_camera_policy_rejects_direct_over_720p_request(monkeypatch):
    # The policy must reject an oversized direct URL request before consulting
    # the physical camera/cache.
    with pytest.raises(ValueError, match="1280x720"):
        camera._resolve_capture_mode("cam0", 1920, 1080)


def test_camera_policy_is_installed_once():
    assert getattr(camera, "_GC_POLICY_INSTALLED", False) is True
