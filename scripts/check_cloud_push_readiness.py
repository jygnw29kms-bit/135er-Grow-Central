#!/usr/bin/env python3
"""Read-only Cloud Beta push readiness check; never displays keys or tokens."""
from __future__ import annotations
import argparse
import importlib.util
import json
import subprocess
from pathlib import Path


def check(backend: Path, python: Path, worker: Path | None = None) -> dict[str, bool]:
    source = backend.read_text(encoding="utf-8")
    result = {
        "cloud_collaboration_router": "# GROW_CENTRAL_BETA_ROOM_COLLABORATION_V1" in source,
        "cloud_push_router": "# GROW_CENTRAL_BETA_ACCOUNT_PUSH_V1" in source,
        "cloud_push_module": (backend.parent / "cloud_push.py").is_file(),
        "cloud_room_membership_module": (backend.parent / "cloud_room_membership.py").is_file(),
    }
    script = (
        "import importlib.util,json;"
        "print(json.dumps({name:bool(importlib.util.find_spec(name)) "
        "for name in ('qrcode','pywebpush','sqlalchemy')}))"
    )
    output = subprocess.run([str(python), "-c", script], capture_output=True,
                            text=True, timeout=15, check=True)
    modules = json.loads(output.stdout)
    for name, found in modules.items():
        result[f"python_{name}"] = bool(found)
    if worker is not None:
        result["push_service_worker"] = worker.is_file()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", type=Path, required=True)
    parser.add_argument("--venv-python", type=Path, required=True)
    parser.add_argument("--push-worker", type=Path)
    args = parser.parse_args()
    try:
        results = check(args.backend, args.venv_python, args.push_worker)
    except (OSError, ValueError, subprocess.SubprocessError, json.JSONDecodeError):
        print(json.dumps({"ready": False, "error": "readiness_probe_failed"}))
        return 2
    ready = all(results.values())
    print(json.dumps({"ready": ready, "checks": results}, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
