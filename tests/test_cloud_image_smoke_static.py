from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cloud_smoke_is_optional_read_only_and_local_first():
    source = (ROOT / "image-builder/firstboot/cloud-smoke-test.sh").read_text()
    assert "https://135ercloud.grow-central.de" in source
    assert "/api/health" in source
    assert "/health" in source
    assert "DEGRADED" in source
    assert "lokaler Betrieb bleibt gültig" in source
    assert "GESAMTSTATUS: LOCAL-FIRST OK" in source
    assert "api/v1/telemetry" not in source
    assert "GC_REMOTE_COMMANDS" not in source


def test_cloud_smoke_enforces_headless_final_image():
    source = (ROOT / "image-builder/firstboot/cloud-smoke-test.sh").read_text()
    assert "HEADLESS-PRUNE" in source
    assert "apt-get purge -y --auto-remove" in source
    for component in (
        "chromium",
        "openbox",
        "unclutter",
        "xinit",
        "x11-xserver-utils",
        "xserver-xorg-core",
        "xserver-xorg-input-libinput",
    ):
        assert component in source
    assert "display-policy" in source
    assert "command -v \"$command\"" in source
    assert "grow-central-display-kiosk.service" in source


def test_image_workflow_installs_and_runs_cloud_smoke():
    workflow = (ROOT / ".github/workflows/build-pi3-image.yml").read_text()
    setup_ap = (ROOT / "image-builder/firstboot/setup-ap.sh").read_text()
    assert "grow-central-cloud-smoke-test" in workflow
    assert "cloud-smoke-test.sh" in workflow
    assert "GC_REMOTE_COMMANDS=false" in workflow
    assert "ipv4.method shared" in setup_ap
    assert "wifi-sec.psk" not in setup_ap
    assert "PasswordAuthentication no" in setup_ap


def test_closed_test_image_has_no_remote_maintenance_activation_path():
    workflow = (ROOT / ".github/workflows/build-pi3-image.yml").read_text()
    firstboot = (ROOT / "app/firstboot.py").read_text()
    apply_setup = (ROOT / "image-builder/firstboot/apply_setup.py").read_text()

    assert "maintenance_activation_code" not in firstboot
    assert "maintenance_activation_code" not in apply_setup
    assert "grow-central-remote-maintenance.service" not in workflow
    assert "systemctl enable grow-central-remote-maintenance" not in workflow
    assert "GC_REMOTE_COMMANDS=false" in workflow


def test_remote_maintenance_assets_remain_dormant_if_retained_for_future_work():
    controller_path = ROOT / "image-builder/firstboot/remote-maintenance.sh"
    unit_path = ROOT / "image-builder/firstboot/grow-central-remote-maintenance.service"
    if controller_path.exists() and unit_path.exists():
        controller = controller_path.read_text()
        unit = unit_path.read_text()
        assert "systemctl enable --now" in controller
        assert "StrictHostKeyChecking=yes" in unit
        assert "BatchMode=yes" in unit
        workflow = (ROOT / ".github/workflows/build-pi3-image.yml").read_text()
        assert "grow-central-remote-maintenance.service" not in workflow


def test_cloud_installer_provisions_one_time_enrollment_without_exposing_ssh():
    installer = (ROOT / "scripts/install-135ercloud-v6.payload.sh").read_text()
    assert "growcentral-maintenance-code" in installer
    assert "growcentral-maintenance-worker" in installer
    assert 'permitlisten="127.0.0.1:{port}"' in installer
    assert "GatewayPorts no" in installer
    assert "PasswordAuthentication no" in installer
    assert 'record["used"]=True' in installer
    assert "MAINTENANCE_SSH_HOST" in installer
