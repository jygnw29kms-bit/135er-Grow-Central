import asyncio
import base64
import hashlib
import json
import os
from types import SimpleNamespace

import httpx

from local.cloud_link import agent_v2, device_identity, device_pairing, platform_report


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def test_device_identity_is_persistent_and_private(monkeypatch, tmp_path):
    identity_dir = tmp_path / "identity"
    monkeypatch.setattr(device_identity, "IDENTITY_DIR", identity_dir)
    monkeypatch.setattr(device_identity, "PRIVATE_KEY_FILE", identity_dir / "device-ed25519.key")
    monkeypatch.setattr(device_identity, "PUBLIC_KEY_FILE", identity_dir / "device-ed25519.pub")
    monkeypatch.setattr(device_identity, "DEVICE_ID_FILE", identity_dir / "device-id")
    machine_id = tmp_path / "machine-id"
    machine_id.write_text("0123456789abcdef0123456789abcdef\n", encoding="utf-8")
    monkeypatch.setattr(device_identity, "MACHINE_ID_FILE", machine_id)
    monkeypatch.delenv("GC_HARDWARE_GUID", raising=False)
    monkeypatch.delenv("GC_PLATFORM_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("GC_PLATFORM_DEVICE_ID", raising=False)

    first = device_identity.ensure_identity()
    second = device_identity.ensure_identity()

    assert first.hardware_guid == "gc-pi-0123456789abcdef0123456789abcdef"
    assert first.public_key == second.public_key
    assert first.device_id is None
    assert len(_b64decode(first.public_key)) == 32
    assert len(_b64decode((identity_dir / "device-ed25519.key").read_text().strip())) == 32
    assert os.stat(identity_dir / "device-ed25519.key").st_mode & 0o777 == 0o600

    monkeypatch.setattr(device_pairing, "IDENTITY_DIR", identity_dir)
    monkeypatch.setattr(device_pairing, "PAIR_STATE_FILE", identity_dir / "pairing.json")
    device_identity.save_device_id("11111111-2222-3333-4444-555555555555")
    paired = device_identity.ensure_identity()
    assert paired.device_id == "11111111-2222-3333-4444-555555555555"
    assert paired.public_key == first.public_key


def test_pairing_uses_public_key_and_persists_approved_device(monkeypatch, tmp_path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    monkeypatch.setattr(device_pairing, "IDENTITY_DIR", identity_dir)
    monkeypatch.setattr(device_pairing, "PAIR_STATE_FILE", identity_dir / "pairing.json")

    fake_identity = SimpleNamespace(
        hardware_guid="gc-pi-0123456789abcdef",
        public_key="A" * 43,
        device_id=None,
    )
    monkeypatch.setattr(device_pairing, "ensure_identity", lambda: fake_identity)
    saved = []
    monkeypatch.setattr(device_pairing, "save_device_id", saved.append)
    monkeypatch.setattr(device_pairing.time, "time", lambda: 1000)

    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path == "/api/v2/device/authorize":
            payload = json.loads(request.content)
            assert payload["hardware_guid"] == fake_identity.hardware_guid
            assert payload["public_key"] == fake_identity.public_key
            return httpx.Response(200, json={
                "device_code": "secret-device-code",
                "user_code": "ABCD-EFGH",
                "verification_uri": "https://cloud.example/pair",
                "verification_uri_complete": "https://cloud.example/pair?code=ABCD-EFGH",
                "expires_in": 600,
                "interval": 5,
            })
        if request.url.path == "/api/v2/device/pair-status":
            assert json.loads(request.content) == {"device_code": "secret-device-code"}
            return httpx.Response(200, json={
                "status": "approved",
                "device_id": "11111111-2222-3333-4444-555555555555",
            })
        raise AssertionError(request.url.path)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            started = await device_pairing.start_pairing(client, cloud_url="https://cloud.example", name="Test Pi")
            assert started["status"] == "authorization_pending"
            assert "device_code" not in started
            approved = await device_pairing.poll_pairing(client, cloud_url="https://cloud.example")
            assert approved["status"] == "approved"

    asyncio.run(scenario())
    assert saved == ["11111111-2222-3333-4444-555555555555"]
    assert not device_pairing.PAIR_STATE_FILE.exists()
    assert len(calls) == 2


def test_platform_report_signature_matches_cloud_contract(monkeypatch):
    private_key = device_identity.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    device_id = "11111111-2222-3333-4444-555555555555"
    fake_identity = SimpleNamespace(device_id=device_id, private_key=private_key)
    monkeypatch.setattr(platform_report, "ensure_identity", lambda: fake_identity)
    monkeypatch.setattr(platform_report.time, "time", lambda: 1700000000)

    nonce = "nonce-value"
    accepted = {"report": None}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v7/platform/challenge":
            return httpx.Response(200, json={"nonce": nonce})
        if request.url.path == "/api/v1/smarthome/homekit/status":
            return httpx.Response(200, json={"summary": {"total": 3, "published": 2, "pending": 1, "errors": 0}})
        if request.url.path == "/api/v7/platform/report":
            body = json.loads(request.content)
            report = body["report"]
            digest = hashlib.sha256(platform_report.canonical_report(report).encode("utf-8")).hexdigest()
            signed = f"GCPLATFORM1\n{device_id}\n{nonce}\n1700000000\n{digest}".encode("utf-8")
            public_key.verify(_b64decode(body["signature"]), signed)
            assert report["homekit_published"] == 2
            assert report["capabilities"]["local_first"] is True
            assert report["capabilities"]["homekit_cloud_required"] is False
            accepted["report"] = report
            return httpx.Response(200, json={"ok": True, "reported_at": 1700000000})
        raise AssertionError(request.url.path)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await platform_report.send_platform_report(
                client,
                cloud_url="https://cloud.example",
                local_api="http://local.example",
                local_headers={"X-API-Token": "local"},
                capabilities={"diagnostics": True},
            )
            assert result["sent"] is True
            assert result["state"] == "reported"

    asyncio.run(scenario())
    assert accepted["report"] is not None


def test_cloud_link_prefers_approved_device_uuid_but_keeps_legacy_fallback(monkeypatch, tmp_path):
    approved_file = tmp_path / "device-id"
    monkeypatch.setattr(agent_v2, "DEVICE_ID_FILE", approved_file)
    monkeypatch.delenv("GC_DEVICE_ID", raising=False)
    monkeypatch.setattr(agent_v2, "LEGACY_DEVICE_ID", lambda: "raspberry-pi-a1b2c3d4e5f6")

    assert agent_v2.effective_device_id() == "raspberry-pi-a1b2c3d4e5f6"

    approved_file.write_text("11111111-2222-3333-4444-555555555555\n", encoding="utf-8")
    assert agent_v2.effective_device_id() == "11111111-2222-3333-4444-555555555555"

    monkeypatch.setenv("GC_DEVICE_ID", "operator-override")
    assert agent_v2.effective_device_id() == "operator-override"
