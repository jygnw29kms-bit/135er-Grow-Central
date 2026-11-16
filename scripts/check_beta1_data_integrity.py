#!/usr/bin/env python3
"""Read-only Grow-Central Beta 1.0 storage integrity audit.

Never print credentials, growbook contents, sensor values, or user identifiers.
Checks reference integrity and SQLite; does not edit the installation.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import stat
from pathlib import Path

DBS = ("history.sqlite3", "mars-history.sqlite3", "sensor-calibration.db", "device-trust.db")
MEMBER_ROLES = {"admin", "grower", "observer"}


def audit(root: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    counters: dict[str, int] = {}

    def read_json(name: str, required: bool = False):
        path = root / name
        if not path.exists():
            if required:
                errors.append(f"{name}: missing")
            return None
        if path.is_symlink() or not path.is_file():
            errors.append(f"{name}: invalid or symlink")
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            errors.append(f"{name}: unreadable or invalid JSON")
            return None

    rooms = read_json("rooms.json", required=True)
    room_ids: set[str] = set()
    plant_ids: set[str] = set()
    if rooms is not None:
        if not isinstance(rooms, dict):
            errors.append("rooms.json: expected an object")
        else:
            active = rooms.get("rooms", [])
            archived = rooms.get("archived_rooms", [])
            if not isinstance(active, list) or not isinstance(archived, list):
                errors.append("rooms.json: room collections must be lists")
                active, archived = [], []
            all_rooms = active + archived
            room_id_list = [str(v.get("id")) for v in all_rooms if isinstance(v, dict) and v.get("id")]
            if len(room_id_list) != len(all_rooms) or len(set(room_id_list)) != len(room_id_list):
                errors.append("rooms.json: duplicate or missing room identifiers")
            room_ids = set(room_id_list)
            counters["rooms"] = len(active)
            counters["archived_rooms"] = len(archived)
            plants = rooms.get("plants", [])
            if not isinstance(plants, list):
                errors.append("rooms.json: plants must be a list")
                plants = []
            plant_id_list = [str(p.get("id")) for p in plants if isinstance(p, dict) and p.get("id")]
            if len(plant_id_list) != len(plants) or len(set(plant_id_list)) != len(plant_id_list):
                errors.append("rooms.json: duplicate or missing plant identifiers")
            plant_ids = set(plant_id_list)
            counters["plants"] = len(plants)
            for p in plants:
                if not isinstance(p, dict) or p.get("room_id") not in room_ids:
                    errors.append("rooms.json: plant references missing room")
                    break
            for key in ("room_journal", "sensor_history", "grow_events", "plant_journal"):
                records = rooms.get(key, [])
                if not isinstance(records, list):
                    errors.append(f"rooms.json: {key} must be a list")
                    continue
                counters[key] = len(records)
                if any(not isinstance(row, dict) or row.get("room_id") not in room_ids
                       for row in records):
                    # Historical entries may intentionally remain after room deletion,
                    # but must not be silently mistaken for valid current ownership.
                    warnings.append(f"{key}: some entries reference absent rooms")
                if key in {"room_journal", "plant_journal"}:
                    if any(row.get("plant_id") and row.get("plant_id") not in plant_ids
                           for row in records if isinstance(row, dict)):
                        warnings.append(f"{key}: some entries reference removed plants")
            assignments = rooms.get("assignments", {})
            if not isinstance(assignments, dict):
                errors.append("rooms.json: assignments must be an object")
            else:
                counters["assignments"] = len(assignments)
                if any(v not in room_ids for v in assignments.values()):
                    warnings.append("assignments: devices refer to missing rooms")

    sharing = read_json("room-sharing.json")
    if sharing is not None:
        if not isinstance(sharing, dict):
            errors.append("room-sharing.json: expected object")
        else:
            for key in ("members", "invitations"):
                records = sharing.get(key, [])
                if not isinstance(records, list):
                    errors.append(f"room-sharing.json: {key} must be a list")
                    continue
                counters[key] = len(records)
                if any(not isinstance(m, dict) or m.get("room_id") not in room_ids
                       for m in records):
                    warnings.append(f"{key}: references deleted room")
            for member in sharing.get("members", []):
                if isinstance(member, dict) and member.get("role") not in MEMBER_ROLES:
                    errors.append("room-sharing.json: unknown member role")
                    break
            if not isinstance(sharing.get("sessions", {}), dict):
                errors.append("room-sharing.json: sessions must be an object")

    pushes = read_json("room-push.json")
    if pushes is not None:
        if not isinstance(pushes, list):
            errors.append("room-push.json: expected list")
        else:
            counters["push_subscriptions"] = len(pushes)
            if any(not isinstance(item, dict) or item.get("room_id") not in room_ids
                   for item in pushes):
                warnings.append("room-push.json: subscriptions reference missing rooms")

    for file in ("room-control-plans.json", "room-notifications.json"):
        data = read_json(file)
        if data is not None and not isinstance(data, dict):
            errors.append(f"{file}: expected object")

    photos = root / "grow-photos"
    if photos.exists():
        if photos.is_symlink() or not photos.is_dir():
            errors.append("grow-photos: invalid directory")
        else:
            image_files = list(photos.iterdir())
            counters["photos"] = len([x for x in image_files if x.is_file()])
            if any(x.is_symlink() for x in image_files):
                errors.append("grow-photos: symlink entry rejected")

    for name in DBS:
        db = root / name
        if not db.exists():
            warnings.append(f"{name}: absent")
            continue
        if db.is_symlink() or not db.is_file():
            errors.append(f"{name}: invalid SQLite file")
            continue
        try:
            with sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5) as connection:
                if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    errors.append(f"{name}: SQLite integrity failed")
                else:
                    counters["db_checked"] = counters.get("db_checked", 0) + 1
        except (OSError, sqlite3.Error):
            errors.append(f"{name}: SQLite unreadable")

    return {"ok": not errors, "errors": errors, "warnings": warnings, "counts": counters}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("/var/lib/135er-grow-central"))
    args = parser.parse_args()
    result = audit(args.data_root)
    print("Grow Central Beta 1.0 read-only data integrity")
    for name, count in sorted(result["counts"].items()):
        print(f"  {name}: {count}")
    for name in result["warnings"]:
        print("  WARN:", name)
    for name in result["errors"]:
        print("  FAIL:", name)
    print("RESULT:", "PASS" if result["ok"] else "FAIL")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
