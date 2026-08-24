"""135er-Grow Central Pi-to-Cloud Agent.

DE:
    Sendet Telemetrie und Diagnosezustand über ausgehendes HTTPS an den VServer.
    Das jeweils neueste redigierte Pi-Support-Bundle wird bei Erstellung oder
    Änderung automatisch gespiegelt. Im expliziten Closed-Test-Modus funktioniert
    dies ohne Cloud-Zugangsdaten; Remote-Befehle bleiben dabei verboten.

EN:
    Sends telemetry and diagnostic state to the VPS over outbound HTTPS. The
    latest redacted Pi support bundle is mirrored whenever it is created or
    changed. Explicit closed-test mode works without cloud credentials while
    remote commands remain forbidden.
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
REMOTE = os.getenv("GC_REMOTE_COMMANDS", "false").lower() == "true"
LOCAL_API = os.getenv("GC_LOCAL_API", "http://127.0.0.1:8080").rstrip("/")
LOCAL_TOKEN = os.getenv("GC_LOCAL_API_TOKEN", "").strip()
SUPPORT_BUNDLE = Path(os.getenv(
    "GC_SUPPORT_BUNDLE",
    "/var/lib/135er-grow-central/support/Grow-Central-Support-latest.tar.gz",
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


async def local_status(client: httpx.AsyncClient) -> dict:
    """DE: Lokalen Status lesen. EN: Read local status."""
    local = {}
    try:
        response = await client.get(f"{LOCAL_API}/api/status", timeout=5)
        if response.is_success:
            local = response.json()
    except Exception as exc:
        logger.warning("Local status unavailable: %s", type(exc).__name__)
    return local


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
    payload = {
        "site_id": SITE,
        "device_id": device_id(),
        "ts": datetime.now(timezone.utc).isoformat(),
        "temperature_c": None,
        "humidity_pct": None,
        "vpd_kpa": None,
        "fan_speed_pct": None,
        "device_online": bool(local.get("connected", False)),
        "extra": {"df100m": local, "closed_test_mode": CLOSED_TEST},
    }
    return payload, local


def diagnostic_payload(local: dict) -> dict:
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
        "local_status": local,
        "support_bundle": bundle_metadata(),
        "cloud_link": {
            "closed_test_mode": CLOSED_TEST,
            "remote_commands": REMOTE,
            "sync_seconds": SYNC,
            "cloud_origin": CLOUD_URL,
        },
    }


async def mirror_bundle_if_changed(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    last_signature: tuple[int, int] | None,
) -> tuple[int, int] | None:
    if not SUPPORT_BUNDLE.is_file():
        return None
    try:
        stat = SUPPORT_BUNDLE.stat()
        signature = (stat.st_size, stat.st_mtime_ns)
    except OSError:
        return last_signature
    if signature == last_signature:
        return last_signature

    body = SUPPORT_BUNDLE.read_bytes()
    digest = hashlib.sha256(body).hexdigest()
    response = await client.put(
        f"{CLOUD_URL}/api/v1/diagnostics/bundle/{SITE}/{device_id()}",
        content=body,
        headers={**headers, "Content-Type": "application/gzip", "X-Content-SHA256": digest},
        timeout=60,
    )
    response.raise_for_status()
    logger.info("Mirrored support bundle sha256=%s size=%d", digest, len(body))
    return signature


async def apply_command(client: httpx.AsyncClient, command: dict) -> tuple[bool, str]:
    """DE: Remote-Anforderung lokal validieren. EN: Validate a remote request locally."""
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
            headers={"X-API-Token": LOCAL_TOKEN},
            timeout=8,
        )
        return response.is_success, response.text[:500]

    return False, "unsupported command"


async def main():
    """DE: Periodische Sync-Schleife. EN: Periodic synchronization loop."""
    if not CLOUD_ENABLED:
        print("Grow Central Cloud Link disabled / Cloud-Link deaktiviert")
        return

    validate_configuration()
    headers = {"X-API-Token": TOKEN} if TOKEN else {}
    last_bundle_signature: tuple[int, int] | None = None

    async with httpx.AsyncClient() as client:
        while True:
            try:
                telemetry, local = await telemetry_payload(client)
                telemetry_response = await client.post(
                    f"{CLOUD_URL}/api/v1/telemetry",
                    json=telemetry,
                    headers=headers,
                    timeout=10,
                )
                telemetry_response.raise_for_status()

                diagnostic_response = await client.post(
                    f"{CLOUD_URL}/api/v1/diagnostics/snapshot",
                    json=diagnostic_payload(local),
                    headers=headers,
                    timeout=15,
                )
                diagnostic_response.raise_for_status()

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
                                json={
                                    "ok": ok,
                                    "message": message,
                                    "ts": datetime.now(timezone.utc).isoformat(),
                                },
                                headers=headers,
                                timeout=10,
                            )
            except Exception as exc:
                print("cloud sync / Cloud-Sync:", exc)

            await asyncio.sleep(SYNC)


if __name__ == "__main__":
    asyncio.run(main())
