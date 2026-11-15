#!/usr/bin/env python3
"""Fail-closed Grow-Central 1.0 Beta 1 release gate.

Only verified evidence + explicit manual acceptance permit a release.
Does not change installations, tags, code or stored user information.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[1] / "docs/BETA1_RELEASE_GATES.json"


def evaluate(record: dict) -> tuple[bool, list[str]]:
    blockers = []
    gates = record.get("mandatory_gates", [])
    if not gates:
        return False, ["No mandatory acceptance gates defined"]
    ids = [item.get("id") for item in gates]
    if len(set(ids)) != len(ids):
        blockers.append("Duplicate release gate IDs")
    for gate in gates:
        name = str(gate.get("id") or "unnamed")
        if gate.get("status") != "accepted":
            blockers.append(f"{name}: {gate.get('status', 'missing_status')}")
        if not str(gate.get("evidence") or "").strip():
            blockers.append(f"{name}: missing verification evidence")
        if gate.get("manual_acceptance_required") and not str(gate.get("accepted_by") or "").strip():
            blockers.append(f"{name}: operator acceptance missing")
    if record.get("status") != "ready":
        blockers.append("release status is not ready")
    return not blockers, blockers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT)
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"BETA RELEASE BLOCKED: invalid manifest ({type(exc).__name__})")
        return 2
    ready, blockers = evaluate(data)
    print(f"TARGET {data.get('target_release', 'unknown')}")
    for item in data.get("mandatory_gates", []):
        print(f"  {item.get('status','missing'):<20} {item.get('id','unnamed')}")
    if ready:
        print("RELEASE READY: all gates accepted with evidence")
        return 0
    print(f"RELEASE BLOCKED: {len(blockers)} issue(s)")
    for issue in blockers:
        print(f"  - {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
