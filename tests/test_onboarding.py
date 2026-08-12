import asyncio
import json
from types import SimpleNamespace

from app.smarthome import onboarding
from app.main import app


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


def test_onboarding_routes_have_exact_public_prefix():
    paths = app.openapi()["paths"]
    assert "/api/v1/smarthome/onboarding/discover" in paths
    assert "/api/v1/smarthome/onboarding/discover/account" in paths
    assert not any("/api/v1/smarthome/api/v1/" in path for path in paths)


def test_plain_tp_link_discovery_scans_every_active_network(monkeypatch):
    calls = []

    class Discover:
        @staticmethod
        async def discover(**kwargs):
            calls.append(kwargs)
            return {}

    monkeypatch.setattr(onboarding, "_ipv4_discovery_targets", lambda: [("eth0", "192.168.1.255"), ("wlan0", "10.42.0.255")])
    monkeypatch.setitem(__import__("sys").modules, "kasa", SimpleNamespace(Discover=Discover))
    assert asyncio.run(onboarding._kasa_candidates(3)) == []
    assert [(call["interface"], call["target"]) for call in calls] == [("eth0", "192.168.1.255"), ("wlan0", "10.42.0.255")]


def test_tapo_account_is_verified_with_device_update(monkeypatch):
    updates = []

    class Device:
        alias = "Tapo Test"
        model = "P110"
        device_id = "device-1"
        device_type = "plug"

        async def update(self):
            updates.append(True)

    class Discover:
        @staticmethod
        async def discover(**_kwargs):
            return {"192.168.1.20": Device()}

    class Credentials:
        def __init__(self, username, password):
            assert username == "user@example.test"
            assert password == "secret-value"

    monkeypatch.setattr(onboarding, "_ipv4_discovery_targets", lambda: [("eth0", "192.168.1.255")])
    monkeypatch.setitem(__import__("sys").modules, "kasa", SimpleNamespace(Discover=Discover, Credentials=Credentials))
    request = onboarding.AccountDiscoveryRequest(provider="tapo", username="user@example.test", password="secret-value")
    rows = asyncio.run(onboarding._kasa_account_candidates(request))
    assert updates == [True]
    assert rows[0].metadata["authentication"] == "verified-for-this-request"
