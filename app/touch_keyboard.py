"""Inject the local Grow Central touch keyboard into HTML responses.

The appliance kiosk runs a minimal X11/Chromium stack without depending on a
full desktop on-screen keyboard. The keyboard assets are injected centrally so
First Boot, Login and the normal UI all behave consistently.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

ASSETS = (
    '<link rel="stylesheet" href="/static/touch_keyboard.css?v=1">'
    '<script defer src="/static/touch_keyboard.js?v=1"></script>'
)


class TouchKeyboardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        content_type = response.headers.get("content-type", "").lower()
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
        return Response(
            content=text.encode("utf-8"),
            status_code=response.status_code,
            headers=headers,
            media_type=None,
            background=response.background,
        )
