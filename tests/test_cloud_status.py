import asyncio
from datetime import datetime, timedelta, timezone
import subprocess
import threading

import httpx
import pytest

from app import cloud_status
from app.cloud_link_state import connection_state
from local.cloud_link.cloud_url import https_origin


@pytest.mark.parametrize("url", [
    "http://cloud.example", "https://user:secret@cloud.example",
    "https://cloud.example/path", "https://cloud.example?token=secret",
    "https://cloud.example#fragment", "https://cloud.example:99999",
    "https://[broken", "https://cloud.example\n", "https://cloud.example:0",
])
def test_invalid_origins_are_rejected(url):
    with pytest.raises(ValueError):
        https_origin(url)


def test_https_origin_allows_self_hosted_port_and_ipv6():
    assert https_origin("https://[::1]:8443/") == "https://[::1]:8443"


@pytest.mark.parametrize("updated", [None, "bad", "2026-10-09T12:00:00", 123])
def test_invalid_heartbeat_never_claims_connected(updated):
    status = connection_state({"state": "connected", "updated_at": updated}, enabled=True)
    assert status["state"] == "stale"
    assert not status["connected"]


def test_heartbeat_expiry_disabled_mode_and_server_change():
    now = datetime.now(timezone.utc)
    runtime = {"state": "connected", "updated_at": now.isoformat(), "cloud_origin": "https://cloud.example", "retry_seconds": 30}
    assert connection_state(runtime, enabled=True, now=now)["connected"]
    assert connection_state(runtime, enabled=True, now=now + timedelta(minutes=10))["stale"]
    assert not connection_state(runtime, enabled=False, now=now)["connected"]
    assert connection_state(runtime, enabled=True, origin="https://other.example", now=now)["stale"]
    assert connection_state(runtime, enabled=True, now=now - timedelta(minutes=5))["stale"]
    runtime["retry_seconds"] = 3600
    assert connection_state(runtime, enabled=True, now=now + timedelta(hours=1))["connected"]


@pytest.mark.parametrize("error", [FileNotFoundError(), subprocess.TimeoutExpired("systemctl", 3)])
def test_missing_or_timed_out_systemd_is_not_active(monkeypatch, error):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(cloud_status.subprocess, "run", fail)
    assert cloud_status._service_active() is False


def test_status_checks_service_off_event_loop_and_validates_identity(monkeypatch):
    thread = threading.get_ident()
    monkeypatch.setattr(cloud_status, "_read_env", lambda: {"GC_CLOUD_ENABLED": "true", "GC_CLOUD_URL": "https://cloud.example"})
    monkeypatch.setattr(cloud_status, "_read_runtime", lambda: {
        "state": "connected", "updated_at": datetime.now(timezone.utc).isoformat(),
        "cloud_origin": "https://cloud.example",
    })
    def active():
        assert threading.get_ident() != thread
        return True
    monkeypatch.setattr(cloud_status, "_service_active", active)
    async def handler(request):
        return httpx.Response(200, json={"ok": True, "service": "Unrelated service"})
    client_class = httpx.AsyncClient
    monkeypatch.setattr(cloud_status.httpx, "AsyncClient", lambda **kw: client_class(transport=httpx.MockTransport(handler), **kw))
    status = asyncio.run(cloud_status.cloud_status())
    assert status["connected"] is True
    assert status["health_reachable"] is False


def test_invalid_origin_is_not_probed_or_exposed(monkeypatch):
    monkeypatch.setattr(cloud_status, "_read_env", lambda: {"GC_CLOUD_ENABLED": "true", "GC_CLOUD_URL": "https://user:secret@cloud.example"})
    monkeypatch.setattr(cloud_status, "_read_runtime", lambda: {"state": "connected", "cloud_origin": "https://user:secret@cloud.example"})
    monkeypatch.setattr(cloud_status, "_service_active", lambda: True)
    def unexpected(**kw):
        pytest.fail("Invalid cloud address must not be probed")
    monkeypatch.setattr(cloud_status.httpx, "AsyncClient", unexpected)
    status = asyncio.run(cloud_status.cloud_status())
    assert status["state"] == "invalid_configuration"
    assert not status["connected"]
    assert "secret" not in str(status)
