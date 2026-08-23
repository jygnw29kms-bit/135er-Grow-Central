from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cloud_smoke_is_read_only_and_validates_official_endpoints():
    source = (ROOT / "image-builder/firstboot/cloud-smoke-test.sh").read_text()
    assert "https://135ercloud.dezender.de" in source
    assert '"$CLOUD_ORIGIN/health"' in source
    assert '"$CLOUD_ORIGIN/.well-known/growcentral-cloud"' in source
    assert 'startswith("wss://")' in source
    assert "api/v1/telemetry" not in source
    assert "GC_REMOTE_COMMANDS" not in source


def test_image_workflow_installs_and_runs_cloud_smoke():
    workflow = (ROOT / ".github/workflows/build-pi3-image.yml").read_text()
    assert "grow-central-cloud-smoke-test" in workflow
    assert "cloud-smoke-test.sh" in workflow
    assert "GC_REMOTE_COMMANDS=false" in workflow
    assert "802-11-wireless-security.pmf 1" in (
        ROOT / "image-builder/firstboot/setup-ap.sh"
    ).read_text()


def test_test_image_remote_maintenance_enrolls_at_first_boot_and_is_loopback_only():
    controller = (ROOT / "image-builder/firstboot/remote-maintenance.sh").read_text()
    unit = (
        ROOT / "image-builder/firstboot/grow-central-remote-maintenance.service"
    ).read_text()
    workflow = (ROOT / ".github/workflows/build-pi3-image.yml").read_text()
    bastion = (ROOT / "scripts/setup-growcentral-maintenance-bastion.sh").read_text()
    assert "ssh-keygen" in controller
    assert "ssh-keyscan" in controller
    assert "SHA256:" in controller
    assert "StrictHostKeyChecking=yes" in unit
    assert "BatchMode=yes" in unit
    assert "-R 127.0.0.1:${GC_REMOTE_MAINTENANCE_PORT}:127.0.0.1:22" in unit
    assert "systemctl enable --now" in controller
    assert "/api/v2/maintenance/enroll" in controller
    assert "maintenance_activation_code" in (ROOT / "app/firstboot.py").read_text()
    assert '"/usr/local/sbin/grow-central-remote-maintenance", "enroll", "-"' in (
        ROOT / "image-builder/firstboot/apply_setup.py"
    ).read_text()
    assert "input_text=activation_code" in (
        ROOT / "image-builder/firstboot/apply_setup.py"
    ).read_text()
    assert "--data-binary @-" in controller
    assert '--data "$request"' not in controller
    assert "systemctl disable --now" in controller
    assert "systemctl enable NetworkManager.service" in workflow
    assert "systemctl enable grow-central-remote-maintenance" not in workflow
    assert "AllowTcpForwarding remote" in bastion
    assert "GatewayPorts no" in bastion
    assert 'permitlisten="127.0.0.1:' in bastion
    assert "PasswordAuthentication no" in bastion


def test_cloud_installer_provisions_one_time_enrollment_without_exposing_ssh():
    installer = (ROOT / "scripts/install-135ercloud-v6.payload.sh").read_text()
    assert "growcentral-maintenance-code" in installer
    assert "growcentral-maintenance-worker" in installer
    assert 'permitlisten="127.0.0.1:{port}"' in installer
    assert "GatewayPorts no" in installer
    assert "PasswordAuthentication no" in installer
    assert 'record["used"]=True' in installer
    assert "MAINTENANCE_SSH_HOST" in installer
