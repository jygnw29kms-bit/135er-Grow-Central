from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_failed_firstboot_reuses_hardened_ap_bootstrap_and_verifies_dhcp():
    text = read("image-builder/firstboot/apply_setup.py")
    assert 'SETUP_AP_SCRIPT = APP_ROOT / "image-builder/firstboot/setup-ap.sh"' in text
    assert 'run("bash", str(SETUP_AP_SCRIPT), check=False)' in text
    assert '"10.42.0.1/24" in address.stdout' in text
    assert '":67" in dhcp.stdout' in text
    assert "Setup-AP-Wiederherstellung fehlgeschlagen" in text


def test_v7_proxy_limits_accept_cloud_link_support_bundle_cap():
    routing = read("scripts/configure-v7-routing.sh")
    agent = read("local/cloud_link/agent.py")
    example = read("deploy/nginx/grow-central-cloud.conf.example")
    assert "32 * 1024 * 1024" in agent
    assert routing.count("client_max_body_size 40m;") >= 2
    assert "135ER-GROWCENTRAL-V7-PROXY-LIMIT" in routing
    assert "client_max_body_size 40m;" in example


def test_mdns_alias_restarts_if_publisher_exits_without_ip_change():
    text = read("app/mdns_alias.py")
    assert "publisher_dead = _process is not None and _process.returncode is not None" in text
    assert "publisher_missing = bool(address) and _process is None" in text
    assert "address != published or publisher_dead or publisher_missing" in text
    assert "_process = None" in text
