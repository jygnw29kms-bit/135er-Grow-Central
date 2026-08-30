from pathlib import Path

ROOT = Path(__file__).parents[1]
PORTAL = ROOT / "app" / "setup_portal.py"
AP_SCRIPT = ROOT / "image-builder" / "firstboot" / "setup-ap.sh"
CONSOLE_CSS = ROOT / "web" / "console.css"
APP_CSS = ROOT / "web" / "app.css"
MOBILE_CSS = ROOT / "mobile" / "www" / "styles.css"
CLOUD_STATUS = ROOT / "app" / "cloud_status.py"


def test_captive_portal_waits_for_real_setup_completion():
    source = PORTAL.read_text(encoding="utf-8")
    assert "waitForCompletion" in source
    assert "/api/setup/status" in source
    assert "setTimeout(()=>location.href" not in source
    assert "setup_required===false" in source


def test_captive_portal_cleans_setup_ap_after_provisioning():
    source = PORTAL.read_text(encoding="utf-8")
    assert "90-grow-central-captive.conf" in source
    assert '"connection", "modify", AP_CONNECTION, "connection.autoconnect", "no"' in source
    assert '"connection", "down", AP_CONNECTION' in source
    assert "if not firstboot.setup_active():" in source
    assert "_cleanup_captive_runtime()" in source


def test_unprovisioned_appliance_exposes_setup_not_normal_runtime_routes():
    source = PORTAL.read_text(encoding="utf-8")
    assert 'if path == "/api/health" and request.method == "GET":' in source
    assert 'if path.startswith("/api/"):' in source
    assert '"detail": "Ersteinrichtung erforderlich"' in source
    assert "status_code=403" in source
    assert 'return RedirectResponse("/setup", status_code=302)' in source
    assert '/static/brand-logo.png' in source
    assert '/static/brand-mark.png' in source


def test_firstboot_portal_creates_gui_login_and_keeps_ssh_opt_in():
    source = PORTAL.read_text(encoding="utf-8")
    assert "kein bekanntes Benutzer- oder Gerätepasswort" in source
    assert 'id="guiPassword2"' in source
    assert 'id="sshEnabled" type="checkbox"' in source
    assert "SSH aktivieren" in source
    assert "ssh_enabled:ssh" in source
    assert "new_password:ssh?$('systemPassword').value:''" in source


def test_setup_wifi_list_uses_dom_text_not_ssid_html():
    source = PORTAL.read_text(encoding="utf-8")
    assert "document.createElement('option')" in source
    assert "o.textContent=" in source
    assert ".map(n=>`<option" not in source


def test_setup_ap_advertises_and_forces_captive_portal_dns():
    source = AP_SCRIPT.read_text(encoding="utf-8")
    assert 'CAPTIVE_URL="http://10.42.0.1/setup"' in source
    assert "address=/#/${CAPTIVE_IP}" in source
    assert "dhcp-option=114,${CAPTIVE_URL}" in source


def test_responsive_layers_use_dynamic_viewport_and_safe_areas():
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in (CONSOLE_CSS, APP_CSS, MOBILE_CSS)
    )
    assert "100dvh" in combined
    assert "safe-area-inset-bottom" in combined
    assert "safe-area-inset-left" in combined
    assert "safe-area-inset-right" in combined


def test_cloud_status_checks_real_health_endpoint_and_service():
    source = CLOUD_STATUS.read_text(encoding="utf-8")
    assert "135er-grow-central-cloud-link.service" in source
    assert 'f"{origin}/api/health"' in source
    assert '"connected": connected' in source
    assert '"host": host' in source
