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
import os

import httpx

CLOUD_ENABLED = os.getenv("GC_CLOUD_ENABLED", "false").lower() == "true"
CLOUD_URL = os.getenv("GC_CLOUD_URL", "").rstrip("/")
TOKEN = os.getenv("GC_CLOUD_TOKEN", "")
SITE = os.getenv("GC_SITE_ID", "garage")
SYNC = int(os.getenv("GC_SYNC_SECONDS", "30"))
REMOTE = os.getenv("GC_REMOTE_COMMANDS", "false").lower() == "true"
LOCAL_API = os.getenv("GC_LOCAL_API", "http://127.0.0.1:8080").rstrip("/")


async def local_status(client: httpx.AsyncClient) -> dict:
    """DE: Lokalen Status lesen. EN: Read local status."""
    local = {}
    try:
        response = await client.get(f"{LOCAL_API}/api/status", timeout=5)
        if response.is_success:
            local = response.json()
    except Exception:
        # DE: Cloud-Probleme dürfen den lokalen Betrieb nie stoppen.
        # EN: Cloud issues must never stop local operation.
        pass

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
            timeout=8,
        )
        return response.is_success, response.text[:500]

    return False, "unsupported command"


async def main():
    """DE: Periodische Sync-Schleife. EN: Periodic synchronization loop."""
    if not CLOUD_ENABLED:
        print("Grow Central Cloud Link disabled / Cloud-Link deaktiviert")
        return

    headers = {"X-API-Token": TOKEN}

    async with httpx.AsyncClient() as client:
        while True:
            try:
                payload = await local_status(client)
                await client.post(
                    f"{CLOUD_URL}/api/v1/telemetry",
                    json=payload,
                    headers=headers,
                    timeout=10,
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
