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


def test_test_image_remote_maintenance_is_opt_in_and_loopback_only():
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
    assert "systemctl disable --now" in controller
    assert "systemctl enable NetworkManager.service" in workflow
    assert "systemctl enable grow-central-remote-maintenance" not in workflow
    assert "AllowTcpForwarding remote" in bastion
    assert "GatewayPorts no" in bastion
    assert 'permitlisten="127.0.0.1:' in bastion
    assert "PasswordAuthentication no" in bastion
