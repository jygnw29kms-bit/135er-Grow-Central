from pathlib import Path
import asyncio

from app import diagnostics
from app.diagnostics import COMPLETION_MARKERS, SUPPORT_LATEST, SUPPORT_REQUEST, redact, router


def test_redacts_common_secret_shapes():
    value = redact("token=test password: hunter2 Authorization=Bearer-secret safe=value")
    assert "test" not in value
    assert "hunter2" not in value
    assert "Bearer-secret" not in value
    assert "safe=value" in value


def test_does_not_redact_unrelated_log_text():
    assert redact("ssh.service active on port 22") == "ssh.service active on port 22"


def test_firstboot_units_have_completion_markers():
    assert set(COMPLETION_MARKERS) == {
        "grow-central-headless-firstboot.service",
        "grow-central-firstboot-firewall.service",
    }


def test_support_bundle_api_can_request_check_and_download():
    paths = {(route.path, tuple(sorted(route.methods))) for route in router.routes}
    assert ("/api/v1/diagnostics/bundle", ("POST",)) in paths
    assert ("/api/v1/diagnostics/bundle/status", ("GET",)) in paths
    assert ("/api/v1/diagnostics/bundle/download", ("GET",)) in paths
    assert SUPPORT_REQUEST.name == "support-bundle-request"
    assert SUPPORT_LATEST.name == "Grow-Central-Support-latest.tar.gz"


def test_support_collector_covers_future_system_hardware_and_app_failures():
    source = (Path(__file__).parents[1] / "image-builder" / "firstboot-debug.sh").read_text(encoding="utf-8")
    for evidence in ("journalctl -b -1", "coredumpctl", "lsusb", "bluetoothctl", "v4l2-ctl", "PRAGMA quick_check", "nft list ruleset"):
        assert evidence in source
    assert "nmcli connection show grow-central-uplink" in source
    assert '"registered_devices": safe' in source
    assert '"password"' not in source[source.index('section "Application data integrity"'):source.index('section "Permissions as service user"')]
    assert "--show-secrets no" not in source
    assert "[REDACTED]" in source


def test_support_bundle_request_and_status_use_state_files(tmp_path, monkeypatch):
    request = tmp_path / "support-bundle-request"
    latest = tmp_path / "Grow-Central-Support-latest.tar.gz"
    monkeypatch.setattr(diagnostics, "STATE_DIR", tmp_path)
    monkeypatch.setattr(diagnostics, "SUPPORT_REQUEST", request)
    monkeypatch.setattr(diagnostics, "SUPPORT_LATEST", latest)
    result = asyncio.run(diagnostics.create_support_bundle())
    assert result == {"ok": True, "pending": True}
    assert request.is_file()
    pending = asyncio.run(diagnostics.support_bundle_status())
    assert pending["pending"] is True
    assert pending["available"] is False
    latest.write_bytes(b"support")
    ready = asyncio.run(diagnostics.support_bundle_status())
    assert ready["available"] is True
    assert ready["size"] == 7


def test_download_pins_archive_before_latest_symlink_changes(monkeypatch, tmp_path):
    import gzip
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    old=tmp_path/'old.tar.gz';new=tmp_path/'new.tar.gz';latest=tmp_path/'latest.tar.gz'
    old.write_bytes(gzip.compress(b'old diagnostic'));new.write_bytes(gzip.compress(b'new diagnostic'))
    latest.symlink_to(old.name);monkeypatch.setattr(diagnostics,'SUPPORT_LATEST',latest)
    response=asyncio.run(diagnostics.download_support_bundle())
    latest.unlink();latest.symlink_to(new.name)
    app=FastAPI()
    @app.get('/download')
    async def download():return response
    result=TestClient(app).get('/download')
    assert result.status_code==200 and result.content==old.read_bytes()
    assert int(result.headers['content-length'])==len(result.content)
    assert result.headers['cache-control']=='private, no-store'
    assert result.headers['content-type']=='application/gzip'


def test_missing_bundle_download_has_clear_status(monkeypatch,tmp_path):
    from fastapi import HTTPException
    import pytest
    monkeypatch.setattr(diagnostics,'SUPPORT_LATEST',tmp_path/'missing.tar.gz')
    with pytest.raises(HTTPException) as error:asyncio.run(diagnostics.download_support_bundle())
    assert error.value.status_code==404
