"""Read-only appliance and Raspberry Pi identity for the System view."""
from __future__ import annotations

import platform
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/system", tags=["system"])
ROOT = Path(__file__).resolve().parent.parent


def _text(path: Path, fallback: str) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").replace("\x00", "").strip() or fallback
    except OSError:
        return fallback


def system_identity() -> dict[str, str]:
    return {
        "model": _text(Path("/proc/device-tree/model"), platform.machine()),
        "version": _text(ROOT / "VERSION", "unknown"),
        "build": _text(ROOT / "BUILD", "development"),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "domain": "135er-Grow-Central.local",
    }


@router.get("/info")
async def system_info():
    return system_identity()
