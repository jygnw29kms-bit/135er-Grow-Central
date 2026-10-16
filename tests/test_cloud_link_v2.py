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
    monkeypatch.setattr(agent_v2.legacy, "LOCAL_API", "http://127.0.0.1:8080")
    monkeypatch.setattr(agent_v2.legacy, "LOCAL_TOKEN", "test")
    client = FakeClient(FakeResponse(200, {"ok": True}))

    payload = asyncio.run(agent_v2.local_status(client))

    assert payload == {"ok": True}
    assert client.calls[0][1]["headers"] == {"X-API-Token": token}


def test_cloud_link_rejects_public_image_placeholder_token(monkeypatch, tmp_path):
    monkeypatch.setattr(agent_v2, "LOCAL_TOKEN_FILE", tmp_path / "missing-token")
    monkeypatch.setattr(agent_v2.legacy, "LOCAL_TOKEN", "test")
    assert agent_v2.local_headers() == {}


def test_cloud_capabilities_reports_incompatible_http_response(monkeypatch):
    monkeypatch.setattr(agent_v2.legacy, "CLOUD_URL", "https://example.invalid")
    client = FakeClient([FakeResponse(404, {}), FakeResponse(404, {})])

    result = asyncio.run(agent_v2.cloud_capabilities(client))

    assert result["reachable"] is True
    assert result["compatible"] is False
    assert result["http_status"] == 404
    assert result["v7_error"] == "http_404"
    assert client.calls[0][0].endswith("/v7/health")
    assert client.calls[1][0].endswith("/api/health")


def test_cloud_capabilities_prefers_v7_control_plane(monkeypatch):
    monkeypatch.setattr(agent_v2.legacy, "CLOUD_URL", "https://example.invalid")
    client = FakeClient(FakeResponse(200, {
        "ok": True,
        "version": 7,
        "admin_mode": "plesk",
    }))

    result = asyncio.run(agent_v2.cloud_capabilities(client))

    assert result["compatible"] is True
    assert result["version"] == 7
    assert result["architecture"] == "v7-control-v2-device"
    assert result["legacy_telemetry"] is False
    assert result["device_pairing"] is True
    assert client.calls[0][0].endswith("/v7/health")
    assert len(client.calls) == 1


def test_cloud_capabilities_accepts_legacy_health_fallback(monkeypatch):
    monkeypatch.setattr(agent_v2.legacy, "CLOUD_URL", "https://example.invalid")
    client = FakeClient([FakeResponse(404, {}), FakeResponse(200, {
        "ok": True,
        "service": "135er-Grow Central Cloud",
        "version": "0.8.0",
        "closed_test_mode": True,
    })])

    result = asyncio.run(agent_v2.cloud_capabilities(client))

    assert result["compatible"] is True
    assert result["version"] == "0.8.0"
    assert result["closed_test_mode"] is True
    assert result["architecture"] == "legacy-v1"
    assert result["legacy_telemetry"] is True


def test_cloud_capabilities_rejects_unrelated_legacy_health_endpoint(monkeypatch):
    monkeypatch.setattr(agent_v2.legacy, "CLOUD_URL", "https://example.invalid")
    client = FakeClient([FakeResponse(404, {}), FakeResponse(200, {
        "ok": True,
        "service": "Some Other Service",
        "version": "1.0.0",
    })])

    result = asyncio.run(agent_v2.cloud_capabilities(client))

    assert result["reachable"] is True
    assert result["compatible"] is False
    assert result["reason"] == "unexpected_cloud_identity"


def test_telemetry_reports_pi_online_even_without_ble_connection(monkeypatch):
    monkeypatch.setattr(agent_v2.legacy, "SITE", "test-site")
    monkeypatch.setattr(agent_v2.legacy, "device_id", lambda: "raspberry-pi-test")
    client = FakeClient(FakeResponse(200, {"connected": False, "online": False}))

    telemetry, local = asyncio.run(agent_v2.telemetry_payload(client))

    assert local["connected"] is False
    assert telemetry["device_online"] is True


def test_telemetry_reports_pi_offline_when_local_api_is_unreachable(monkeypatch):
    monkeypatch.setattr(agent_v2.legacy, "SITE", "test-site")
    monkeypatch.setattr(agent_v2.legacy, "device_id", lambda: "raspberry-pi-test")
    client = FakeClient(FakeResponse(503, {}))

    telemetry, local = asyncio.run(agent_v2.telemetry_payload(client))

    assert local == {}
    assert telemetry["device_online"] is False


def test_cloud_agent_v2_can_be_started_as_systemd_script(tmp_path):
    env = os.environ.copy()
    env.update({
        "GC_CLOUD_ENABLED": "false",
        "GC_CLOUD_URL": "https://example.invalid",
        "GC_CLOUD_CONTACT_STATE": str(tmp_path / "contact.json"),
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


@pytest.mark.parametrize("failure", ["health", "telemetry_404"])
def test_recovery_repeats_contact_handshake(monkeypatch, failure):
    monkeypatch.setattr(agent_v2.legacy, "CLOUD_ENABLED", True)
    monkeypatch.setattr(agent_v2.legacy, "validate_configuration", lambda: None)
    monkeypatch.setattr(agent_v2, "_persist_state", lambda **kw: None)
    monkeypatch.setattr(agent_v2.time, "monotonic", lambda: 0)
    iteration = 0
    reasons = []

    async def capabilities(client):
        nonlocal iteration
        iteration += 1
        return {"compatible": not (failure == "health" and iteration == 2)}

    async def telemetry(client):
        return {}, {}

    async def handshake(client, headers, local, reason):
        reasons.append(reason)

    async def mirror(client, headers, signature):
        return None

    async def sleep(delay):
        if iteration >= 3:
            raise asyncio.CancelledError

    class Response(FakeResponse):
        def raise_for_status(self):
            assert self.is_success

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            return Response(404 if failure == "telemetry_404" and iteration == 2 else 200)

    monkeypatch.setattr(agent_v2, "cloud_capabilities", capabilities)
    monkeypatch.setattr(agent_v2, "telemetry_payload", telemetry)
    monkeypatch.setattr(agent_v2.legacy, "contact_handshake", handshake)
    monkeypatch.setattr(agent_v2.legacy, "mirror_bundle_if_changed", mirror)
    monkeypatch.setattr(agent_v2.asyncio, "sleep", sleep)
    monkeypatch.setattr(agent_v2.httpx, "AsyncClient", Client)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(agent_v2.main())
    assert reasons == ["startup", "reconnect"]


def test_v7_control_plane_skips_legacy_v1_telemetry(monkeypatch):
    monkeypatch.setattr(agent_v2.legacy, "CLOUD_ENABLED", True)
    monkeypatch.setattr(agent_v2.legacy, "validate_configuration", lambda: None)
    monkeypatch.setattr(agent_v2.time, "monotonic", lambda: 0)
    states = []
    monkeypatch.setattr(agent_v2, "_persist_state", lambda **kw: states.append(kw))

    async def capabilities(client):
        return {
            "compatible": True,
            "version": 7,
            "architecture": "v7-control-v2-device",
            "legacy_telemetry": False,
        }

    async def no_pairing(client):
        return None

    async def report(*args, **kwargs):
        return {"state": "unpaired", "sent": False}

    async def local(client):
        return {"ok": True}

    async def legacy_telemetry_must_not_run(client):
        pytest.fail("V7 control plane must not call legacy /api/v1 telemetry")

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
    monkeypatch.setattr(agent_v2, "telemetry_payload", legacy_telemetry_must_not_run)
    monkeypatch.setattr(agent_v2.asyncio, "sleep", sleep)
    monkeypatch.setattr(agent_v2.httpx, "AsyncClient", Client)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(agent_v2.main())

    assert states[-1]["state"] == "connected"
    assert states[-1]["detail"] == "v7 control plane active"
    assert states[-1]["cloud_compatible"] is True
