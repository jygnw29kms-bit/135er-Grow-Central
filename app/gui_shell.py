"""Redesigned Grow Central GUI shell while preserving the proven device UI."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
router = APIRouter(tags=["gui-shell"])


@router.get("/ui", include_in_schema=False)
async def gui_shell():
    return FileResponse(WEB_DIR / "console.html")


@router.get("/legacy", include_in_schema=False)
async def legacy_gui():
    return FileResponse(WEB_DIR / "index.html")
