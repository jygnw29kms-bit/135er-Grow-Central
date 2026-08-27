"""Static regression checks for the Cloud administration foundation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_cloud_core_has_device_entitlements_and_pending_registration():
    main = text("cloud/app/main.py")
    assert "/api/v1/devices/{device_id}/entitlements" in main
    assert "_touch_managed_device" in main
    assert "'pending','BASIC'" in main


def test_admin_api_is_token_protected_and_supports_manual_plans():
    admin = text("cloud/app/admin.py")
    assert "cloud_admin_token" in admin
    assert 'Literal["BASIC", "PLUS", "PRO", "INTERNAL"]' in admin
    for feature in (
        "remote_control", "camera", "history_extended", "alerts",
        "automation_pro", "api_access", "beta_features",
    ):
        assert feature in admin


def test_database_migration_is_idempotent():
    db = text("cloud/app/db.py")
    assert "CREATE TABLE IF NOT EXISTS managed_devices" in db
    assert "CREATE TABLE IF NOT EXISTS device_features" in db
    assert "CREATE TABLE IF NOT EXISTS cloud_settings" in db


def test_installer_preserves_admin_mode_on_apt_upgrade():
    setup = text("scripts/configure-cloud-admin-mode.sh")
    assert "Existing installations keep their selected mode across apt upgrade" in setup
    assert "standalone|plesk|both" in setup
    assert "CLOUD_ADMIN_TOKEN" in setup
