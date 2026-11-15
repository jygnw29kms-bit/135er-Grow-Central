"""Ensure USB/BLE onboarding expose the same broker status without leaking credentials."""
import asyncio
from app.provisioning.broker import broker_info_payload


def test_available_broker_returns_hosts_only():
    def request(action):
        assert action == "info"
        return {"ok": True, "hosts": ["192.0.2.10"], "secret": "private"}
    result = asyncio.run(broker_info_payload(request))
    assert result == {"ready": True, "hosts": ["192.0.2.10"]}


def test_offline_broker_is_graceful():
    def request(_):
        raise OSError("not connected")
    result = asyncio.run(broker_info_payload(request))
    assert result["ready"] is False
    assert result["hosts"] == []
    assert "message" in result
