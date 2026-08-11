import importlib.util
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PORTAL_PATH = Path(__file__).parents[1] / "image-builder" / "firstboot" / "portal.py"
APPLY_PATH = Path(__file__).parents[1] / "image-builder" / "firstboot" / "apply_setup.py"
SPEC = importlib.util.spec_from_file_location("firstboot_portal", PORTAL_PATH)
portal = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = portal
SPEC.loader.exec_module(portal)
APPLY_SPEC = importlib.util.spec_from_file_location("firstboot_apply", APPLY_PATH)
apply_setup = importlib.util.module_from_spec(APPLY_SPEC)
assert APPLY_SPEC and APPLY_SPEC.loader
sys.modules[APPLY_SPEC.name] = apply_setup
APPLY_SPEC.loader.exec_module(apply_setup)


def valid_form():
    return {
        "mode": "wifi",
        "hostname": "grow-central",
        "timezone": "Europe/Berlin",
        "ssid": "Werkstatt WLAN",
        "wifi_password": "sicheres-wlan-passwort",
        "new_password": "ein-neues-passwort",
        "new_password_confirm": "ein-neues-passwort",
    }


def test_valid_setup_is_normalized():
    config, error = portal.validate_setup(valid_form())
    assert error is None
    assert config["hostname"] == "grow-central"
    assert "new_password_confirm" not in config


def test_invalid_hostname_is_rejected():
    form = valid_form()
    form["hostname"] = "grow central; reboot"
    config, error = portal.validate_setup(form)
    assert config is None
    assert "Hostname" in error


def test_short_password_is_rejected():
    form = valid_form()
    form["new_password"] = form["new_password_confirm"] = "kurz"
    config, error = portal.validate_setup(form)
    assert config is None
    assert "12 Zeichen" in error


def test_login_guard_limits_attempts_and_recovers():
    guard = portal.LoginGuard()
    for offset in range(5):
        guard.failed("10.42.0.2", now=float(offset))
    assert not guard.allowed("10.42.0.2", now=5.0)
    assert guard.allowed("10.42.0.2", now=65.0)


def test_apply_stage_revalidates_untrusted_data():
    config, error = portal.validate_setup(valid_form())
    assert error is None
    apply_setup.validate(config)
    config["timezone"] = "Europe/Berlin; reboot"
    try:
        apply_setup.validate(config)
    except ValueError:
        pass
    else:
        raise AssertionError("apply stage accepted an unsafe timezone")


def test_wifi_password_is_not_exposed_in_process_arguments():
    calls = []

    def fake_run(*arguments, **_kwargs):
        calls.append(arguments)
        return SimpleNamespace(returncode=0)

    real_mkstemp = tempfile.mkstemp

    def temporary_runtime_file(*_args, **_kwargs):
        return real_mkstemp(prefix="grow-central-test-", dir="/tmp", text=True)

    config, error = portal.validate_setup(valid_form())
    assert error is None
    with patch.object(apply_setup, "run", fake_run), patch.object(apply_setup.tempfile, "mkstemp", temporary_runtime_file):
        apply_setup.configure_wifi(config)

    flattened = [str(argument) for call in calls for argument in call]
    assert config["wifi_password"] not in flattened
    assert "--passwd-file" in flattened
