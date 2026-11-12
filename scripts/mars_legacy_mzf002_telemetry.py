#!/usr/bin/env python3
"""Offline Mars Legacy MZF002 temperature/humidity extraction from HCI PCAP.

Uses ONLY previously recorded notifications. Does not connect, write or alter
BLE devices. Redacts identity, session metadata, and all other raw fields.
Observed field mapping requires an additional independent hardware check.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

try:
    from scripts.fc3000_legacy_notify_audit import att_records
except ModuleNotFoundError:
    from fc3000_legacy_notify_audit import att_records

_NUMBER = re.compile(r"^-?\d+(?:[.,]\d+)?$")
_MAX_BYTES = 100 * 1024 * 1024


def decode_fan_notification(payload: bytes) -> dict | None:
    try:
        fields = payload.decode("ascii").split("|")
    except UnicodeDecodeError:
        return None
    if len(fields) != 23 or fields[3] != "MZF002":
        return None
    if not _NUMBER.fullmatch(fields[19]) or not _NUMBER.fullmatch(fields[20]):
        return None
    temperature = float(fields[19].replace(",", "."))
    humidity = float(fields[20].replace(",", "."))
    if not (-40 <= temperature <= 85 and 0 <= humidity <= 100):
        return None
    return {
        "device_family": "MZF002",
        "temperature_c_candidate": temperature,
        "humidity_rh_candidate": humidity,
        "field_indices": {"temperature": 19, "humidity": 20},
        "unverified_fields_omitted": True,
        "fan_power_state_verified": False,
        "firmware_identity_verified": False,
    }


def summarize(rows: list[tuple[float, int, int, bytes]]) -> dict:
    events = []
    for ts, op, handle, payload in rows:
        if op != 0x1B or handle != 0x002A:
            continue
        item = decode_fan_notification(payload)
        if item is not None:
            item["timestamp_utc"] = datetime.fromtimestamp(ts, timezone.utc).isoformat()
            events.append(item)
    return {
        "schema": "mars_legacy_mzf002_telemetry_v1",
        "samples": len(events),
        "latest": events[-1] if events else None,
        "temperature_min_c": min((x["temperature_c_candidate"] for x in events), default=None),
        "temperature_max_c": max((x["temperature_c_candidate"] for x in events), default=None),
        "humidity_min_rh": min((x["humidity_rh_candidate"] for x in events), default=None),
        "humidity_max_rh": max((x["humidity_rh_candidate"] for x in events), default=None),
        "events": events,
        "control_enabled": False,
        "note": "Observed read-only candidate fields; not validated live Grow Central integration.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pcap", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.pcap.stat().st_size > _MAX_BYTES:
            raise ValueError("PCAP exceeds size limit")
        report = summarize(att_records(args.pcap.read_bytes()))
        encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(encoded)
        else:
            print(encoded, end="")
    except (OSError, ValueError) as exc:
        print(f"MZF002 decode failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
