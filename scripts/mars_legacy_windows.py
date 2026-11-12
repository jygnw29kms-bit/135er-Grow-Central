#!/usr/bin/env python3
"""Offline action-window labelling for decoded BLE ATT CSV exports.

Capture columns: time_epoch,device,session,direction,characteristic_uuid,payload_hex
Windows columns: start_epoch,end_epoch,device,session,action
Unmatched records become 'idle'. No BLE connection, network or hardware writes.
The input must contain decoded ATT, not encrypted RF packets. Keep private.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path

CAPTURE_FIELDS = {"time_epoch", "device", "session", "direction", "characteristic_uuid", "payload_hex"}
WINDOW_FIELDS = {"start_epoch", "end_epoch", "device", "session", "action"}


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"{path.name}: missing headers {sorted(required - set(reader.fieldnames or []))}")
        result = list(reader)
    if len(result) > 100000:
        raise ValueError(f"{path.name}: too many rows")
    return result


def finite_time(value: str, field: str) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {field}") from exc
    if not math.isfinite(n) or n < 0 or n > 253402300799:
        raise ValueError(f"invalid {field}")
    return n


def convert(capture: list[dict[str, str]], windows: list[dict[str, str]]) -> list[dict]:
    prepared: dict[tuple[str, str], list[tuple[float, float, str]]] = {}
    for row in windows:
        device, session = row["device"].strip(), row["session"].strip()
        start = finite_time(row["start_epoch"], "start_epoch")
        end = finite_time(row["end_epoch"], "end_epoch")
        if not device or not session or not row["action"].strip() or end <= start:
            raise ValueError("empty device/session/action or invalid window length")
        prepared.setdefault((device, session), []).append((start, end, row["action"].strip()))
    for key, spans in prepared.items():
        spans.sort()
        if any(spans[i][1] > spans[i + 1][0] for i in range(len(spans) - 1)):
            raise ValueError(f"overlapping action windows for {key}")
    result = []
    for row in capture:
        device, session = row["device"].strip(), row["session"].strip()
        stamp = finite_time(row["time_epoch"], "time_epoch")
        if not device or not session:
            raise ValueError("capture device/session required")
        matches = [action for start, end, action in prepared.get((device, session), [])
                   if start <= stamp < end]
        result.append({
            "ts": datetime.fromtimestamp(stamp, tz=timezone.utc).isoformat(),
            "action": matches[0] if matches else "idle",
            "direction": row["direction"],
            "characteristic_uuid": row["characteristic_uuid"],
            "payload_hex": row["payload_hex"],
            "device": device, "session": session,
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("windows", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        capture = read_csv(args.capture, CAPTURE_FIELDS)
        windows = read_csv(args.windows, WINDOW_FIELDS)
        records = convert(capture, windows)
        try:
            from scripts.mars_legacy_capture_analyze import normalize
        except ModuleNotFoundError:
            from mars_legacy_capture_analyze import normalize
        for i, row in enumerate(records, 1):
            normalize(row, i)
        with args.output.open("x", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
