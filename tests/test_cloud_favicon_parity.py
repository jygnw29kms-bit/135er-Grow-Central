"""Favicon parity for Cloud login, guest join and local/cloud Final Master."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cloud_entrypoints_expose_canonical_icons():
    local = (ROOT / "web/gc-final.html").read_text(encoding="utf-8")
    for name in ("cloud/portal/index.html", "cloud/portal/join-room.html",
                 "cloud/portal/cloud-master.html"):
        html = (ROOT / name).read_text(encoding="utf-8")
        assert 'rel="icon"' in html
        assert 'href="/static/brand-mark.png"' in html
        assert 'rel="apple-touch-icon"' in html
        assert 'href="/static/gc-icon-192.png"' in html
        assert 'rel="manifest"' in html
        assert 'href="/static/gc-manifest.webmanifest"' in html
    assert 'href="/static/brand-mark.png"' in local


def test_generated_browser_favicon_matches_app_icon():
    module_path = ROOT / "scripts/build_cloud_favicon.py"
    spec = importlib.util.spec_from_file_location("gc_favicon_builder", module_path)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    icon = (ROOT / "web/gc-icon-192.png").read_bytes()
    ico = builder.favicon_bytes(icon)
    assert ico[:6] == b"\x00\x00\x01\x00\x01\x00"
    assert ico[22:] == icon
    assert ico[:6] + ico[22:] != ico
    assert ico == builder.favicon_bytes(icon)


def test_favicon_is_part_of_cloud_deployment_and_verification():
    deploy = (ROOT / "cloud/portal/deploy_cloud_portal.sh").read_text()
    verify = (ROOT / "scripts/verify_cloud_final_master_deployment.py").read_text()
    assert '"$stage/favicon.ico"' in deploy
    assert '"favicon.ico"' in verify
    assert "favicon_bytes(icon.read_bytes())" in verify
