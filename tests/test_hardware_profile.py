from shared.hardware_profile import (
    FULL_PERFORMANCE,
    FULL_STANDARD,
    LEGACY_LITE,
    UNKNOWN,
    classify_model,
)


def test_pi3_is_legacy_lite():
    assert classify_model("Raspberry Pi 3 Model B Rev 1.2") == LEGACY_LITE
    assert classify_model("Raspberry Pi 3 Model B Plus Rev 1.3") == LEGACY_LITE


def test_pi4_and_400_are_full_support():
    assert classify_model("Raspberry Pi 4 Model B Rev 1.5") == FULL_STANDARD
    assert classify_model("Raspberry Pi 400 Rev 1.0") == FULL_STANDARD


def test_pi5_is_performance_full_support():
    assert classify_model("Raspberry Pi 5 Model B Rev 1.0") == FULL_PERFORMANCE


def test_compute_modules_follow_generation():
    assert classify_model("Raspberry Pi Compute Module 4 Rev 1.1") == FULL_STANDARD
    assert classify_model("Raspberry Pi Compute Module 5 Rev 1.0") == FULL_PERFORMANCE


def test_unknown_hardware_fails_conservatively():
    assert classify_model("Generic ARM64 board") == UNKNOWN


def test_legacy_profile_is_intentionally_limited():
    assert not LEGACY_LITE.full_support
    assert LEGACY_LITE.camera_max_width == 1280
    assert LEGACY_LITE.camera_max_height == 720
    assert LEGACY_LITE.camera_max_fps == 15
    assert LEGACY_LITE.worker_profile == "conservative"


def test_full_profiles_are_not_constrained_by_pi3():
    assert FULL_STANDARD.full_support
    assert FULL_PERFORMANCE.full_support
    assert FULL_STANDARD.camera_max_width >= 1920
    assert FULL_STANDARD.camera_max_height >= 1080
    assert FULL_STANDARD.camera_max_fps >= 30
    assert FULL_PERFORMANCE.worker_profile == "performance"
