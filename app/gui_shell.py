"""Grow Central GUI routes.

The productive desktop route is the approved GrowCentral Final Master.
The former console remains available only through the explicit legacy route.
"""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
router = APIRouter(tags=["gui-shell"])


@router.get("/ui", include_in_schema=False)
async def gui_shell():
    """Serve the approved GrowCentral Final Master desktop UI."""
    return FileResponse(WEB_DIR / "platform.html", headers={"Cache-Control": "no-store"})


@router.get("/mobile", include_in_schema=False)
async def mobile_gui():
    """Dedicated touch-first UI for phones and compact mobile devices."""
    return FileResponse(WEB_DIR / "mobile.html", headers={"Cache-Control": "no-store"})


@router.get("/legacy", include_in_schema=False)
async def legacy_gui():
    """Keep the proven diagnostic/transition console available explicitly."""
    console = WEB_DIR / "console.html"
    return FileResponse(console if console.exists() else WEB_DIR / "index.html", headers={"Cache-Control": "no-store"})
