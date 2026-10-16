from pathlib import Path


def test_firstboot_verifies_mdns_after_setup_ap_is_down():
    root = Path(__file__).resolve().parents[1]
    text = (root / "image-builder/firstboot/apply_setup.py").read_text(encoding="utf-8")
    assert 'mdns_name = f"{FIXED_HOSTNAME}.local"' in text
    assert 'avahi-resolve-host-name", "-4", mdns_name' in text
    ap_down = text.index('run("nmcli", "connection", "down", AP_CONNECTION, check=False)', text.index('network_mode = config["mode"]'))
    avahi_restart = text.index('run("systemctl", "restart", "avahi-daemon.service")', ap_down)
    runtime_check = text.index('verify_runtime(network_address)', avahi_restart)
    assert ap_down < avahi_restart < runtime_check
