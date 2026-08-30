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


def valid_form(ssh_enabled=True):
    return {
        "mode": "wifi",
        "hostname": "135er-grow-central",
        "timezone": "Europe/Berlin",
        "ssid": "Werkstatt WLAN",
        "wifi_password": "sicheres-wlan-passwort",
        "ssh_enabled": "1" if ssh_enabled else "0",
        "new_password": "ein-neues-systempasswort" if ssh_enabled else "",
        "gui_username": "GrowCentral",
        "gui_password": "ein-neues-gui-passwort",
        "fritz_enabled": "0",
    }


def test_setup_ap_exposes_always_on_gui_for_firstboot():
    script = SETUP_AP_PATH.read_text(encoding="utf-8")
    assert 'deny from "$SETUP_SUBNET" to any port 8080 proto tcp' not in script
    assert 'DHCP_RANGE="10.42.0.10,10.42.0.250"' in script
    assert 'ipv4.shared-dhcp-range "$DHCP_RANGE"' in script
    assert "ipv4.method shared" in script


def test_setup_ap_is_open_only_while_unprovisioned_and_locks_ssh():
    script = SETUP_AP_PATH.read_text(encoding="utf-8")
    assert "wifi-sec.psk" not in script
    assert "wifi-sec.key-mgmt wpa-psk" not in script
    assert 'if [ -e "${STATE_DIR}/.provisioned" ]' in script
    assert "passwd --lock GrowCentral" in script
    assert "PasswordAuthentication no" in script
    assert 'systemctl disable --now "$unit"' in script


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


def test_system_password_is_optional_only_when_ssh_is_disabled():
    apply_setup.validate(valid_form(ssh_enabled=False))
    invalid = valid_form(ssh_enabled=True)
    invalid["new_password"] = ""
    with __import__("pytest").raises(ValueError):
        apply_setup.validate(invalid)


def test_ssh_disabled_path_locks_account_stops_listener_and_closes_firewall(tmp_path):
    calls = []

    def fake_run(*arguments, **_kwargs):
        calls.append(arguments)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    dropin = tmp_path / "99-grow-central-access.conf"
    with patch.object(apply_setup, "run", fake_run), patch.object(apply_setup, "SSH_DROPIN", dropin):
        apply_setup.configure_local_ssh(False)

    assert "PasswordAuthentication no" in dropin.read_text(encoding="utf-8")
    assert ("passwd", "--lock", "GrowCentral") in calls
    for unit in ("ssh.socket", "ssh.service", "sshd.service"):
        assert ("systemctl", "disable", "--now", unit) in calls
    assert ("ufw", "--force", "delete", "allow", "22/tcp") in calls


def test_ssh_enabled_path_sets_password_opens_firewall_and_starts_service(tmp_path):
    calls = []

    def fake_run(*arguments, **kwargs):
        calls.append((arguments, kwargs.get("input_text")))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    dropin = tmp_path / "99-grow-central-access.conf"
    with patch.object(apply_setup, "run", fake_run), patch.object(apply_setup, "SSH_DROPIN", dropin):
        apply_setup.configure_local_ssh(True, "ein-neues-systempasswort")

    assert "PasswordAuthentication yes" in dropin.read_text(encoding="utf-8")
    chpasswd = next(item for item in calls if item[0] == ("chpasswd",))
    assert chpasswd[1] == "GrowCentral:ein-neues-systempasswort\n"
    assert any(item[0] == ("ufw", "allow", "22/tcp") for item in calls)
    assert any(item[0] == ("systemctl", "enable", "--now", "ssh.service") for item in calls)


def test_wifi_password_is_not_exposed_in_process_arguments(monkeypatch):
    calls = []

    def fake_run(*arguments, **_kwargs):
        calls.append(arguments)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    real_mkstemp = tempfile.mkstemp

    def temporary_runtime_file(*_args, **_kwargs):
        return real_mkstemp(prefix="grow-central-test-", dir="/tmp", text=True)

    config = valid_form()
    with patch.object(apply_setup, "run", fake_run), patch.object(apply_setup, "wifi_interface", lambda: "wlan0"), patch.object(apply_setup.tempfile, "mkstemp", temporary_runtime_file):
        apply_setup.configure_wifi(config)

    flattened = [str(argument) for call in calls for argument in call]
    assert config["wifi_password"] not in flattened
    assert "passwd-file" in flattened
    activation = next(call for call in calls if "passwd-file" in call)
    assert activation[:6] == ("nmcli", "--wait", "35", "connection", "up", "grow-central-uplink")
    assert activation.index("passwd-file") > activation.index("grow-central-uplink")


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
    assert "grow-central-firstboot-debug.service" in workflow
    assert "grow-central-support-bundle.path" in workflow
    assert "Storage=persistent" in workflow


def test_image_workflow_has_no_factory_password_or_default_ssh_exposure():
    workflow = IMAGE_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "GrowCentral:grow-central-test" not in workflow
    assert "Initial GUI login: GrowCentral / grow-central-test" not in workflow
    assert "Setup AP key: grow-central-test" not in workflow
    assert not any(line.strip().startswith("GC_GUI_PASSWORD_HASH=") for line in workflow.splitlines())
    assert not any(line.strip().startswith("GC_GUI_USERNAME=") for line in workflow.splitlines())
    assert not any(line.strip() == "ufw allow 22/tcp" for line in workflow.splitlines())
    assert "systemctl enable NetworkManager.service avahi-daemon.service grow-central-headless-firstboot.service grow-central-bluetooth-init.service ssh " not in workflow
    assert "passwd --lock GrowCentral" in workflow
    assert "Factory password: none" in workflow


def test_appliance_exposes_a_simple_port_80_login_without_changing_the_backend_port():
    root = Path(__file__).parents[1]
    workflow = IMAGE_WORKFLOW_PATH.read_text(encoding="utf-8")
    socket = (root / "systemd" / "grow-central-http.socket").read_text(encoding="utf-8")
    proxy = (root / "systemd" / "grow-central-http.service").read_text(encoding="utf-8")
    assert "ListenStream=80" in socket
    assert "systemd-socket-proxyd 127.0.0.1:8080" in proxy
    assert "DynamicUser=true" in proxy
    assert "NoNewPrivileges=true" in proxy
    assert "CapabilityBoundingSet=\n" in proxy
    assert "SystemCallFilter=@system-service" in proxy
    assert "RestrictNamespaces=true" in proxy
    assert "ufw allow 80/tcp" in workflow
    assert "systemctl enable" in workflow and "grow-central-http.socket" in workflow
    assert "http://127.0.0.1/api/health" in workflow


def test_setup_completion_marker_is_written_only_after_runtime_and_access_policy():
    source = APPLY_PATH.read_text(encoding="utf-8")
    main_source = source[source.index("def main()") :]
    assert main_source.index("verify_runtime(network_address)") < main_source.index("configure_local_ssh(ssh_enabled, system_credential)")
    assert main_source.index("configure_local_ssh(ssh_enabled, system_credential)") < main_source.index("mark_provisioned()")
    assert "SETUP_FILE" not in source


def test_setup_verifies_real_network_and_retries_runtime():
    source = APPLY_PATH.read_text(encoding="utf-8")
    assert '"ip", "route", "show", "default"' in source
    assert '"getent", "ahostsv4", "www.debian.org"' in source
    assert '"curl", "--ipv4", "--interface", device' in source
    assert 'f"http://{target}:8080/api/health"' in source
    assert "time.monotonic() + 60" in source
    assert "restore_runtime_settings(previous_env)" in source
    main_source = source[source.index("def main()") :]
    assert main_source.index("ERROR_FILE.unlink(missing_ok=True)") < main_source.index("try:")


def test_setup_is_integrated_into_authenticated_main_gui():
    root = Path(__file__).parents[1]
    page = (root / "web" / "index.html").read_text(encoding="utf-8")
    script = (root / "web" / "app.js").read_text(encoding="utf-8")
    assert not (root / "web" / "setup.html").exists()
    assert 'id="firstBootSetupForm"' in page
    assert 'id="restartSetupBtn"' in page
    assert "135er-Grow-Central.local" in page
    assert "/api/setup/network-status" in script
    assert "/api/setup/networks" in script
    assert "/api/setup/restart" in script


def test_pi3_ap_scan_limitation_is_explicit_and_manual_ssid_remains_available():
    source = (Path(__file__).parents[1] / "app" / "firstboot.py").read_text(encoding="utf-8")
    page = (Path(__file__).parents[1] / "web" / "index.html").read_text(encoding="utf-8")
    assert '"manual_ssid_required"' in source
    assert "während des aktiven Setup-APs" in source
    assert 'name="ssid"' in page


def test_setup_error_is_readable_by_the_web_service():
    source = APPLY_PATH.read_text(encoding="utf-8")
    assert 'os.chown(ERROR_FILE, 0, grp.getgrnam("growcentral").gr_gid)' in source


def test_external_probe_is_a_warning_not_a_setup_blocker():
    source = APPLY_PATH.read_text(encoding="utf-8")
    assert "write_warning(" in source
    assert "Das Setup wurde trotzdem abgeschlossen." in source
    assert 'raise RuntimeError("Über die gewählte Verbindung konnte kein Internetzugang bestätigt werden.")' not in source
    assert 'os.chown(WARNING_FILE, 0, grp.getgrnam("growcentral").gr_gid)' in source
