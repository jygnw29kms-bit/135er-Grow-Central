#!/usr/bin/env python3
"""FC3000-only offline audit of previously decoded Mars Legacy BLE ATT frames.

Does NOT sniff, connect, decrypt, pair, or issue GATT writes. Inputs are private.
Data format: labelled JSONL from mars_legacy_windows.py (device='lamp').
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

try:
    from scripts.mars_legacy_capture_analyze import analyze, normalize
except ModuleNotFoundError:
    from mars_legacy_capture_analyze import analyze, normalize

ACTIONS = {"idle", "light_on", "light_off", "dim_25", "dim_50", "dim_75", "dim_100"}
DEVICE = "lamp"


def audit(records: list[dict]) -> dict:
    if not records:
        raise ValueError("no FC3000 capture records")
    for index, row in enumerate(records, 1):
        if row["device"] != DEVICE:
            raise ValueError(f"record {index}: only 'lamp' is permitted; fan data rejected")
        if row["action"] not in ACTIONS:
            raise ValueError(f"record {index}: unsupported FC3000 action {row['action']!r}")
        if row["session"] in ("", "unknown"):
            raise ValueError(f"record {index}: real session label is required")

    result = analyze(records)
    for group in result["groups"]:
        # Never promote a statistically correlated payload to a validated command.
        for candidate in group["candidates"]:
            candidate["candidate_only"] = True
            candidate["validated"] = False
    result["device_scope"] = "FC3000_only"
    result["identity_verified"] = False
    result["control_enabled"] = False
    result["known_payloads"] = 0
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labelled_jsonl", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        rows = []
        with args.labelled_jsonl.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError(f"line {line_no}: JSON object expected")
                rows.append(normalize(item, line_no))
                if len(rows) > 100000:
                    raise ValueError("too many records")
        report = audit(rows)
        data = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(data)
        else:
            print(data, end="")
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"FC3000 offline audit failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
