#!/usr/bin/env python3
"""Passive, bounded MZF002 BLE notification capture on a Grow Central Pi.

This subscribes to a proven notify-capable characteristic for up to 6 seconds.
It does not issue actuator or vendor-protocol write commands.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import mars_hydro_ble as ble

MZF002_NOTIFY_UUID = "6f588463-f8f1-44f8-bdae-a1272a1b0f6e"


async def main() -> None:
    scan = await ble.scan(seconds=10)
    candidates = [
        row for row in scan["devices"]
        if str(row["name"]).upper().startswith("MZ_MZF002")
    ]
    print("CANDIDATES", len(candidates), flush=True)
    if not candidates:
        print("RESULT", json.dumps({"ok": False, "reason": "MZF002 not advertising"}), flush=True)
        return
    candidate = candidates[0]
    try:
        result = await asyncio.wait_for(
            ble.observe(ble.ObserveRequest(
                candidate_id=candidate["candidate_id"],
                characteristic_uuid=MZF002_NOTIFY_UUID,
                seconds=6.0,
            )), timeout=25,
        )
        print("RESULT", json.dumps({
            "name": candidate["name"], "notify_uuid": result["uuid"],
            "events": result["events"], "count": result["event_count"],
            "write_attempted": result["write_attempted"],
        }, ensure_ascii=True), flush=True)
    except Exception as exc:
        print("ERROR", json.dumps({
            "type": type(exc).__name__, "message": str(exc)[:250]
        }, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
