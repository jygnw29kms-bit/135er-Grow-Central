from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_v7_installer_preserves_legacy_data_and_modes():
    text = read("scripts/install-135ercloud-v7.sh")
    assert "backup_current" in text
    assert "sqlite3" in text and ".backup" in text
    assert "pg_dump" in text
    assert "admin-mode" in text
    assert "configure-cloud-admin-mode.sh" in text
    assert "bootstrap-standalone-cloud-core.sh" in text
    assert "command -v plesk" in text
    assert "rm -rf \"$DATA_DIR\"" not in text
    assert "rm -rf \"$CONF_DIR\"" not in text


def test_standalone_bootstrap_keeps_v6_identity_core():
    text = read("scripts/bootstrap-standalone-cloud-core.sh")
    assert "install-135ercloud-v6.payload.sh" in text
    assert "V7 standalone compatibility overrides" in text
    assert "configure_plesk()" in text
    assert "proxy_pass http://127.0.0.1:$APP_PORT" in text


def test_v7_admin_uses_same_database_url_and_entitlements_are_separate():
    text = read("cloud/v7/admin_app.py")
    assert 'DATABASE_URL = os.environ["DATABASE_URL"]' in text
    assert "CREATE TABLE IF NOT EXISTS device_entitlements" in text
    assert "SELECT id FROM devices" in text
    assert "BASIC" in text and "PLUS" in text and "PRO" in text and "INTERNAL" in text
    for feature in (
        "remote_control", "camera", "history_extended", "alerts",
        "automation_pro", "api_access", "beta_features",
    ):
        assert feature in text


def test_v7_apt_package_does_not_purge_customer_data():
    text = read("scripts/setup-135ercloud-apt-repo-v2.sh")
    assert "Version: $PKG_VERSION" in text
    assert "install-135ercloud-v7.sh --package-mode" in text
    assert "preserve /etc/135er-growcentral-cloud" in text
    assert "preserve /etc/135er-growcentral-cloud and /var/lib" in text
    assert "rm -rf /var/lib/135er-growcentral-cloud" not in text
