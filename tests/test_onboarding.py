import asyncio
import json
from types import SimpleNamespace

from app.smarthome import onboarding


def test_account_password_is_redacted():
    request = onboarding.AccountDiscoveryRequest(provider="tapo", username="user@example.test", password="secret-value")
    assert "secret-value" not in repr(request)


def test_account_discovery_does_not_return_credentials(monkeypatch):
    request = onboarding.AccountDiscoveryRequest(provider="tapo", username="user@example.test", password="secret-value")

    async def fake_discovery(_request):
        assert _request.password.get_secret_value() == "secret-value"
        return [onboarding.Candidate(provider="tapo", host="192.168.1.20", name="Test Plug", source="test")]

    monkeypatch.setattr(onboarding, "_kasa_account_candidates", fake_discovery)
    result = asyncio.run(onboarding.discover_devices_with_account(request))

    assert result["count"] == 1
    assert result["credentials_stored"] is False
    assert "secret-value" not in repr(result)


def test_all_active_ipv4_networks_are_used(monkeypatch):
    interfaces = [
        {"ifname": "lo", "addr_info": [{"family": "inet", "broadcast": "127.255.255.255"}]},
        {"ifname": "eth0", "addr_info": [{"family": "inet", "broadcast": "192.168.178.255"}]},
        {"ifname": "wlan0", "addr_info": [{"family": "inet", "broadcast": "10.42.0.255"}]},
    ]
    monkeypatch.setattr(onboarding.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=json.dumps(interfaces)))
    assert onboarding._ipv4_discovery_targets() == [("eth0", "192.168.178.255"), ("wlan0", "10.42.0.255")]
