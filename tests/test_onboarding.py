import asyncio
import importlib
import json
from types import SimpleNamespace

from app.smarthome import onboarding
from app.smarthome.adapters.base import AdapterError
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


def test_tapo_login_stores_verified_account_and_imports_name_room(monkeypatch):
    stored = {}
    imported = []
    candidate = onboarding.Candidate(
        provider="tapo", host="192.168.1.20", name="Grow Lüfter",
        source="test", native_id="DEVICE-123",
        metadata={"model": "P110", "device_type": "plug", "room": "Growzelt"},
    )

    async def fake_discovery(request):
        assert request.username == "user@example.test"
        assert request.password.get_secret_value() == "secret-value"
        return [candidate]

    def fake_store(provider, username, password, **metadata):
        stored.update(provider=provider, username=username, password=password, **metadata)

    class Registry:
        def upsert(self, device):
            imported.append(device)

    monkeypatch.setattr(onboarding, "_kasa_account_candidates", fake_discovery)
    monkeypatch.setattr(onboarding, "set_credentials", fake_store)
    monkeypatch.setattr(onboarding, "get_provider_config", lambda _provider: stored or None)
    monkeypatch.setattr(onboarding.DeviceRegistry, "from_env", lambda: Registry())
    monkeypatch.setattr(onboarding, "_ipv4_discovery_targets", lambda: [("eth0", "192.168.1.255")])

    request = onboarding.TapoLoginRequest(
        username="user@example.test", password="secret-value", import_devices=True,
    )
    result = asyncio.run(onboarding.tapo_login(request))

    assert result["credentials_stored"] is True
    assert result["cloud_inventory"] is False
    assert result["networks_scanned"] == 1
    assert imported[0].id == "tapo-device-123"
    assert imported[0].name == "Grow Lüfter"
    assert imported[0].metadata["room"] == "Growzelt"
    assert imported[0].approved is True
    assert imported[0].writable is True
    assert "secret-value" not in repr(result)


def test_tapo_stored_login_is_reused_and_status_never_exposes_password(monkeypatch):
    stored = {"username": "user@example.test", "password": "secret-value", "transport": "local-authenticated"}
    monkeypatch.setattr(onboarding, "get_provider_config", lambda _provider: stored)

    assert onboarding._tapo_request_credentials(onboarding.TapoLoginRequest()) == (
        "user@example.test", "secret-value", False,
    )
    status = asyncio.run(onboarding.tapo_credentials_status())
    assert status == {
        "configured": True,
        "username": "user@example.test",
        "transport": "local-authenticated",
    }
    assert "password" not in status


def test_smarthome_overview_cache_and_forced_refresh(monkeypatch):
    router = importlib.import_module("app.smarthome.router")
    calls = []
    device = SimpleNamespace(id="plug", name="Plug", adapter="test", approved=True, writable=False, metadata={})
    monkeypatch.setattr(router, "_registry", lambda: SimpleNamespace(list=lambda: [device]))

    async def fake_row(_device):
        calls.append(True)
        return {"id": "plug", "online": True, "state": {"on": False, "power_w": 1.0, "energy_wh": 2.0}}

    monkeypatch.setattr(router, "_overview_row", fake_row)
    router._overview_cache = None

    async def scenario():
        first = await router.device_overview()
        second = await router.device_overview()
        refreshed = await router.device_overview(refresh=True)
        return first, second, refreshed

    first, second, refreshed = asyncio.run(scenario())
    assert first is second
    assert refreshed["summary"]["power_w"] == 1.0
    assert len(calls) == 2


def test_registered_fritz_device_remains_visible_without_live_credentials(monkeypatch):
    router = importlib.import_module("app.smarthome.router")
    device = SimpleNamespace(
        id="fritz-lampe", name="Lampe", adapter="fritz",
        approved=True, writable=True, metadata={"product": "FRITZ!DECT 210"},
    )

    def unavailable_adapter(_device):
        raise AdapterError("FRITZ!Box credentials are not configured")

    monkeypatch.setattr(router, "build_switch_adapter", unavailable_adapter)
    row = asyncio.run(router._overview_row(device))

    assert row["id"] == "fritz-lampe"
    assert row["online"] is False
    assert row["error"] == "FRITZ!Box credentials are not configured"
