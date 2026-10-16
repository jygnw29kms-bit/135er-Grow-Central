"""Inject the grow photo journal enhancement into approved Grow-Central HTML shells.

The master HTML files remain untouched; only responses that are positively
identified as the Grow-Central UI receive the small enhancement script.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_SCRIPT = '<script src="/static/grow-photos.js?v=20261016-photo1"></script>'
_TARGET_PATHS = {"/", "/ui", "/mobile"}


class GrowPhotoUiMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path not in _TARGET_PATHS:
            return response
        if "text/html" not in (response.headers.get("content-type") or ""):
            return response

        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
        raw = b"".join(chunks)
        try:
            html = raw.decode("utf-8")
        except UnicodeDecodeError:
            return Response(
                content=raw,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
                background=response.background,
            )

        # Do not alter captive/setup/legacy HTML. Only enhance the current
        # product shells that contain the known Grow-Central navigation/runtime.
        if "growlog" not in html or "/static/menu-live.js" not in html:
            return Response(
                content=raw,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
                background=response.background,
            )
        if "/static/grow-photos.js" not in html:
            html = html.replace("</body>", f"{_SCRIPT}\n</body>", 1)

        headers = dict(response.headers)
        headers.pop("content-length", None)
        headers["Cache-Control"] = "no-store"
        return Response(
            content=html,
            status_code=response.status_code,
            headers=headers,
            media_type="text/html",
            background=response.background,
        )
