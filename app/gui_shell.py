"""Grow Central GUI routes while preserving the proven legacy UI."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
router = APIRouter(tags=["gui-shell"])


@router.get("/ui", include_in_schema=False)
async def gui_shell():
    """Serve the existing console shell used by diagnostics and transition tools."""
    html = (WEB_DIR / "console.html").read_text(encoding="utf-8")
    if "mobile_runtime_fix.css" not in html:
        html = html.replace(
            "</head>",
            '<link rel="stylesheet" href="/static/mobile_runtime_fix.css?v=3">\n</head>',
            1,
        )
    if "mobile_runtime_fix.js" not in html:
        html = html.replace(
            "</body>",
            '<script src="/static/mobile_runtime_fix.js?v=3"></script>\n</body>',
            1,
        )
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@router.get("/mobile", include_in_schema=False)
async def mobile_gui():
    """Dedicated touch-first UI for phones and compact mobile devices."""
    return FileResponse(WEB_DIR / "mobile.html", headers={"Cache-Control": "no-store"})


@router.get("/legacy", include_in_schema=False)
async def legacy_gui():
    return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-store"})
