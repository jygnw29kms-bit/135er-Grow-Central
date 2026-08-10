import asyncio

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
