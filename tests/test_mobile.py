import json
from pathlib import Path
from types import SimpleNamespace

from app.mobile import WEB_DIR, _client_is_lan


def request_from(host: str):
    return SimpleNamespace(client=SimpleNamespace(host=host))


def test_mobile_accepts_private_ipv4():
    assert _client_is_lan(request_from("192.168.178.42")) is True
    assert _client_is_lan(request_from("10.42.0.15")) is True


def test_mobile_accepts_loopback_and_link_local():
    assert _client_is_lan(request_from("127.0.0.1")) is True
    assert _client_is_lan(request_from("169.254.20.10")) is True


def test_mobile_rejects_public_ip():
    assert _client_is_lan(request_from("8.8.8.8")) is False


def test_mobile_allows_internal_proxy_name():
    assert _client_is_lan(request_from("testclient")) is True


def test_mobile_manifest_is_valid_and_lan_start_path():
    manifest = json.loads((WEB_DIR / "mobile.webmanifest").read_text(encoding="utf-8"))
    assert manifest["start_url"] == "/mobile"
    assert manifest["display"] == "standalone"
    assert manifest["short_name"] == "GrowCentral"


def test_mobile_assets_exist():
    for name in ("mobile.html", "mobile.webmanifest", "mobile-sw.js"):
        assert (Path(WEB_DIR) / name).is_file()
