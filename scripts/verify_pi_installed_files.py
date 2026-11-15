#!/usr/bin/env python3
"""Read-only comparison of installed Pi code with a Git checkout.

This is deliberately not a claim that an installed image fully matches Git:
source metadata and runtime dependencies are reported separately.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

CRITICAL = (
    "web/gc-final.html",
    "web/gc-final.css",
    "web/gc-final.js",
    "web/gc-worker.js",
    "app/entrypoint.py",
    "app/main.py",
    "README.md",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--installed-root", default="/opt/135er-grow-central", type=Path)
    args = parser.parse_args()
    failure = 0
    for relative in CRITICAL:
        src, installed = args.source_root / relative, args.installed_root / relative
        if not src.is_file() or not installed.is_file():
            result = "MISSING"
        elif digest(src) == digest(installed):
            result = "MATCH"
        else:
            result = "DIFF"
        print(f"{result:<7} {relative}")
        failure += result != "MATCH"
    for name in ("SOURCE_COMMIT", "BUILD", "VERSION"):
        path = args.installed_root / name
        print(f"{name}: {path.read_text().strip() if path.exists() else 'MISSING'}")
    print(f"RESULT: {len(CRITICAL)-failure}/{len(CRITICAL)} selected files match")
    return 1 if failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
