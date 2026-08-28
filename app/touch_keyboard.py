"""Inject kiosk/touch runtime assets into local Grow Central HTML responses.

The appliance kiosk runs a minimal X11/Chromium stack without depending on a
full desktop on-screen keyboard. Runtime assets are injected centrally so
First Boot, Login and the normal UI all behave consistently. UI assets are
served without persistent browser caching because a first-boot network change
must never leave stale health-check JavaScript behind.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

ASSETS = (
    '<link rel="stylesheet" href="/static/touch_keyboard.css?v=2">'
    '<script defer src="/static/touch_keyboard.js?v=2"></script>'
    '<script defer src="/static/runtime_health_fix.js?v=1"></script>'
)


class TouchKeyboardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        content_type = response.headers.get("content-type", "").lower()
        path = request.url.path

        # The local UI changes frequently during appliance updates. Prevent an
        # old app.js from surviving a first-boot WLAN switch or image upgrade.
        if path.startswith("/ui") or path.startswith("/login") or path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        if "text/html" not in content_type:
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        text = body.decode("utf-8", "replace")
        if "touch_keyboard.js" not in text:
            if "</head>" in text:
                text = text.replace("</head>", ASSETS + "</head>", 1)
            elif "</body>" in text:
                text = text.replace("</body>", ASSETS + "</body>", 1)
            else:
                text += ASSETS

        headers = dict(response.headers)
        headers.pop("content-length", None)
        headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        headers["Pragma"] = "no-cache"
        headers["Expires"] = "0"
        return Response(
            content=text.encode("utf-8"),
            status_code=response.status_code,
            headers=headers,
            media_type=None,
            background=response.background,
        )
