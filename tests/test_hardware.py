from types import SimpleNamespace

from app import hardware


def test_supported_raspberry_pi_profiles():
    cases = {
        "Raspberry Pi 3 Model B Rev 1.2": ("pi3b", "BCM2837", True),
        "Raspberry Pi 3 Model B Plus Rev 1.3": ("pi3b+", "BCM2837B0", True),
        "Raspberry Pi 4 Model B Rev 1.5": ("pi4b", "BCM2711", True),
        "Raspberry Pi 400 Rev 1.0": ("pi400", "BCM2711", True),
        "Raspberry Pi 5 Model B Rev 1.0": ("pi5", "BCM2712", True),
        "Raspberry Pi Compute Module 4 Rev 1.1": ("cm4", "BCM2711", False),
        "Raspberry Pi Compute Module 5 Rev 1.0": ("cm5", "BCM2712", False),
    }
    for model, expected in cases.items():
        result = hardware.classify_model(model + "\x00")
        assert (result["profile"], result["soc"], result["onboard_wifi"]) == expected


def test_wifi_prefers_wlan0_but_falls_back(monkeypatch):
    def fake_run(*_args, **_kwargs):
        return SimpleNamespace(returncode=0, stdout="wlx001122334455:wifi\nwlan0:wifi\nenp1s0:ethernet\n")
    monkeypatch.setattr(hardware.subprocess, "run", fake_run)
    assert hardware.find_interface("wifi", "wlan0") == "wlan0"
    assert hardware.find_interface("ethernet", "eth0") == "enp1s0"


def test_wifi_fallback_when_wlan0_is_absent(monkeypatch):
    monkeypatch.setattr(hardware.subprocess, "run", lambda *_a, **_k: SimpleNamespace(returncode=0, stdout="wlP2p1s0:wifi\n"))
    assert hardware.find_interface("wifi", "wlan0") == "wlP2p1s0"
