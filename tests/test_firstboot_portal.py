import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

APPLY_PATH = Path(__file__).parents[1] / "image-builder" / "firstboot" / "apply_setup.py"
SETUP_AP_PATH = Path(__file__).parents[1] / "image-builder" / "firstboot" / "setup-ap.sh"
IMAGE_WORKFLOW_PATH = Path(__file__).parents[1] / ".github" / "workflows" / "build-pi3-image.yml"

import importlib.util
APPLY_SPEC = importlib.util.spec_from_file_location("firstboot_apply", APPLY_PATH)
apply_setup = importlib.util.module_from_spec(APPLY_SPEC)
assert APPLY_SPEC and APPLY_SPEC.loader
APPLY_SPEC.loader.exec_module(apply_setup)


def valid_form():
    return {
        "mode": "wifi",
        "hostname": "grow-central",
        "timezone": "Europe/Berlin",
        "ssid": "Werkstatt WLAN",
        "wifi_password": "sicheres-wlan-passwort",
        "new_password": "ein-neues-systempasswort",
        "new_password_confirm": "ein-neues-systempasswort",
        "gui_username": "GrowCentral",
        "gui_password": "ein-neues-gui-passwort",
        "gui_password_confirm": "ein-neues-gui-passwort",
        "fritz_enabled": "0",
    }


def test_setup_ap_exposes_always_on_gui_for_firstboot():
    script = SETUP_AP_PATH.read_text(encoding="utf-8")
    assert 'deny from "$SETUP_SUBNET" to any port 8080 proto tcp' not in script
    assert "ipv4.shared-dhcp-range 10.42.0.10,10.42.0.250" in script
    assert "ipv4.method shared" in script


def test_runtime_password_hash_does_not_store_plaintext():
    password = "ein-neues-gui-passwort"
    encoded = apply_setup._gui_hash(password)
    assert encoded.startswith("pbkdf2_sha256$")
    assert password not in encoded


def test_apply_revalidates_gui_and_fritz_fields(monkeypatch):
    config = valid_form()
    apply_setup.validate(config)
    config["gui_username"] = "ungültig mit leerzeichen"
    with __import__("pytest").raises(ValueError):
        apply_setup.validate(config)


def test_wifi_password_is_not_exposed_in_process_arguments(monkeypatch):
    calls = []

    def fake_run(*arguments, **_kwargs):
        calls.append(arguments)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    real_mkstemp = tempfile.mkstemp

    def temporary_runtime_file(*_args, **_kwargs):
        return real_mkstemp(prefix="grow-central-test-", dir="/tmp", text=True)

    config = valid_form()
    with patch.object(apply_setup, "run", fake_run), patch.object(apply_setup.tempfile, "mkstemp", temporary_runtime_file):
        apply_setup.configure_wifi(config)

    flattened = [str(argument) for call in calls for argument in call]
    assert config["wifi_password"] not in flattened
    assert "--passwd-file" in flattened


def test_image_workflow_is_synchronized_to_alpha_075():
    workflow = IMAGE_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "alpha-0.7.5-build-" in workflow
    assert '.version == "0.7.5"' in workflow
    assert "app.entrypoint:app" in workflow
    assert "polkitd" in workflow
    assert "v4l2-ctl" in workflow
    assert "ffmpeg" in workflow
    assert "SupplementaryGroups=systemd-journal video netdev" in workflow
    assert "grow-central-apply-setup.path" in workflow
    assert "grow-central-setup-ap.service" in workflow


def test_setup_file_is_deleted_only_after_runtime_health_check():
    source = APPLY_PATH.read_text(encoding="utf-8")
    assert source.index('http://127.0.0.1:8080/api/health') < source.index("SETUP_FILE.unlink()")
    assert source.index("mark_provisioned()") < source.index("SETUP_FILE.unlink()")
