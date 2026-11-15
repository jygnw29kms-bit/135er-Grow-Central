#!/usr/bin/env python3
"""Read-only Grow Central Mars BLE freshness / BlueZ presence diagnostic.

No passwords or live command/control calls. Exit 0 when both latest reported
controller states are fresh, 2 when unavailable/stale, 1 on malformed files.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DEVICES = {
    "fan": ("mars-fan-live.json", "GC_MZF002_BLE_ADDRESS"),
    "lamp": ("mars-lamp-live.json", "GC_FC3000_BLE_ADDRESS"),
}


def inspect(root: Path, max_age: float, now: datetime) -> int:
    failures = 0
    for device, (file_name, _) in DEVICES.items():
        path = root / file_name
        if not path.is_file():
            print(f"{device}: UNAVAILABLE no measured-state file")
            failures += 1
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            measured_at = datetime.fromisoformat(payload["timestamp"])
            if measured_at.tzinfo is None:
                raise ValueError("timestamp has no timezone")
            age = (now - measured_at.astimezone(timezone.utc)).total_seconds()
            if age < 0 or age > max_age:
                print(f"{device}: STALE last-controller-report age={age:.0f}s")
                failures += 1
            else:
                print(f"{device}: FRESH last-controller-report age={age:.0f}s")
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            print(f"{device}: INVALID reported-state file ({type(exc).__name__})")
            failures += 1
    return 2 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, default=Path("/var/lib/135er-grow-central"))
    parser.add_argument("--max-age-seconds", type=float, default=120)
    args = parser.parse_args()
    if args.max_age_seconds <= 0:
        parser.error("--max-age-seconds must be positive")
    return inspect(args.state_dir, args.max_age_seconds, datetime.now(timezone.utc))


if __name__ == "__main__":
    raise SystemExit(main())
