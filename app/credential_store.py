"""Encrypted server-side credential store for local integrations.

Secrets stay on the Raspberry Pi under ``/var/lib/135er-grow-central``.  The
encrypted payload and its appliance-local key both use mode 0600 and are never
included in public API responses or support bundles.  File permissions remain
the primary protection; encryption also prevents accidental plaintext leaks.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

STORE_PATH = Path(os.getenv("GC_CREDENTIAL_STORE", "/var/lib/135er-grow-central/credentials.json"))
KEY_PATH = Path(os.getenv("GC_CREDENTIAL_KEY", "/var/lib/135er-grow-central/credentials.key"))


def _fernet(*, create: bool) -> Fernet | None:
    if KEY_PATH.is_symlink():
        return None
    try:
        key = KEY_PATH.read_bytes().strip()
    except FileNotFoundError:
        if not create:
            return None
        KEY_PATH.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
        key = Fernet.generate_key()
        try:
            descriptor = os.open(KEY_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            if KEY_PATH.is_symlink():
                return None
            key = KEY_PATH.read_bytes().strip()
        else:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(key + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
    except OSError:
        return None
    try:
        os.chmod(KEY_PATH, 0o600)
        return Fernet(key)
    except (OSError, ValueError):
        return None


def _read() -> dict[str, Any]:
    if not STORE_PATH.exists() or STORE_PATH.is_symlink():
        return {}
    try:
        raw = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    if raw.get("format") != "fernet-v1":
        # Read the Build <=68 plaintext format once so it can be migrated by
        # the next successful write without breaking existing installations.
        return raw
    token = raw.get("token")
    cipher = _fernet(create=False)
    if not isinstance(token, str) or cipher is None:
        return {}
    try:
        payload = json.loads(cipher.decrypt(token.encode("ascii")).decode("utf-8"))
    except (InvalidToken, UnicodeError, json.JSONDecodeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write(payload: dict[str, Any]) -> None:
    cipher = _fernet(create=True)
    if cipher is None:
        raise OSError("credential encryption key is unavailable")
    token = cipher.encrypt(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).decode("ascii")
    envelope = {"format": "fernet-v1", "token": token}
    STORE_PATH.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".credentials-", dir=STORE_PATH.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(envelope, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, STORE_PATH)
        os.chmod(STORE_PATH, 0o600)
    finally:
        Path(temporary).unlink(missing_ok=True)


def get_provider_config(provider: str) -> dict[str, Any] | None:
    row = _read().get(provider)
    return dict(row) if isinstance(row, dict) else None


def get_credentials(provider: str) -> tuple[str, str] | None:
    row = get_provider_config(provider)
    if row is None:
        return None
    username = str(row.get("username") or "").strip()
    password = str(row.get("password") or "")
    if not username or not password:
        return None
    return username, password


def set_credentials(provider: str, username: str, password: str, **metadata: Any) -> None:
    username = username.strip()
    if not username or not password:
        raise ValueError("username and password are required")
    payload = _read()
    payload[provider] = {**metadata, "username": username, "password": password}
    _write(payload)


def delete_credentials(provider: str) -> bool:
    payload = _read()
    if provider not in payload:
        return False
    del payload[provider]
    _write(payload)
    return True


def configured_providers() -> list[str]:
    return sorted(key for key, value in _read().items() if isinstance(value, dict) and value.get("username") and value.get("password"))
