#!/usr/bin/env python3
"""Read-only BLE GATT audit run on a Grow Central Pi (no writes or pairing).

Usage: cd /opt/135er-grow-central && .venv/bin/python scripts/ble_live_audit.py
Prints only Mars-Hydro-like candidates and bounded service metadata. No secrets.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import mars_hydro_ble as ble


async def main() -> None:
    result = await ble.scan(seconds=10)
    selected = [row for row in result["devices"] if row["mars_hydro_hint"]]
    print("SCAN", json.dumps({
        "found_total": result["found"],
        "adapter": result["adapter"],
        "selected": selected,
    }, ensure_ascii=True), flush=True)
    for candidate in selected:
        try:
            report = await asyncio.wait_for(
                ble.inspect(ble.InspectRequest(candidate_id=candidate["candidate_id"])),
                timeout=30,
            )
            # Do not persist raw values or stable addresses in the repository.
            print("GATT", json.dumps({
                "name": candidate["name"],
                "services": report.get("services", []),
                "readable_uuids": [r.get("uuid") for r in report.get("reads", []) if r.get("ok")],
                "read_failures": [
                    {"uuid": r.get("uuid"), "error": r.get("error")}
                    for r in report.get("reads", []) if not r.get("ok")
                ],
                "write_attempted": report.get("write_attempted"),
                "identity_verified": report.get("identity_verified"),
            }, ensure_ascii=True), flush=True)
        except Exception as exc:
            print("GATT_ERROR", json.dumps({
                "name": candidate["name"],
                "error_type": type(exc).__name__,
                "error": str(exc)[:250],
            }, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
