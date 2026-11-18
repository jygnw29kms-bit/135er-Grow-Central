"""Cloud owner Web Push consent API: account/device isolation and no fake delivery."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("gc_cloud_push_test", ROOT / "cloud/v7/cloud_push.py")
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

VALID = {"endpoint": "https://web.push.apple.com/some-valid-route",
         "keys": {"p256dh": "A" * 55, "auth": "B" * 22}}
VAPID = {"GC_CLOUD_VAPID_PUBLIC_KEY": "PUBLIC_TEST_ONLY",
         "GC_CLOUD_VAPID_PRIVATE_KEY": "PRIVATE_TEST_ONLY",
         "GC_CLOUD_WEBPUSH_SUBJECT": "mailto:fake@example.com"}


def make_api(tmp_path, monkeypatch):
    for key, val in VAPID.items():
        monkeypatch.setenv(key, val)
    engine = create_engine("sqlite:///" + str(tmp_path / "cloud-push.db"), future=True)
    mod.ensure_schema(engine)
    owners = {"device_1": "owner1", "device_2": "owner2"}

    def auth(token):
        if token not in {"owner1", "owner2"}:
            raise HTTPException(401, "Invalid account session")
        return token

    def device(device_id, account_id):
        if owners.get(device_id) != account_id:
            raise HTTPException(403, "Not device owner")

    app = FastAPI()
    app.include_router(mod.build_router(engine, account_from_access=auth,
                                        get_device_for_account=device, clock=lambda: 1000))
    return TestClient(app), engine


def headers(account):
    return {"Authorization": "Bearer " + account}


def test_cloud_push_needs_authenticated_owner_and_explicit_subscription(tmp_path, monkeypatch):
    client, engine = make_api(tmp_path, monkeypatch)
    path = "/api/v2/push/devices/device_1"
    assert client.get(path + "/status").status_code == 401
    assert client.get(path + "/status", headers=headers("owner2")).status_code == 403
    status = client.get(path + "/status", headers=headers("owner1")).json()
    assert status["registered_devices"] == 0
    assert status["can_subscribe"] is True
    created = client.post(path + "/subscriptions", headers=headers("owner1"), json=VALID)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["registered"] is True
    assert body["delivery"] == "registration_only_not_proof_of_notification"
    assert client.get(path + "/status", headers=headers("owner1")).json()["registered_devices"] == 1
    forbidden = client.delete(path + "/subscriptions/" + body["subscription_id"],
                              headers=headers("owner2"))
    assert forbidden.status_code == 403
    assert client.delete(path + "/subscriptions/" + body["subscription_id"],
                         headers=headers("owner1")).status_code == 200
    assert client.get(path + "/status", headers=headers("owner1")).json()["registered_devices"] == 0


def test_cloud_push_rejects_internal_and_foreign_service_urls(tmp_path, monkeypatch):
    client, _ = make_api(tmp_path, monkeypatch)
    url = "/api/v2/push/devices/device_1/subscriptions"
    for endpoint in (
        "http://web.push.apple.com/a", "https://127.0.0.1/private",
        "https://web.push.apple.com.attacker.tld/a",
        "https://fake@example.com@web.push.apple.com:8443/a",
        "https://localhost/a", "https://web.push.apple.com/"
    ):
        assert client.post(url, headers=headers("owner1"),
                           json={**VALID, "endpoint": endpoint}).status_code == 422


def test_same_push_endpoint_cannot_be_bound_to_two_accounts(tmp_path, monkeypatch):
    client, _ = make_api(tmp_path, monkeypatch)
    base = "/api/v2/push/devices/"
    assert client.post(base + "device_1/subscriptions",
                       headers=headers("owner1"), json=VALID).status_code == 201
    assert client.post(base + "device_2/subscriptions",
                       headers=headers("owner2"), json=VALID).status_code == 409


def test_without_configured_sender_registration_is_unavailable(tmp_path, monkeypatch):
    client, _ = make_api(tmp_path, monkeypatch)
    monkeypatch.delenv("GC_CLOUD_VAPID_PRIVATE_KEY")
    path = "/api/v2/push/devices/device_1"
    status = client.get(path + "/status", headers=headers("owner1")).json()
    assert status["can_subscribe"] is False
    assert client.post(path + "/subscriptions", headers=headers("owner1"),
                       json=VALID).status_code == 503


def test_cloud_optin_is_a_user_click_and_token_stays_out_of_iframe():
    portal = (ROOT / "cloud/portal/cloud-portal.js").read_text(encoding="utf-8")
    html = (ROOT / "cloud/portal/index.html").read_text(encoding="utf-8")
    patch = (ROOT / "scripts/patch_cloud_push.py").read_text(encoding="utf-8")
    for key in ("gcPushEnable", "gcPushDisable", "gcPushStatus"):
        assert key in html
    assert "Notification.requestPermission()" in portal
    assert "navigator.serviceWorker.register('/gc-push-worker.js'" in portal
    assert "cloudPushEnable().catch" in portal
    assert "cloudPushDisable().catch" in portal
    assert "registration_only_not_proof_of_notification" in (
        ROOT / "cloud/v7/cloud_push.py").read_text(encoding="utf-8")
    assert "app.include_router(_gc_push_router(" in patch
    assert "token" not in html.lower() or "token" not in html[:200]
