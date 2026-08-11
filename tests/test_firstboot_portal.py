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
        "new_password": "ein-neues-passwort",
        "new_password_confirm": "ein-neues-passwort",
    }


def test_valid_setup_is_normalized():
    config, error = portal.validate_setup(valid_form())
    assert error is None
    assert config["hostname"] == "grow-central"
    assert "new_password_confirm" not in config


def test_manual_ssid_overrides_network_selection():
    form = valid_form()
    form["ssid"] = "Gefundenes WLAN"
    form["manual_ssid"] = "Verstecktes WLAN"
    config, error = portal.validate_setup(form)
    assert error is None
    assert config["ssid"] == "Verstecktes WLAN"


def test_hosts_entry_follows_configured_hostname(tmp_path):
    hosts = tmp_path / "hosts"
    hosts.write_text("127.0.0.1\tlocalhost\n127.0.1.1\tgrow-central-test\n", encoding="utf-8")
    apply_setup.update_hosts("grow-central", hosts)
    assert hosts.read_text(encoding="utf-8") == "127.0.0.1\tlocalhost\n127.0.1.1\tgrow-central\n"


def test_provisioning_marker_is_committed_atomically(tmp_path, monkeypatch):
    marker = tmp_path / ".provisioned"
    monkeypatch.setattr(apply_setup, "STATE_DIR", tmp_path)
    monkeypatch.setattr(apply_setup, "MARKER", marker)
    apply_setup.mark_provisioned()
    assert marker.read_text(encoding="utf-8").startswith("provisioned_at=")
    assert not marker.with_suffix(".tmp").exists()


def test_native_debian_pam_binding_is_used(monkeypatch):
    class Client:
        def start(self, service): assert service == "login"
        def set_item(self, *_args): pass
        def authenticate(self): pass

    fake = SimpleNamespace(pam=Client, PAM_USER=1, PAM_CONV=2, PAM_PROMPT_ECHO_ON=3, PAM_PROMPT_ECHO_OFF=4)
    monkeypatch.setattr(portal, "PAM", fake)
    assert portal.authenticate_user("GrowCentral", "secret") is True
    assert portal.authenticate_user("root", "secret") is False


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


def test_setup_networks_are_dual_stack_and_ap_profile_is_repaired():
    script = SETUP_AP_PATH.read_text(encoding="utf-8")
    workflow = IMAGE_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'ADDRESS="10.42.0.1/24"' in script
    assert "ipv4.method shared" in script
    assert "ipv4.shared-dhcp-range 10.42.0.10,10.42.0.250" in script
    assert "ipv4.shared-dhcp-lease-time 3600" in script
    assert "ss -H -lun" in script and "/:67$/" in script
    assert "ipv4.never-default yes" in script
    assert "ipv6.method shared" in script
    assert "ipv6.never-default yes" in script
    assert script.index('fi\n\n# Apply the complete profile') < script.index('nmcli connection modify "$CONNECTION"')
    assert "ufw allow in on wlan0 to any port 67 proto udp" in workflow
    assert "ufw allow in on wlan0 to any port 53 proto udp" in workflow
    assert "ufw allow in on wlan0 to any port 53 proto tcp" in workflow
    assert "SupplementaryGroups=systemd-journal" in workflow
    assert "rfkill unblock bluetooth" in workflow

    calls = []

    def fake_run(*arguments, **_kwargs):
        calls.append(arguments)
        return SimpleNamespace(returncode=0)

    real_mkstemp = tempfile.mkstemp

    def temporary_runtime_file(*_args, **_kwargs):
        return real_mkstemp(prefix="grow-central-ipv4-test-", dir="/tmp", text=True)

    config, error = portal.validate_setup(valid_form())
    assert error is None
    with patch.object(apply_setup, "run", fake_run), patch.object(apply_setup.tempfile, "mkstemp", temporary_runtime_file):
        apply_setup.configure_wifi(config)

    flattened = [str(argument) for call in calls for argument in call]
    ipv6_index = flattened.index("ipv6.method")
    assert flattened[ipv6_index + 1] == "auto"
