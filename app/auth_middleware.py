"""Unified GUI/API authentication boundary for the local appliance."""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.gui_auth import authenticated, configured
from app.security import api_token_authenticated


class GuiAuthMiddleware(BaseHTTPMiddleware):
    """Protect browser surfaces while allowing authenticated API clients.

    GUI users authenticate with the HttpOnly session cookie. Service clients
    such as the local cloud-link may access only API paths and must present the
    per-device API token. The first-boot portal remains the outer middleware and
    therefore owns all unprovisioned traffic.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        public = (
            path == "/api/health"
            or path == "/login"
            or path.startswith("/api/auth/")
            or path.startswith("/static/")
        )
        if public:
            return await call_next(request)

        if not configured():
            if path.startswith("/api/"):
                return JSONResponse(
                    {"detail": "GUI authentication is not configured; complete first-boot setup"},
                    status_code=503,
                )
            return HTMLResponse(
                "<h1>135er-Grow Central</h1><p>First-Boot-Setup noch nicht abgeschlossen.</p>",
                status_code=503,
            )

        if authenticated(request):
            if path == "/":
                return RedirectResponse("/ui", status_code=303)
            return await call_next(request)

        # API tokens never grant browser/page access. They exist only for local
        # service-to-service/API traffic such as the Pi cloud-link.
        if path.startswith("/api/") and api_token_authenticated(request):
            return await call_next(request)

        if path.startswith("/api/"):
            return JSONResponse({"detail": "GUI login or API token required"}, status_code=401)
        return RedirectResponse("/login", status_code=303)
