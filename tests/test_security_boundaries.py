import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import _classify_ble_name, app
from app.smarthome.onboarding import _lan_host
from cloud.app.config import settings
from cloud.app.main import CommandPayload, TelemetryPayload, check_token


def test_ble_state_change_fails_closed_without_local_token(monkeypatch):
    monkeypatch.delenv("GC_LOCAL_API_TOKEN", raising=False)
    response = TestClient(app).post("/api/connect", json={"address": "AA:BB:CC:DD:EE:FF"})
    assert response.status_code == 503


def test_cloud_token_placeholder_fails_closed():
    previous = settings.cloud_api_token
    try:
        settings.cloud_api_token = "CHANGE_ME_TO_AT_LEAST_32_RANDOM_CHARACTERS"
        with pytest.raises(HTTPException) as error:
            check_token("CHANGE_ME_TO_AT_LEAST_32_RANDOM_CHARACTERS")
        assert error.value.status_code == 503
    finally:
        settings.cloud_api_token = previous


def test_cloud_token_accepts_matching_strong_value():
    previous = settings.cloud_api_token
    token = "a-secure-test-token-with-more-than-32-characters"
    try:
        settings.cloud_api_token = token
        assert check_token(token) is None
    finally:
        settings.cloud_api_token = previous


def test_cloud_payloads_are_bounded():
    with pytest.raises(ValidationError):
        CommandPayload(site_id="garage", target="df100m", action="set_speed", value=101)
    with pytest.raises(ValidationError):
        TelemetryPayload(site_id="../invalid", device_id="pi", ts="2026-08-10T00:00:00Z")


def test_loopback_is_not_a_discoverable_lan_device():
    with pytest.raises(HTTPException):
        _lan_host("127.0.0.1")


def test_ble_devices_are_not_mislabeled_as_df100m():
    assert _classify_ble_name("Random Headphones") == "generic_ble"
    assert _classify_ble_name("MZ_MZF002") == "df100m_candidate"
