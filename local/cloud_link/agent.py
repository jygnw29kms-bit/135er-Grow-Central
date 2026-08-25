"""135er-Grow Central Pi-to-Cloud agent.

Closed-test mode may sync telemetry and diagnostics without cloud credentials.
Remote commands remain forbidden in credential-free closed-test mode.
"""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import platform
import re
import socket
import time
from urllib.parse import urlparse

import httpx

CLOUD_ENABLED = os.getenv("GC_CLOUD_ENABLED", "false").lower() == "true"
CLOUD_URL = os.getenv("GC_CLOUD_URL", "").rstrip("/")
CLOSED_TEST = os.getenv("GC_CLOUD_TEST_MODE", "false").lower() == "true"
TOKEN = os.getenv("GC_CLOUD_TOKEN", "").strip()
SITE = os.getenv("GC_SITE_ID", "closed-test")
SYNC = min(max(int(os.getenv("GC_SYNC_SECONDS", "30")), 10), 3600)
DIAG_SYNC = min(max(int(os.getenv("GC_DIAGNOSTIC_SYNC_SECONDS", "120")), 30), 3600)
BUNDLE_REFRESH = min(max(int(os.getenv("GC_DIAGNOSTIC_BUNDLE_SECONDS", "300")), 120), 21600)
REMOTE = os.getenv("GC_REMOTE_COMMANDS", "false").lower() == "true"
LOCAL_API = os.getenv("GC_LOCAL_API", "http://127.0.0.1:8080").rstrip("/")
LOCAL_TOKEN = os.getenv("GC_LOCAL_API_TOKEN", "").strip()
SUPPORT_BUNDLE = Path(os.getenv(
    "GC_SUPPORT_BUNDLE",
    "/var/lib/135er-grow-central/support/Grow-Central-Support-latest.tar.gz",
))
CONTACT_ACK = Path(os.getenv(
    "GC_CLOUD_CONTACT_STATE",
    "/var/lib/135er-grow-central/cloud-link-contact.json",
))
BUILD_FILE = Path("/opt/135er-grow-central/BUILD")
VERSION_FILE = Path("/opt/135er-grow-central/VERSION")
BOOT_ID_FILE = Path("/proc/sys/kernel/random/boot_id")
logger = logging.getLogger(__name__)


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
        logger.warning("Could not persist cloud contact state: %s", type(exc).__name__)


def device_id() -> str:
    configured = os.getenv("GC_DEVICE_ID", "").strip()
    if configured:
        return configured
    machine_id = _read_text(Path("/etc/machine-id"))
    suffix = re.sub(r"[^a-fA-F0-9]", "", machine_id)[-12:]
    return f"raspberry-pi-{suffix}" if suffix else "raspberry-pi-test"


def validate_configuration() -> None:
    cloud = urlparse(CLOUD_URL)
    local = urlparse(LOCAL_API)
    if cloud.scheme != "https" or not cloud.netloc or cloud.path not in {"", "/"}:
        raise RuntimeError("GC_CLOUD_URL must be a plain HTTPS origin")
    if local.scheme != "http" or local.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("GC_LOCAL_API must use loopback HTTP")
    if not CLOSED_TEST and (len(TOKEN) < 32 or TOKEN.startswith("CHANGE_ME")):
        raise RuntimeError("GC_CLOUD_TOKEN must contain at least 32 non-placeholder characters outside closed-test mode")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", SITE):
        raise RuntimeError("GC_SITE_ID contains unsupported characters")
    if REMOTE and not LOCAL_TOKEN:
        raise RuntimeError("GC_LOCAL_API_TOKEN is required when remote commands are enabled")
    if CLOSED_TEST and REMOTE:
        raise RuntimeError("remote commands must remain disabled in credential-free closed-test mode")


def local_headers() -> dict[str, str]:
    return {"X-API-Token": LOCAL_TOKEN} if LOCAL_TOKEN else {}


async def local_status(client: httpx.AsyncClient) -> dict:
    try:
        response = await client.get(f"{LOCAL_API}/api/status", timeout=5)
        if response.is_success:
            return response.json()
    except Exception as exc:
        logger.warning("Local status unavailable: %s", type(exc).__name__)
    return {}


async def full_local_diagnostics(client: httpx.AsyncClient) -> dict:
    """Read the allowlisted full local snapshot; failures are themselves diagnosable."""
    try:
        response = await client.get(
            f"{LOCAL_API}/api/v1/diagnostics/snapshot?lines=120",
            headers=local_headers(),
            timeout=35,
        )
        if response.is_success:
            return response.json()
        return {"available": False, "http_status": response.status_code}
    except Exception as exc:
        return {"available": False, "error": type(exc).__name__}


async def request_fresh_bundle(client: httpx.AsyncClient) -> None:
    """Ask the local path unit to create a fresh redacted support bundle."""
    try:
        status = await client.get(f"{LOCAL_API}/api/v1/diagnostics/bundle/status", timeout=5)
        if status.is_success and status.json().get("pending"):
            return
        response = await client.post(
            f"{LOCAL_API}/api/v1/diagnostics/bundle",
            headers=local_headers(),
            timeout=5,
        )
        if response.status_code not in {200, 409}:
            logger.warning("Bundle refresh request returned HTTP %s", response.status_code)
    except Exception as exc:
        logger.warning("Bundle refresh request failed: %s", type(exc).__name__)


def bundle_metadata() -> dict:
    if not SUPPORT_BUNDLE.is_file():
        return {"available": False}
    try:
        stat = SUPPORT_BUNDLE.stat()
        return {
            "available": True,
            "filename": SUPPORT_BUNDLE.name,
            "size": stat.st_size,
            "modified_ns": stat.st_mtime_ns,
        }
    except OSError:
        return {"available": False}


async def telemetry_payload(client: httpx.AsyncClient) -> tuple[dict, dict]:
    local = await local_status(client)
    return {
        "site_id": SITE,
        "device_id": device_id(),
        "ts": datetime.now(timezone.utc).isoformat(),
        "temperature_c": None,
        "humidity_pct": None,
        "vpd_kpa": None,
        "fan_speed_pct": None,
        "device_online": bool(local.get("connected", False)),
        "extra": {"df100m": local, "closed_test_mode": CLOSED_TEST},
    }, local


def diagnostic_payload(local: dict, full_diagnostics: dict) -> dict:
    try:
        uptime = max(0.0, time.clock_gettime(time.CLOCK_BOOTTIME))
    except (AttributeError, OSError):
        uptime = None
    return {
        "site_id": SITE,
        "device_id": device_id(),
        "ts": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "build": _read_text(BUILD_FILE),
        "version": _read_text(VERSION_FILE),
        "kernel": platform.release(),
        "boot_id": _read_text(BOOT_ID_FILE),
        "uptime_seconds": uptime,
        "local_status": {
            "device": local,
            "diagnostics": full_diagnostics,
        },
        "support_bundle": bundle_metadata(),
        "cloud_link": {
            "closed_test_mode": CLOSED_TEST,
            "remote_commands": REMOTE,
            "telemetry_sync_seconds": SYNC,
            "diagnostic_sync_seconds": DIAG_SYNC,
            "bundle_refresh_seconds": BUNDLE_REFRESH,
            "cloud_origin": CLOUD_URL,
        },
    }


async def contact_handshake(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    local: dict,
    reason: str,
) -> dict:
    """Push a diagnostic snapshot on first/re-established contact and retain server acknowledgement."""
    full_diag = await full_local_diagnostics(client)
    payload = diagnostic_payload(local, full_diag)
    payload["reason"] = reason
    response = await client.post(
        f"{CLOUD_URL}/api/v1/diagnostics/contact",
        json=payload,
        headers=headers,
        timeout=35,
    )
    response.raise_for_status()
    acknowledgement = response.json()
    _write_json(CONTACT_ACK, {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "cloud_origin": CLOUD_URL,
        "site_id": SITE,
        "device_id": device_id(),
        "reason": reason,
        "server": acknowledgement,
    })
    await request_fresh_bundle(client)
    logger.info("Cloud diagnostic handshake accepted reason=%s host=%s", reason, urlparse(CLOUD_URL).hostname)
    return acknowledgement


async def mirror_bundle_if_changed(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    last_signature: tuple[int, int] | None,
) -> tuple[int, int] | None:
    if not SUPPORT_BUNDLE.is_file():
        return last_signature
    try:
        stat = SUPPORT_BUNDLE.stat()
        signature = (stat.st_size, stat.st_mtime_ns)
    except OSError:
        return last_signature
    if signature == last_signature:
        return last_signature

    if stat.st_size > 32 * 1024 * 1024:
        logger.warning("Support bundle too large to mirror: %d bytes", stat.st_size)
        return last_signature
    body = SUPPORT_BUNDLE.read_bytes()
    digest = hashlib.sha256(body).hexdigest()
    response = await client.put(
        f"{CLOUD_URL}/api/v1/diagnostics/bundle/{SITE}/{device_id()}",
        content=body,
        headers={**headers, "Content-Type": "application/gzip", "X-Content-SHA256": digest},
        timeout=90,
    )
    response.raise_for_status()
    logger.info("Mirrored support bundle sha256=%s size=%d", digest, len(body))
    return signature


async def apply_command(client: httpx.AsyncClient, command: dict) -> tuple[bool, str]:
    if not REMOTE:
        return False, "remote commands disabled locally"
    if command.get("target") == "df100m" and command.get("action") == "set_speed":
        try:
            value = int(json.loads(command.get("value_json", "0")))
        except (TypeError, ValueError, json.JSONDecodeError):
            return False, "invalid speed value"
        if not 0 <= value <= 100:
            return False, "speed out of range"
        response = await client.post(
            f"{LOCAL_API}/api/speed",
            json={"percent": value},
            headers=local_headers(),
            timeout=8,
        )
        return response.is_success, response.text[:500]
    return False, "unsupported command"


async def main():
    if not CLOUD_ENABLED:
        print("Grow Central Cloud Link disabled / Cloud-Link deaktiviert")
        return

    validate_configuration()
    headers = {"X-API-Token": TOKEN} if TOKEN else {}
    last_bundle_signature: tuple[int, int] | None = None
    next_diag = 0.0
    next_bundle_refresh = 0.0
    connected = False
    ever_connected = False

    async with httpx.AsyncClient() as client:
        while True:
            now = time.monotonic()
            try:
                telemetry, local = await telemetry_payload(client)
                response = await client.post(
                    f"{CLOUD_URL}/api/v1/telemetry", json=telemetry, headers=headers, timeout=10
                )
                response.raise_for_status()

                if not connected:
                    reason = "reconnect" if ever_connected else "startup"
                    await contact_handshake(client, headers, local, reason)
                    connected = True
                    ever_connected = True
                    last_bundle_signature = None
                    next_diag = now + DIAG_SYNC
                    next_bundle_refresh = now + BUNDLE_REFRESH

                if now >= next_bundle_refresh:
                    await request_fresh_bundle(client)
                    next_bundle_refresh = now + BUNDLE_REFRESH

                if now >= next_diag:
                    full_diag = await full_local_diagnostics(client)
                    response = await client.post(
                        f"{CLOUD_URL}/api/v1/diagnostics/snapshot",
                        json=diagnostic_payload(local, full_diag),
                        headers=headers,
                        timeout=30,
                    )
                    response.raise_for_status()
                    next_diag = now + DIAG_SYNC

                last_bundle_signature = await mirror_bundle_if_changed(
                    client, headers, last_bundle_signature
                )

                if REMOTE:
                    response = await client.get(
                        f"{CLOUD_URL}/api/v1/sites/{SITE}/commands/pending",
                        headers=headers,
                        timeout=10,
                    )
                    if response.is_success:
                        for command in response.json():
                            ok, message = await apply_command(client, command)
                            await client.post(
                                f"{CLOUD_URL}/api/v1/commands/{command['id']}/result",
                                json={"ok": ok, "message": message, "ts": datetime.now(timezone.utc).isoformat()},
                                headers=headers,
                                timeout=10,
                            )
            except Exception as exc:
                if connected:
                    logger.warning("Cloud contact lost: %s", type(exc).__name__)
                else:
                    logger.warning("cloud sync failed: %s", type(exc).__name__)
                connected = False

            await asyncio.sleep(SYNC)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main())
