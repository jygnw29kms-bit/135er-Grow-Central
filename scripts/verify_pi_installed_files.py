#!/usr/bin/env python3
"""Read-only Pi installed-file audit against a Git checkout.

Default: seven UI/entrypoint/documentation files.
--runtime: all Python application modules plus active Final-Master assets.
Does NOT equate the original image SOURCE_COMMIT with an applied source revision.
Legacy, deliberately not deployed web pages are excluded from --runtime.
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
ACTIVE_UI = (
    "web/gc-final.html",
    "web/gc-final.css",
    "web/gc-final.js",
    "web/gc-worker.js",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_files(source: Path) -> list[str]:
    """Audit application source, not old unused web examples or build assets."""
    modules = [p.relative_to(source).as_posix() for p in (source / "app").rglob("*.py")]
    return sorted(set(modules).union(ACTIVE_UI).union(("README.md",)))


def verify(source: Path, installed_root: Path, files: tuple[str, ...] | list[str]) -> int:
    failure = 0
    for relative in files:
        src, installed = source / relative, installed_root / relative
        if not src.is_file() or not installed.is_file():
            result = "MISSING"
        elif digest(src) == digest(installed):
            result = "MATCH"
        else:
            result = "DIFF"
        print(f"{result:<7} {relative}")
        failure += result != "MATCH"
    for name in ("SOURCE_COMMIT", "BUILD", "VERSION"):
        path = installed_root / name
        print(f"{name}: {path.read_text().strip() if path.exists() else 'MISSING'}")
    print(f"RESULT: {len(files) - failure}/{len(files)} selected files match")
    return 1 if failure else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--installed-root", default="/opt/135er-grow-central", type=Path)
    parser.add_argument("--runtime", action="store_true", help="check all Python app modules and active UI")
    args = parser.parse_args()
    source = args.source_root.resolve()
    files = runtime_files(source) if args.runtime else CRITICAL
    return verify(source, args.installed_root.resolve(), files)


if __name__ == "__main__":
    raise SystemExit(main())
