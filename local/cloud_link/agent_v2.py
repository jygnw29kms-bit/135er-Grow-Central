"""Grow Central Cloud Link runtime v2.

Runtime-hardening wrapper introduced after the Build 192 Raspberry Pi hardware
validation. It keeps the proven payload/diagnostics helpers from ``agent.py``
while fixing local API authentication and making cloud incompatibility visible
without a 30-second error storm.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import time
from urllib.parse import urlparse

import httpx

from . import agent as legacy

logger = logging.getLogger(__name__)

CLOUD_STATE = legacy.CONTACT_ACK.with_name("cloud-link-runtime.json")
MIN_RETRY = 30
MAX_RETRY = 600


def _persist_state(**values) -> None:
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "cloud_origin": legacy.CLOUD_URL,
        "site_id": legacy.SITE,
        "device_id": legacy.device_id(),
        **values,
    }
    legacy._write_json(CLOUD_STATE, payload)


async def local_status(client: httpx.AsyncClient) -> dict:
    """Read local status with the configured API token.

    Build 192 exposed that the legacy call omitted ``local_headers()`` and
    therefore generated a permanent 401 on a correctly protected Pi API.
    """
    try:
        response = await client.get(
            f"{legacy.LOCAL_API}/api/status",
            headers=legacy.local_headers(),
            timeout=5,
        )
        if response.is_success:
            return response.json()
        logger.warning("Local status returned HTTP %s", response.status_code)
    except Exception as exc:
        logger.warning("Local status unavailable: %s", type(exc).__name__)
    return {}


async def cloud_capabilities(client: httpx.AsyncClient) -> dict:
    """Probe the cloud before entering the telemetry loop."""
    try:
        response = await client.get(f"{legacy.CLOUD_URL}/api/health", timeout=10)
        if not response.is_success:
            return {"reachable": True, "compatible": False, "http_status": response.status_code}
        data = response.json()
        return {
            "reachable": True,
            "compatible": bool(data.get("ok")),
            "version": data.get("version"),
            "service": data.get("service"),
            "closed_test_mode": data.get("closed_test_mode"),
        }
    except Exception as exc:
        return {"reachable": False, "compatible": False, "error": type(exc).__name__}


async def telemetry_payload(client: httpx.AsyncClient) -> tuple[dict, dict]:
    local = await local_status(client)
    return {
        "site_id": legacy.SITE,
        "device_id": legacy.device_id(),
        "ts": datetime.now(timezone.utc).isoformat(),
        "temperature_c": None,
        "humidity_pct": None,
        "vpd_kpa": None,
        "fan_speed_pct": None,
        "device_online": bool(local.get("connected", local.get("ok", False))),
        "extra": {"df100m": local, "closed_test_mode": legacy.CLOSED_TEST, "runtime": "cloud-link-v2"},
    }, local


async def main() -> None:
    if not legacy.CLOUD_ENABLED:
        print("Grow Central Cloud Link disabled / Cloud-Link deaktiviert")
        return

    legacy.validate_configuration()
    headers = {"X-API-Token": legacy.TOKEN} if legacy.TOKEN else {}
    retry_seconds = MIN_RETRY
    connected = False
    ever_connected = False
    last_bundle_signature = None
    next_diag = 0.0
    next_bundle_refresh = 0.0

    async with httpx.AsyncClient() as client:
        while True:
            capabilities = await cloud_capabilities(client)
            if not capabilities.get("compatible"):
                _persist_state(state="degraded", reason="cloud_incompatible_or_unreachable", capabilities=capabilities)
                logger.warning("Cloud unavailable/incompatible: %s; retry in %ss", json.dumps(capabilities), retry_seconds)
                await asyncio.sleep(retry_seconds)
                retry_seconds = min(MAX_RETRY, retry_seconds * 2)
                continue

            now = time.monotonic()
            try:
                telemetry, local = await telemetry_payload(client)
                response = await client.post(
                    f"{legacy.CLOUD_URL}/api/v1/telemetry",
                    json=telemetry,
                    headers=headers,
                    timeout=10,
                )
                if response.status_code == 404:
                    _persist_state(state="degraded", reason="telemetry_endpoint_missing", capabilities=capabilities)
                    logger.error("Cloud API mismatch: telemetry endpoint missing")
                    await asyncio.sleep(MAX_RETRY)
                    connected = False
                    continue
                response.raise_for_status()

                if not connected:
                    reason = "reconnect" if ever_connected else "startup"
                    await legacy.contact_handshake(client, headers, local, reason)
                    connected = True
                    ever_connected = True
                    last_bundle_signature = None
                    next_diag = now + legacy.DIAG_SYNC
                    next_bundle_refresh = now + legacy.BUNDLE_REFRESH

                if now >= next_bundle_refresh:
                    await legacy.request_fresh_bundle(client)
                    next_bundle_refresh = now + legacy.BUNDLE_REFRESH

                if now >= next_diag:
                    full_diag = await legacy.full_local_diagnostics(client)
                    response = await client.post(
                        f"{legacy.CLOUD_URL}/api/v1/diagnostics/snapshot",
                        json=legacy.diagnostic_payload(local, full_diag),
                        headers=headers,
                        timeout=30,
                    )
                    response.raise_for_status()
                    next_diag = now + legacy.DIAG_SYNC

                last_bundle_signature = await legacy.mirror_bundle_if_changed(client, headers, last_bundle_signature)
                retry_seconds = MIN_RETRY
                _persist_state(state="connected", reason="ok", capabilities=capabilities)
            except Exception as exc:
                connected = False
                _persist_state(state="degraded", reason=type(exc).__name__, capabilities=capabilities)
                logger.warning("Cloud cycle failed: %s", type(exc).__name__)
                retry_seconds = min(MAX_RETRY, max(MIN_RETRY, retry_seconds * 2))

            await asyncio.sleep(legacy.SYNC if connected else retry_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main())
