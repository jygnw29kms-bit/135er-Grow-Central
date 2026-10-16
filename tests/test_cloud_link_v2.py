from __future__ import annotations

import asyncio
import os
import subprocess
import sys

import pytest

from local.cloud_link import agent_v2


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    @property
    def is_success(self):
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if isinstance(self.response, list):
            return self.response.pop(0)
        return self.response


def test_local_status_uses_per_device_local_api_token(monkeypatch, tmp_path):
    token = "a-local-device-token-with-more-than-32-characters"
    token_file = tmp_path / "local-api-token"
    token_file.write_text(token + "\n", encoding="utf-8")
    monkeypatch.setattr(agent_v2, "LOCAL_TOKEN_FILE", token_file)
    monkeypatch.setattr(agent_v2, "LOCAL_API", "http://127.0.0.1:8080")
    monkeypatch.setattr(agent_v2, "LOCAL_TOKEN", "test")
    client = FakeClient(FakeResponse(200, {"ok": True}))

    payload = asyncio.run(agent_v2.local_status(client))

    assert payload == {"ok": True}
    assert client.calls[0][1]["headers"] == {"X-API-Token": token}


def test_cloud_link_rejects_public_image_placeholder_token(monkeypatch, tmp_path):
    monkeypatch.setattr(agent_v2, "LOCAL_TOKEN_FILE", tmp_path / "missing-token")
    monkeypatch.setattr(agent_v2, "LOCAL_TOKEN", "test")
    assert agent_v2.local_headers() == {}


def test_cloud_capabilities_reports_v7_http_failure_without_old_fallback(monkeypatch):
    monkeypatch.setattr(agent_v2, "CLOUD_URL", "https://example.invalid")
    client = FakeClient(FakeResponse(404, {}))

    result = asyncio.run(agent_v2.cloud_capabilities(client))

    assert result == {
        "reachable": True,
        "compatible": False,
        "http_status": 404,
        "reason": "v7_health_unavailable",
    }
    assert len(client.calls) == 1
    assert client.calls[0][0].endswith("/v7/health")


def test_cloud_capabilities_accepts_current_v7_control_plane(monkeypatch):
    monkeypatch.setattr(agent_v2, "CLOUD_URL", "https://example.invalid")
    client = FakeClient(FakeResponse(200, {"ok": True, "version": 7, "admin_mode": "plesk"}))

    result = asyncio.run(agent_v2.cloud_capabilities(client))

    assert result["compatible"] is True
    assert result["version"] == 7
    assert result["architecture"] == "v7-control-v2-device"
    assert result["device_pairing"] is True
    assert result["platform_reports"] is True
    assert "legacy_telemetry" not in result
    assert len(client.calls) == 1


def test_cloud_capabilities_rejects_malformed_v7_identity(monkeypatch):
    monkeypatch.setattr(agent_v2, "CLOUD_URL", "https://example.invalid")
    client = FakeClient(FakeResponse(200, {"ok": True, "version": "7"}))

    result = asyncio.run(agent_v2.cloud_capabilities(client))

    assert result["reachable"] is True
    assert result["compatible"] is False
    assert result["reason"] == "unexpected_v7_health"


def test_validate_configuration_requires_https_cloud_and_loopback_local(monkeypatch):
    monkeypatch.setattr(agent_v2, "CLOUD_URL", "https://cloud.example")
    monkeypatch.setattr(agent_v2, "LOCAL_API", "http://127.0.0.1:8080")
    agent_v2.validate_configuration()

    monkeypatch.setattr(agent_v2, "LOCAL_API", "http://192.168.1.10:8080")
    with pytest.raises(RuntimeError, match="loopback"):
        agent_v2.validate_configuration()


def test_cloud_agent_v2_can_be_started_as_systemd_script(tmp_path):
    env = os.environ.copy()
    env.update({
        "GC_CLOUD_ENABLED": "false",
        "GC_CLOUD_URL": "https://example.invalid",
        "GC_CLOUD_STATE": str(tmp_path / "cloud-link-status.json"),
    })
    result = subprocess.run(
        [sys.executable, "local/cloud_link/agent_v2.py"],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Cloud Link disabled" in result.stdout


def test_v7_main_reports_current_state_without_v1_transport(monkeypatch):
    monkeypatch.setattr(agent_v2, "CLOUD_ENABLED", True)
    monkeypatch.setattr(agent_v2, "CLOUD_URL", "https://example.invalid")
    monkeypatch.setattr(agent_v2, "LOCAL_API", "http://127.0.0.1:8080")
    monkeypatch.setattr(agent_v2, "validate_configuration", lambda: None)
    monkeypatch.setattr(agent_v2.time, "monotonic", lambda: 0)
    states = []
    monkeypatch.setattr(agent_v2, "_persist_state", lambda **kw: states.append(kw))

    async def capabilities(client):
        return {
            "compatible": True,
            "version": 7,
            "architecture": "v7-control-v2-device",
            "platform_reports": True,
            "device_pairing": True,
        }

    async def no_pairing(client):
        return None

    async def report(*args, **kwargs):
        return {"state": "unpaired", "sent": False}

    async def local(client):
        return {"ok": True}

    async def sleep(delay):
        raise asyncio.CancelledError

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr(agent_v2, "cloud_capabilities", capabilities)
    monkeypatch.setattr(agent_v2, "_poll_pending_pairing", no_pairing)
    monkeypatch.setattr(agent_v2, "send_platform_report", report)
    monkeypatch.setattr(agent_v2, "local_status", local)
    monkeypatch.setattr(agent_v2.asyncio, "sleep", sleep)
    monkeypatch.setattr(agent_v2.httpx, "AsyncClient", Client)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(agent_v2.main())

    assert states[-1]["state"] == "connected"
    assert states[-1]["detail"] == "v7 control plane active"
    assert states[-1]["cloud_compatible"] is True
    assert states[-1]["local_online"] is True
