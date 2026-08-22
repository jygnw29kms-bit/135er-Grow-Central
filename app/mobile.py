"""LAN-only mobile/PWA entry points for 135er-Grow Central."""
from __future__ import annotations

import ipaddress
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

router = APIRouter(tags=["mobile"])
WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def _client_is_lan(request: Request) -> bool:
    """Reject clearly public client IPs while allowing local proxies/test clients."""
    host = request.client.host if request.client else ""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local)


def _require_lan(request: Request) -> None:
    if not _client_is_lan(request):
        raise HTTPException(status_code=403, detail="GrowCentral Mobile ist in dieser Version nur im lokalen Netzwerk verfügbar.")


@router.get("/mobile", include_in_schema=False)
async def mobile_app(request: Request):
    _require_lan(request)
    return FileResponse(WEB_DIR / "mobile.html", media_type="text/html")


@router.get("/mobile.webmanifest", include_in_schema=False)
async def mobile_manifest(request: Request):
    _require_lan(request)
    return FileResponse(WEB_DIR / "mobile.webmanifest", media_type="application/manifest+json")


@router.get("/mobile-sw.js", include_in_schema=False)
async def mobile_service_worker(request: Request):
    _require_lan(request)
    response = FileResponse(WEB_DIR / "mobile-sw.js", media_type="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@router.get("/api/mobile/config")
async def mobile_config(request: Request):
    _require_lan(request)
    hostname = request.url.hostname or "135er-Grow-Central.local"
    return {
        "name": "135er GrowCentral Mobile",
        "mode": "lan_only",
        "local_only": True,
        "hostname": hostname,
        "origin": str(request.base_url).rstrip("/"),
        "secure_context": request.url.scheme == "https",
        "install_path": "/mobile",
        "api_base": "/api",
    }
