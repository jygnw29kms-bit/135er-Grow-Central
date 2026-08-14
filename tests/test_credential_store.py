import asyncio
import json
import stat

from app import credential_store
from app.smarthome import fritz_onboarding


def _paths(monkeypatch, tmp_path):
    store = tmp_path / "credentials.json"
    key = tmp_path / "credentials.key"
    monkeypatch.setattr(credential_store, "STORE_PATH", store)
    monkeypatch.setattr(credential_store, "KEY_PATH", key)
    return store, key


def test_credentials_are_encrypted_and_roundtrip(monkeypatch, tmp_path):
    store, key = _paths(monkeypatch, tmp_path)

    credential_store.set_credentials(
        "fritz",
        "grow-central-user",
        "very-secret-fritz-password",
        host="fritz.box",
    )

    raw = store.read_bytes()
    assert b"grow-central-user" not in raw
    assert b"very-secret-fritz-password" not in raw
    assert json.loads(raw)["format"] == "fernet-v1"
    assert credential_store.get_credentials("fritz") == (
        "grow-central-user",
        "very-secret-fritz-password",
    )
    assert credential_store.get_provider_config("fritz")["host"] == "fritz.box"
    assert stat.S_IMODE(store.stat().st_mode) == 0o600
    assert stat.S_IMODE(key.stat().st_mode) == 0o600


def test_delete_credentials_removes_provider(monkeypatch, tmp_path):
    _paths(monkeypatch, tmp_path)
    credential_store.set_credentials("fritz", "user", "password", host="fritz.box")

    assert credential_store.delete_credentials("fritz") is True
    assert credential_store.get_credentials("fritz") is None
    assert credential_store.delete_credentials("fritz") is False


def test_legacy_plaintext_store_is_migrated_on_write(monkeypatch, tmp_path):
    store, _key = _paths(monkeypatch, tmp_path)
    store.write_text(
        json.dumps({"fritz": {"username": "legacy", "password": "old-secret", "host": "fritz.box"}}),
        encoding="utf-8",
    )
    assert credential_store.get_credentials("fritz") == ("legacy", "old-secret")

    credential_store.set_credentials("fritz", "new-user", "new-secret", host="192.168.178.1")

    raw = store.read_bytes()
    assert b"new-user" not in raw
    assert b"new-secret" not in raw
    assert json.loads(raw)["format"] == "fernet-v1"
    assert credential_store.get_provider_config("fritz") == {
        "host": "192.168.178.1",
        "username": "new-user",
        "password": "new-secret",
    }


def test_credential_store_rejects_symlinked_key(monkeypatch, tmp_path):
    _store, key = _paths(monkeypatch, tmp_path)
    target = tmp_path / "unrelated"
    target.write_text("do-not-touch", encoding="utf-8")
    key.symlink_to(target)

    try:
        credential_store.set_credentials("fritz", "user", "password")
    except OSError:
        pass
    else:
        raise AssertionError("symlinked credential key must be rejected")
    assert target.read_text(encoding="utf-8") == "do-not-touch"


def test_fritz_actions_reuse_stored_login_without_exposing_password(monkeypatch):
    stored = {
        "host": "192.168.178.1",
        "username": "grow-central-user",
        "password": "secret-value",
    }
    monkeypatch.setattr(fritz_onboarding, "get_provider_config", lambda _provider: stored)

    request = fritz_onboarding.FritzLoginRequest(import_devices=False)
    assert fritz_onboarding._request_credentials(request) == (
        "192.168.178.1",
        "grow-central-user",
        "secret-value",
        False,
    )
    status = asyncio.run(fritz_onboarding.fritz_credentials_status())
    assert status == {
        "configured": True,
        "host": "192.168.178.1",
        "username": "grow-central-user",
    }
    assert "password" not in status
