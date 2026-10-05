"""Grow Central Cloud Link runtime v2."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import time

import httpx

try:
    from . import agent as legacy
except ImportError:
    import agent as legacy  # type: ignore[no-redef]

logger = logging.getLogger(__name__)

CLOUD_STATE = legacy.CONTACT_ACK.with_name("cloud-link-status.json")
LOCAL_TOKEN_FILE = Path("/var/lib/135er-grow-central/local-api-token")
MIN_RETRY = 30
MAX_RETRY = 600
EXPECTED_CLOUD_SERVICE = "135er-Grow Central Cloud"


def _persist_state(**values) -> None:
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "cloud_origin": legacy.CLOUD_URL,
        "site_id": legacy.SITE,
        "device_id": legacy.device_id(),
        **values,
    }
    legacy._write_json(CLOUD_STATE, payload)


def local_headers() -> dict[str, str]:
    """Read the per-device token created by the local runtime."""
    try:
        token = LOCAL_TOKEN_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        token = ""
    if len(token) < 32:
        configured = legacy.LOCAL_TOKEN.strip()
        token = configured if len(configured) >= 32 and configured.lower() != "test" else ""
    return {"X-API-Token": token} if token else {}


# Legacy diagnostic helpers resolve this global at call time. Replacing it here
# keeps all local cloud-link calls on the same per-device credential.
legacy.local_headers = local_headers


async def local_status(client: httpx.AsyncClient) -> dict:
    try:
        response = await client.get(
            f"{legacy.LOCAL_API}/api/status",
            headers=local_headers(),
            timeout=5,
        )
        if response.is_success:
            payload = response.json()
            return payload if isinstance(payload, dict) else {}
        logger.warning("Local status returned HTTP %s", response.status_code)
    except Exception as exc:
        logger.warning("Local status unavailable: %s", type(exc).__name__)
    return {}


async def cloud_capabilities(client: httpx.AsyncClient) -> dict:
    """Probe and verify the Grow Central cloud endpoint before syncing."""
    try:
        response = await client.get(f"{legacy.CLOUD_URL}/api/health", timeout=10)
        if not response.is_success:
            return {"reachable": True, "compatible": False, "http_status": response.status_code}
        data = response.json()
        if not isinstance(data, dict):
            return {"reachable": True, "compatible": False, "reason": "invalid_health_payload"}
        service = data.get("service")
        version = data.get("version")
        compatible = bool(data.get("ok")) and service == EXPECTED_CLOUD_SERVICE and isinstance(version, str) and bool(version.strip())
        result = {
            "reachable": True,
            "compatible": compatible,
            "version": version,
            "service": service,
            "closed_test_mode": data.get("closed_test_mode"),
        }
        if not compatible:
            result["reason"] = "unexpected_cloud_identity"
        return result
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
        "device_online": bool(local),
        "extra": {"df100m": local, "closed_test_mode": legacy.CLOSED_TEST, "runtime": "cloud-link-v2"},
    }, local


async def main() -> None:
    if not legacy.CLOUD_ENABLED:
        _persist_state(state="disabled", detail="cloud link disabled", cloud_compatible=None)
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
                _persist_state(state="degraded", detail="cloud health unavailable or incompatible", cloud_compatible=False, capabilities=capabilities, retry_seconds=retry_seconds)
                logger.warning("Cloud unavailable/incompatible: %s; retry in %ss", json.dumps(capabilities), retry_seconds)
                await asyncio.sleep(retry_seconds)
                retry_seconds = min(MAX_RETRY, retry_seconds * 2)
                continue

            now = time.monotonic()
            try:
                telemetry, local = await telemetry_payload(client)
                response = await client.post(f"{legacy.CLOUD_URL}/api/v1/telemetry", json=telemetry, headers=headers, timeout=10)
                if response.status_code == 404:
                    _persist_state(state="degraded", detail="cloud telemetry endpoint missing", cloud_compatible=False, http_status=404, retry_seconds=retry_seconds)
                    await asyncio.sleep(retry_seconds)
                    retry_seconds = min(MAX_RETRY, retry_seconds * 2)
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
                    diag_response = await client.post(
                        f"{legacy.CLOUD_URL}/api/v1/diagnostics/snapshot",
                        json=legacy.diagnostic_payload(local, full_diag),
                        headers=headers,
                        timeout=30,
                    )
                    diag_response.raise_for_status()
                    next_diag = now + legacy.DIAG_SYNC

                last_bundle_signature = await legacy.mirror_bundle_if_changed(client, headers, last_bundle_signature)
                _persist_state(state="connected", detail="telemetry sync active", cloud_compatible=True, capabilities=capabilities, retry_seconds=legacy.SYNC)
                retry_seconds = MIN_RETRY
            except Exception as exc:
                connected = False
                _persist_state(state="degraded", detail=f"cloud sync failed: {type(exc).__name__}", cloud_compatible=True, capabilities=capabilities, retry_seconds=retry_seconds)
                logger.warning("Cloud sync degraded: %s; retry in %ss", type(exc).__name__, retry_seconds)
                await asyncio.sleep(retry_seconds)
                retry_seconds = min(MAX_RETRY, retry_seconds * 2)
                continue

            await asyncio.sleep(legacy.SYNC)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main())
