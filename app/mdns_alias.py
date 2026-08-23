"""Publish the stable 135er-GrowCentral.local alias through Avahi.

The OS hostname remains compatible with the proven Build-85 first-boot flow. The
application publishes an additional mDNS address record, so changing the setup
hostname is not required and AP provisioning cannot regress.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from contextlib import suppress

ALIAS = "135er-growcentral.local"
_process: asyncio.subprocess.Process | None = None
_task: asyncio.Task | None = None


def _primary_ipv4() -> str | None:
    """Choose a usable local IPv4 even when no Internet/default route exists."""
    try:
        result = subprocess.run(["ip", "-j", "address", "show"], capture_output=True, text=True, timeout=3, check=False)
        rows = json.loads(result.stdout) if result.returncode == 0 else []
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    candidates: list[tuple[int, str]] = []
    for row in rows if isinstance(rows, list) else []:
        name = str(row.get("ifname") or "")
        if name == "lo" or str(row.get("operstate") or "").upper() == "DOWN":
            continue
        priority = 0 if name.startswith(("eth", "en")) else 1 if name.startswith(("wlan", "wl")) else 2
        for info in row.get("addr_info") or []:
            address = str(info.get("local") or "")
            if info.get("family") == "inet" and address and not address.startswith("127.") and not address.startswith("169.254."):
                candidates.append((priority, address))
    return sorted(candidates)[0][1] if candidates else None


async def _stop_process() -> None:
    global _process
    if _process and _process.returncode is None:
        _process.terminate()
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(_process.wait(), timeout=3)
        if _process.returncode is None:
            _process.kill()
    _process = None


async def _publisher() -> None:
    global _process
    if not shutil.which("avahi-publish-address"):
        return
    published: str | None = None
    while True:
        address = _primary_ipv4()
        if address != published:
            await _stop_process()
            published = None
            if address:
                try:
                    _process = await asyncio.create_subprocess_exec(
                        "avahi-publish-address", "-R", ALIAS, address,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await asyncio.sleep(1)
                    if _process.returncode is None:
                        published = address
                except OSError:
                    _process = None
        await asyncio.sleep(20)


def install(app) -> None:
    @app.on_event("startup")
    async def start_mdns_alias() -> None:
        global _task
        if _task is None or _task.done():
            _task = asyncio.create_task(_publisher(), name="grow-central-mdns-alias")

    @app.on_event("shutdown")
    async def stop_mdns_alias() -> None:
        global _task
        if _task:
            _task.cancel()
            with suppress(asyncio.CancelledError):
                await _task
            _task = None
        await _stop_process()
