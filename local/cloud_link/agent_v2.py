"""Grow Central Cloud Link runtime for the V7 control plane.

The cloud link is optional and local-first. It only handles current device
pairing, signed platform reports and advisory cloud health. Local device
control continues independently when the cloud is unavailable.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import time
from urllib.parse import urlparse

import httpx

try:
    from .cloud_url import https_origin
    from .device_identity import DEVICE_ID_FILE
    from .device_pairing import load_state as load_pairing_state, poll_pairing
    from .platform_report import send_platform_report
except ImportError:
    from cloud_url import https_origin  # type: ignore[no-redef]
    from device_identity import DEVICE_ID_FILE  # type: ignore[no-redef]
    from device_pairing import load_state as load_pairing_state, poll_pairing  # type: ignore[no-redef]
    from platform_report import send_platform_report  # type: ignore[no-redef]

logger = logging.getLogger(__name__)

CLOUD_ENABLED = os.getenv("GC_CLOUD_ENABLED", "false").lower() == "true"
CLOUD_URL = os.getenv("GC_CLOUD_URL", "").rstrip("/")
SITE = os.getenv("GC_SITE_ID", "").strip()
SYNC = min(max(int(os.getenv("GC_SYNC_SECONDS", "30")), 10), 3600)
LOCAL_API = os.getenv("GC_LOCAL_API", "http://127.0.0.1:8080").rstrip("/")
LOCAL_TOKEN = os.getenv("GC_LOCAL_API_TOKEN", "").strip()
CLOUD_STATE = Path(os.getenv("GC_CLOUD_STATE", "/var/lib/135er-grow-central/cloud-link-status.json"))
LOCAL_TOKEN_FILE = Path("/var/lib/135er-grow-central/local-api-token")
MACHINE_ID_FILE = Path("/etc/machine-id")
MIN_RETRY = 30
MAX_RETRY = 600
PLATFORM_REPORT_SECONDS = min(max(int(os.getenv("GC_PLATFORM_REPORT_SECONDS", "120")), 60), 3600)
PAIRING_POLL_SECONDS = min(max(int(os.getenv("GC_PAIRING_POLL_SECONDS", "10")), 5), 60)


def _read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return default


def _write_json(path: Path, payload: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o640)
        os.replace(temporary, path)
    except OSError as exc:
        logger.warning("Could not persist cloud-link state: %s", type(exc).__name__)


def installation_fallback_device_id() -> str:
    """Stable pre-pairing identifier used until the cloud assigns its UUID."""
    machine_id = _read_text(MACHINE_ID_FILE)
    suffix = re.sub(r"[^a-fA-F0-9]", "", machine_id)[-12:]
    return f"raspberry-pi-{suffix}" if suffix else "raspberry-pi-test"


FALLBACK_DEVICE_ID = installation_fallback_device_id


def effective_device_id() -> str:
    configured = os.getenv("GC_DEVICE_ID", "").strip()
    if configured:
        return configured
    try:
        approved = DEVICE_ID_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        approved = ""
    if len(approved) == 36:
        return approved
    return FALLBACK_DEVICE_ID()


def validate_configuration() -> None:
    try:
        https_origin(CLOUD_URL)
    except ValueError as exc:
        raise RuntimeError("GC_CLOUD_URL must be a plain HTTPS origin") from exc
    local = urlparse(LOCAL_API)
    if local.scheme != "http" or local.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("GC_LOCAL_API must use loopback HTTP")


def _persist_state(**values) -> None:
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "cloud_origin": CLOUD_URL,
        "device_id": effective_device_id(),
        **({"site_id": SITE} if SITE else {}),
        **values,
    }
    _write_json(CLOUD_STATE, payload)


def local_headers() -> dict[str, str]:
    """Read the per-device token created by the local runtime."""
    try:
        token = LOCAL_TOKEN_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        token = ""
    if len(token) < 32:
        configured = LOCAL_TOKEN.strip()
        token = configured if len(configured) >= 32 and configured.lower() != "test" else ""
    return {"X-API-Token": token} if token else {}


async def local_status(client: httpx.AsyncClient) -> dict:
    try:
        response = await client.get(f"{LOCAL_API}/api/status", headers=local_headers(), timeout=5)
        if response.is_success:
            payload = response.json()
            return payload if isinstance(payload, dict) else {}
        logger.warning("Local status returned HTTP %s", response.status_code)
    except Exception as exc:
        logger.warning("Local status unavailable: %s", type(exc).__name__)
    return {}


async def cloud_capabilities(client: httpx.AsyncClient) -> dict:
    """Probe only the current V7 control plane."""
    origin = CLOUD_URL.rstrip("/")
    try:
        response = await client.get(f"{origin}/v7/health", timeout=10)
    except Exception as exc:
        return {"reachable": False, "compatible": False, "error": type(exc).__name__}
    if not response.is_success:
        return {
            "reachable": True,
            "compatible": False,
            "http_status": response.status_code,
            "reason": "v7_health_unavailable",
        }
    try:
        data = response.json()
    except Exception:
        return {"reachable": True, "compatible": False, "reason": "invalid_v7_health_payload"}
    version = data.get("version") if isinstance(data, dict) else None
    compatible = (
        isinstance(data, dict)
        and data.get("ok") is True
        and isinstance(version, int)
        and version >= 7
    )
    result = {
        "reachable": True,
        "compatible": compatible,
        "architecture": "v7-control-v2-device",
        "version": version,
        "service": "grow-central-cloud-v7",
        "admin_mode": data.get("admin_mode") if isinstance(data, dict) else None,
        "platform_reports": True,
        "device_pairing": True,
    }
    if not compatible:
        result["reason"] = "unexpected_v7_health"
    return result


async def _poll_pending_pairing(client: httpx.AsyncClient) -> dict | None:
    state = load_pairing_state()
    if not state or not state.get("device_code"):
        return None
    try:
        result = await poll_pairing(client, cloud_url=CLOUD_URL)
        if result.get("status") == "approved":
            logger.info("Grow Central cloud device pairing approved")
        return result
    except Exception as exc:
        logger.warning("Cloud pairing poll failed: %s", type(exc).__name__)
        return {"status": "degraded", "reason": type(exc).__name__}


async def main() -> None:
    if not CLOUD_ENABLED:
        _persist_state(
            state="disabled",
            detail="cloud link disabled",
            cloud_compatible=None,
            platform_report={"state": "disabled", "sent": False},
        )
        print("Grow Central Cloud Link disabled / Cloud-Link deaktiviert")
        return

    validate_configuration()
    retry_seconds = MIN_RETRY
    next_platform_report = 0.0
    next_pairing_poll = 0.0
    platform_state: dict = {"state": "pending", "sent": False}
    pairing_state: dict | None = None

    async with httpx.AsyncClient() as client:
        while True:
            capabilities = await cloud_capabilities(client)
            if not capabilities.get("compatible"):
                _persist_state(
                    state="degraded",
                    detail="V7 cloud health unavailable or incompatible",
                    cloud_compatible=False,
                    capabilities=capabilities,
                    retry_seconds=retry_seconds,
                    platform_report=platform_state,
                    pairing=pairing_state,
                )
                logger.warning("V7 cloud unavailable/incompatible: %s; retry in %ss", json.dumps(capabilities), retry_seconds)
                await asyncio.sleep(retry_seconds)
                retry_seconds = min(MAX_RETRY, retry_seconds * 2)
                continue

            now = time.monotonic()
            if now >= next_pairing_poll:
                pairing_state = await _poll_pending_pairing(client)
                next_pairing_poll = now + PAIRING_POLL_SECONDS
                if pairing_state and pairing_state.get("status") == "approved":
                    next_platform_report = 0.0

            if now >= next_platform_report:
                platform_state = await send_platform_report(
                    client,
                    cloud_url=CLOUD_URL,
                    local_api=LOCAL_API,
                    local_headers=local_headers(),
                    capabilities={
                        "cloud_health_version": capabilities.get("version"),
                        "cloud_architecture": capabilities.get("architecture"),
                    },
                )
                next_platform_report = now + PLATFORM_REPORT_SECONDS
                if platform_state.get("sent"):
                    logger.info("Signed platform report accepted by Grow Central cloud")
                elif platform_state.get("state") not in {"unpaired", "pending"}:
                    logger.warning("Platform report degraded: %s", platform_state.get("reason", "unknown"))

            local = await local_status(client)
            retry_seconds = MIN_RETRY
            _persist_state(
                state="connected",
                detail="v7 control plane active",
                cloud_compatible=True,
                capabilities=capabilities,
                local_online=bool(local),
                retry_seconds=SYNC,
                platform_report=platform_state,
                pairing=pairing_state,
            )
            await asyncio.sleep(SYNC)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main())
