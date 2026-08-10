"""135er-Grow Central Pi-to-Cloud Agent.

DE:
    Sendet Status über ausgehendes HTTPS an den VServer. Remote-Befehle
    benötigen eine zusätzliche lokale Freigabe.

EN:
    Sends state to the VPS over outbound HTTPS. Remote commands require a
    separate local opt-in.
"""
import asyncio
from datetime import datetime, timezone
import json
import logging
import os
import re
from urllib.parse import urlparse

import httpx

CLOUD_ENABLED = os.getenv("GC_CLOUD_ENABLED", "false").lower() == "true"
CLOUD_URL = os.getenv("GC_CLOUD_URL", "").rstrip("/")
TOKEN = os.getenv("GC_CLOUD_TOKEN", "")
SITE = os.getenv("GC_SITE_ID", "garage")
SYNC = min(max(int(os.getenv("GC_SYNC_SECONDS", "30")), 10), 3600)
REMOTE = os.getenv("GC_REMOTE_COMMANDS", "false").lower() == "true"
LOCAL_API = os.getenv("GC_LOCAL_API", "http://127.0.0.1:8080").rstrip("/")
LOCAL_TOKEN = os.getenv("GC_LOCAL_API_TOKEN", "").strip()
logger = logging.getLogger(__name__)


def validate_configuration() -> None:
    cloud = urlparse(CLOUD_URL)
    local = urlparse(LOCAL_API)
    if cloud.scheme != "https" or not cloud.netloc or cloud.path not in {"", "/"}:
        raise RuntimeError("GC_CLOUD_URL must be a plain HTTPS origin")
    if local.scheme != "http" or local.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("GC_LOCAL_API must use loopback HTTP")
    if len(TOKEN) < 32 or TOKEN.startswith("CHANGE_ME"):
        raise RuntimeError("GC_CLOUD_TOKEN must contain at least 32 non-placeholder characters")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", SITE):
        raise RuntimeError("GC_SITE_ID contains unsupported characters")
    if REMOTE and not LOCAL_TOKEN:
        raise RuntimeError("GC_LOCAL_API_TOKEN is required when remote commands are enabled")


async def local_status(client: httpx.AsyncClient) -> dict:
    """DE: Lokalen Status lesen. EN: Read local status."""
    local = {}
    try:
        response = await client.get(f"{LOCAL_API}/api/status", timeout=5)
        if response.is_success:
            local = response.json()
    except Exception as exc:
        # DE: Cloud-Probleme dürfen den lokalen Betrieb nie stoppen.
        # EN: Cloud issues must never stop local operation.
        logger.warning("Local status unavailable: %s", type(exc).__name__)

    return {
        "site_id": SITE,
        "device_id": "raspberry-pi",
        "ts": datetime.now(timezone.utc).isoformat(),
        "temperature_c": None,
        "humidity_pct": None,
        "vpd_kpa": None,
        "fan_speed_pct": None,
        "device_online": bool(local.get("connected", False)),
        "extra": {"df100m": local},
    }


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

    headers = {"X-API-Token": TOKEN}

    async with httpx.AsyncClient() as client:
        while True:
            try:
                payload = await local_status(client)
                telemetry_response = await client.post(
                    f"{CLOUD_URL}/api/v1/telemetry",
                    json=payload,
                    headers=headers,
                    timeout=10,
                )
                telemetry_response.raise_for_status()

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
