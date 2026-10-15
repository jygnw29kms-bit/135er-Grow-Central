"""Signed Pi -> Grow Central platform status reporting.

The reporter is deliberately optional and local-first. Missing cloud pairing,
network failures or rejected reports never block local automation/HomeKit.
It reuses the Grow Central Ed25519 cloud-device identity; it never creates a
second identity just for status reporting.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

IDENTITY_DIR = Path(os.getenv("GC_CLOUD_IDENTITY_DIR", "/var/lib/135er-grow-central/cloud-identity"))
DEVICE_ID_FILE = Path(os.getenv("GC_CLOUD_DEVICE_ID_FILE", str(IDENTITY_DIR / "device-id")))
PRIVATE_KEY_FILE = Path(os.getenv("GC_CLOUD_DEVICE_KEY_FILE", str(IDENTITY_DIR / "device-ed25519.key")))
VERSION_FILE = Path("/opt/135er-grow-central/VERSION")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _b64decode(value: str) -> bytes:
    value = value.strip()
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def identity() -> tuple[str, Ed25519PrivateKey] | None:
    """Load the already-paired cloud identity, without generating credentials."""
    device_id = os.getenv("GC_PLATFORM_DEVICE_ID", "").strip() or _read(DEVICE_ID_FILE)
    key_text = os.getenv("GC_PLATFORM_PRIVATE_KEY", "").strip() or _read(PRIVATE_KEY_FILE)
    if len(device_id) != 36 or not key_text:
        return None
    try:
        raw = _b64decode(key_text)
        if len(raw) != 32:
            return None
        return device_id, Ed25519PrivateKey.from_private_bytes(raw)
    except (ValueError, TypeError):
        return None


def canonical_report(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


async def _homekit_summary(client: httpx.AsyncClient, local_api: str, headers: dict[str, str]) -> dict[str, int]:
    try:
        response = await client.get(
            f"{local_api.rstrip('/')}/api/v1/smarthome/homekit/status",
            headers=headers,
            timeout=5,
        )
        if response.is_success:
            summary = response.json().get("summary", {})
            return {
                "total": max(0, int(summary.get("total", 0))),
                "published": max(0, int(summary.get("published", 0))),
                "pending": max(0, int(summary.get("pending", 0))),
                "errors": max(0, int(summary.get("errors", 0))),
            }
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        pass
    return {"total": 0, "published": 0, "pending": 0, "errors": 0}


async def send_platform_report(
    client: httpx.AsyncClient,
    *,
    cloud_url: str,
    local_api: str,
    local_headers: dict[str, str],
    capabilities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send one authenticated compatibility/status report.

    Returns a compact state dictionary instead of raising for normal pairing or
    connectivity conditions, so callers can keep all local services running.
    """
    loaded = identity()
    if loaded is None:
        return {"state": "unpaired", "sent": False, "reason": "cloud_device_identity_missing"}

    device_id, private_key = loaded
    origin = cloud_url.rstrip("/")
    try:
        challenge = await client.post(
            f"{origin}/api/v7/platform/challenge",
            json={"device_id": device_id},
            timeout=10,
        )
        if challenge.status_code == 404:
            return {"state": "unpaired", "sent": False, "reason": "device_not_registered"}
        challenge.raise_for_status()
        challenge_body = challenge.json()
        nonce = str(challenge_body["nonce"])

        homekit = await _homekit_summary(client, local_api, local_headers)
        report: dict[str, Any] = {
            "local_version": _read(VERSION_FILE) or "unknown",
            "device_api": "local-api-v1",
            "device_protocol": "gc-device-v1",
            "homekit_schema": 1,
            "homekit_total": homekit["total"],
            "homekit_published": homekit["published"],
            "homekit_pending": homekit["pending"],
            "homekit_errors": homekit["errors"],
            "capabilities": {
                "local_first": True,
                "homekit_cloud_required": False,
                "cloud_link_runtime": "v2",
                **(capabilities or {}),
            },
        }
        timestamp = int(time.time())
        digest = hashlib.sha256(canonical_report(report).encode("utf-8")).hexdigest()
        signed = f"GCPLATFORM1\n{device_id}\n{nonce}\n{timestamp}\n{digest}".encode("utf-8")
        signature = _b64encode(private_key.sign(signed))
        response = await client.post(
            f"{origin}/api/v7/platform/report",
            json={
                "device_id": device_id,
                "nonce": nonce,
                "timestamp": timestamp,
                "signature": signature,
                "report": report,
            },
            timeout=10,
        )
        response.raise_for_status()
        body = response.json()
        return {
            "state": "reported",
            "sent": True,
            "reported_at": body.get("reported_at"),
            "homekit": homekit,
        }
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
        return {"state": "degraded", "sent": False, "reason": type(exc).__name__}
