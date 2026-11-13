"""Grow Central: one approved desktop/mobile/PWA GUI."""
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
router = APIRouter(tags=["gui-shell"])

@router.get("/ui", include_in_schema=False)
async def gui_shell():
    return FileResponse(WEB_DIR / "gc-final.html", headers={"Cache-Control":"no-store"})

@router.get("/mobile", include_in_schema=False)
async def mobile_gui():
    return RedirectResponse("/ui", status_code=308)

@router.get("/rooms", include_in_schema=False)
async def room_workspace():
    return RedirectResponse("/ui", status_code=308)

@router.get("/ui-legacy", include_in_schema=False)
async def retired_gui():
    return RedirectResponse("/ui", status_code=308)

@router.get("/gc-worker.js", include_in_schema=False)
async def gui_pwa_worker():
    return FileResponse(WEB_DIR / "gc-worker.js", media_type="application/javascript",
                        headers={"Cache-Control":"no-cache","Service-Worker-Allowed":"/"})