#!/usr/bin/env python3
"""Compare *already decoded* Mars Legacy BLE ATT records by action.

Offline-only. Accepts a JSONL file with fields:
  ts, action, direction, characteristic_uuid, payload_hex
Optional: device, operation, session. Use action="idle" for baseline traffic.
No Bluetooth connection, writes, pairing or network access.
Never commit unredacted captures: BLE payloads may contain identifiers/secrets.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

UUID = re.compile(r"^[0-9a-fA-F-]{4,36}$")
HEX = re.compile(r"^(?:[0-9a-fA-F]{2}(?:[ :\-]?|$))*$")


def normalize(row: dict, line: int) -> dict:
    for name in ("ts", "action", "direction", "characteristic_uuid", "payload_hex"):
        if not isinstance(row.get(name), str) or not row[name].strip():
            raise ValueError(f"line {line}: missing/invalid {name}")
    action = row["action"].strip().lower()
    direction = row["direction"].strip().lower()
    if direction not in ("write", "notify", "indicate", "read", "other"):
        raise ValueError(f"line {line}: invalid direction")
    uuid = row["characteristic_uuid"].strip().lower()
    if not UUID.fullmatch(uuid):
        raise ValueError(f"line {line}: invalid UUID")
    payload = re.sub(r"[ :\-]", "", row["payload_hex"]).lower()
    if not payload or len(payload) % 2 or not re.fullmatch(r"[0-9a-f]+", payload):
        raise ValueError(f"line {line}: invalid payload_hex")
    if len(payload) > 8192:
        raise ValueError(f"line {line}: payload too large")
    return {
        "ts": row["ts"], "action": action, "direction": direction,
        "uuid": uuid, "payload": payload,
        "session": str(row.get("session", "unknown")),
        "device": str(row.get("device", "unknown")),
        "operation": str(row.get("operation", "unknown")).lower(),
    }


def analyze(rows: list[dict]) -> dict:
    baseline = set()
    grouped = defaultdict(list)
    for row in rows:
        key = (row["direction"], row["uuid"], row["payload"])
        if row["action"] == "idle":
            baseline.add(key)
        else:
            grouped[(row["device"], row["action"])].append(row)

    report = []
    for (device, action), events in sorted(grouped.items()):
        counts = Counter((r["direction"], r["uuid"], r["payload"]) for r in events)
        samples = []
        for (direction, uuid, payload), count in counts.most_common():
            sessions = sorted({r["session"] for r in events if
                               (r["direction"], r["uuid"], r["payload"]) == (direction, uuid, payload)})
            samples.append({
                "direction": direction, "uuid": uuid, "payload_hex": payload,
                "count": count, "sessions": sessions,
                "observed_in_idle": (direction, uuid, payload) in baseline,
                "candidate_only": True,
            })
        report.append({
            "device": device, "action": action, "frames": len(events),
            "unique_sessions": len({r["session"] for r in events}),
            "candidates": samples,
        })
    return {
        "schema": "mars-legacy-capture-analysis-v1",
        "total_records": len(rows), "baseline_unique_frames": len(baseline),
        "groups": report,
        "warning": (
            "Correlation is not command validation. App writes can be authentication, "
            "keepalive, ACK or control; repeat in independent sessions and verify physical effect."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Private decoded ATT JSONL capture")
    parser.add_argument("--output", type=Path, help="Write JSON report (treat as sensitive)")
    args = parser.parse_args()
    try:
        rows = []
        with args.input.open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError(f"line {number}: object expected")
                rows.append(normalize(record, number))
                if len(rows) > 100000:
                    raise ValueError("capture exceeds 100000 records")
        result = analyze(rows)
        output = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            if args.output.exists():
                raise ValueError("output exists; refusing overwrite")
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(output + "\n")
        else:
            print(output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"capture analysis failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
