"""Small server-side credential store for local integrations.

Secrets are stored only on the Raspberry Pi under /var/lib/135er-grow-central
with mode 0600. They are never exposed by public API responses.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

STORE_PATH = Path(os.getenv("GC_CREDENTIAL_STORE", "/var/lib/135er-grow-central/credentials.json"))


def _read() -> dict[str, Any]:
    if not STORE_PATH.exists():
        return {}
    try:
        raw = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def get_credentials(provider: str) -> tuple[str, str] | None:
    row = _read().get(provider)
    if not isinstance(row, dict):
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
    payload[provider] = {"username": username, "password": password, **metadata}
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = STORE_PATH.with_suffix(".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, STORE_PATH)
    os.chmod(STORE_PATH, 0o600)


def configured_providers() -> list[str]:
    return sorted(key for key, value in _read().items() if isinstance(value, dict) and value.get("username") and value.get("password"))
