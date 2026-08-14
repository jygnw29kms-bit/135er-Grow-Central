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
    assert "--show-secrets no" in source
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
