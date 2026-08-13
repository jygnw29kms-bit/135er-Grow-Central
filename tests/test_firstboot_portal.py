import importlib.util
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PORTAL_PATH = Path(__file__).parents[1] / "image-builder" / "firstboot" / "portal.py"
APPLY_PATH = Path(__file__).parents[1] / "image-builder" / "firstboot" / "apply_setup.py"
SETUP_AP_PATH = Path(__file__).parents[1] / "image-builder" / "firstboot" / "setup-ap.sh"
IMAGE_WORKFLOW_PATH = Path(__file__).parents[1] / ".github" / "workflows" / "build-pi3-image.yml"

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
        "new_password": "ein-neues-systempasswort",
        "new_password_confirm": "ein-neues-systempasswort",
        "gui_username": "GrowCentral",
        "gui_password": "ein-neues-gui-passwort",
        "gui_password_confirm": "ein-neues-gui-passwort",
        "fritz_enabled": "0",
    }


def test_first_boot_requires_system_and_gui_passwords(monkeypatch):
    monkeypatch.setattr(portal, "ethernet_connected", lambda: False)
    form = valid_form()
    config, error = portal.validate_setup(form)
    assert error is None
    assert config["new_password"] == "ein-neues-systempasswort"
    assert config["gui_username"] == "GrowCentral"
    assert config["gui_password"] == "ein-neues-gui-passwort"

    form["gui_password"] = form["gui_password_confirm"] = "kurz"
    config, error = portal.validate_setup(form)
    assert config is None
    assert "GUI-Passwort" in error


def test_active_lan_skips_wifi_requirement(monkeypatch):
    monkeypatch.setattr(portal, "ethernet_connected", lambda: True)
    form = valid_form()
    form["ssid"] = ""
    form["wifi_password"] = ""
    config, error = portal.validate_setup(form)
    assert error is None
    assert config["mode"] == "ethernet"


def test_wifi_requires_selected_or_manual_ssid(monkeypatch):
    monkeypatch.setattr(portal, "ethernet_connected", lambda: False)
    form = valid_form()
    form["ssid"] = ""
    config, error = portal.validate_setup(form)
    assert config is None
    assert "WLAN" in error


def test_manual_ssid_overrides_scan_selection(monkeypatch):
    monkeypatch.setattr(portal, "ethernet_connected", lambda: False)
    form = valid_form()
    form["manual_ssid"] = "Verstecktes WLAN"
    config, error = portal.validate_setup(form)
    assert error is None
    assert config["ssid"] == "Verstecktes WLAN"


def test_fritz_credentials_are_required_only_when_enabled(monkeypatch):
    monkeypatch.setattr(portal, "ethernet_connected", lambda: False)
    form = valid_form()
    form.update({"fritz_enabled": "1", "fritz_host": "fritz.box", "fritz_username": "GrowCentral", "fritz_password": ""})
    config, error = portal.validate_setup(form)
    assert config is None
    assert "FRITZ" in error

    form["fritz_password"] = "fritz-smart-home-passwort"
    config, error = portal.validate_setup(form)
    assert error is None
    assert config["fritz_username"] == "GrowCentral"


def test_wifi_scan_parses_escaped_ssids_and_keeps_best_signal(monkeypatch):
    outputs = iter([
        SimpleNamespace(returncode=0, stdout="", stderr=""),
        SimpleNamespace(returncode=0, stdout="Grow\\:Lab:61:WPA2\nGrow\\:Lab:88:WPA2\nOffen:40:--\n", stderr=""),
    ])
    monkeypatch.setattr(portal.subprocess, "run", lambda *_args, **_kwargs: next(outputs))
    networks, error = portal.scan_networks()
    assert error is None
    assert networks == [("Grow:Lab", "88", "WPA2"), ("Offen", "40", "--")]


def test_setup_ap_blocks_normal_gui_for_setup_subnet():
    script = SETUP_AP_PATH.read_text(encoding="utf-8")
    assert 'SETUP_SUBNET="10.42.0.0/24"' in script
    assert 'deny from "$SETUP_SUBNET" to any port 8080 proto tcp' in script
    assert "ipv4.shared-dhcp-range 10.42.0.10,10.42.0.250" in script
    assert "ipv4.method shared" in script


def test_runtime_password_hash_does_not_store_plaintext():
    password = "ein-neues-gui-passwort"
    encoded = apply_setup._gui_hash(password)
    assert encoded.startswith("pbkdf2_sha256$")
    assert password not in encoded


def test_apply_revalidates_gui_and_fritz_fields(monkeypatch):
    monkeypatch.setattr(portal, "ethernet_connected", lambda: False)
    config, error = portal.validate_setup(valid_form())
    assert error is None
    apply_setup.validate(config)
    config["gui_username"] = "ungültig mit leerzeichen"
    with __import__("pytest").raises(ValueError):
        apply_setup.validate(config)


def test_wifi_password_is_not_exposed_in_process_arguments(monkeypatch):
    monkeypatch.setattr(portal, "ethernet_connected", lambda: False)
    calls = []

    def fake_run(*arguments, **_kwargs):
        calls.append(arguments)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

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


def test_image_workflow_is_synchronized_to_alpha_075():
    workflow = IMAGE_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "alpha-0.7.5-build-" in workflow
    assert '.version == "0.7.5"' in workflow
    assert "app.entrypoint:app" in workflow
    assert "policykit-1" in workflow
    assert "v4l2-ctl" in workflow
    assert "ffmpeg" in workflow
    assert "SupplementaryGroups=systemd-journal video netdev" in workflow


def test_first_boot_portal_uses_real_pam_user(monkeypatch):
    class Client:
        def start(self, service):
            assert service == "login"
        def set_item(self, *_args):
            pass
        def authenticate(self):
            pass

    fake = SimpleNamespace(pam=Client, PAM_USER=1, PAM_CONV=2, PAM_PROMPT_ECHO_ON=3, PAM_PROMPT_ECHO_OFF=4)
    monkeypatch.setattr(portal, "PAM", fake)
    assert portal.authenticate_user("GrowCentral", "secret") is True
    assert portal.authenticate_user("root", "secret") is False
