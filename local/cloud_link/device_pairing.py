"""Grow Central Pi-side device authorization flow.

This module implements the cloud's existing device-code pairing contract. It
never stores account credentials on the Pi. The user approves the short code
through the HTTPS verification URL; after approval only the cloud device ID is
persisted next to the local Ed25519 identity.
"""
from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any

import httpx

try:
    from .device_identity import IDENTITY_DIR, ensure_identity, save_device_id
except ImportError:
    from device_identity import IDENTITY_DIR, ensure_identity, save_device_id  # type: ignore[no-redef]

PAIR_STATE_FILE = IDENTITY_DIR / "pairing.json"


def _write_state(payload: dict[str, Any]) -> None:
    IDENTITY_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = PAIR_STATE_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    temp.chmod(0o600)
    temp.replace(PAIR_STATE_FILE)


def load_state() -> dict[str, Any]:
    try:
        value = json.loads(PAIR_STATE_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def clear_state() -> None:
    try:
        PAIR_STATE_FILE.unlink()
    except FileNotFoundError:
        pass


async def start_pairing(client: httpx.AsyncClient, *, cloud_url: str, name: str) -> dict[str, Any]:
    identity = ensure_identity()
    if identity.device_id:
        return {"status": "already_paired", "device_id": identity.device_id}

    response = await client.post(
        f"{cloud_url.rstrip('/')}/api/v2/device/authorize",
        json={
            "hardware_guid": identity.hardware_guid,
            "public_key": identity.public_key,
            "name": (name.strip() or "GrowCentral")[:120],
        },
        timeout=10,
    )
    response.raise_for_status()
    body = response.json()
    now = int(time.time())
    state = {
        "status": "authorization_pending",
        "device_code": str(body["device_code"]),
        "user_code": str(body["user_code"]),
        "verification_uri": str(body["verification_uri"]),
        "verification_uri_complete": str(body["verification_uri_complete"]),
        "interval": max(5, int(body.get("interval", 5))),
        "created_at": now,
        "expires_at": now + max(60, int(body.get("expires_in", 600))),
    }
    _write_state(state)
    return {key: value for key, value in state.items() if key != "device_code"}


async def poll_pairing(client: httpx.AsyncClient, *, cloud_url: str) -> dict[str, Any]:
    state = load_state()
    device_code = str(state.get("device_code", ""))
    if not device_code:
        return {"status": "not_started"}
    if int(state.get("expires_at", 0)) <= int(time.time()):
        clear_state()
        return {"status": "expired"}

    response = await client.post(
        f"{cloud_url.rstrip('/')}/api/v2/device/pair-status",
        json={"device_code": device_code},
        timeout=10,
    )
    if response.status_code == 202:
        return {
            "status": "authorization_pending",
            "user_code": state.get("user_code"),
            "verification_uri": state.get("verification_uri"),
            "verification_uri_complete": state.get("verification_uri_complete"),
            "expires_at": state.get("expires_at"),
            "interval": state.get("interval", 5),
        }
    if response.status_code == 400:
        detail = ""
        try:
            detail = str(response.json().get("detail", ""))
        except (ValueError, AttributeError):
            pass
        if detail in {"expired_token", "already_consumed"}:
            clear_state()
            return {"status": "expired" if detail == "expired_token" else "consumed"}
    response.raise_for_status()
    body = response.json()
    if body.get("status") != "approved" or not body.get("device_id"):
        raise ValueError("invalid pairing approval payload")
    save_device_id(str(body["device_id"]))
    clear_state()
    return {"status": "approved", "device_id": str(body["device_id"])}
