"""Inject approved Grow-Central grow enhancements into product HTML shells.

The Final Master HTML files remain untouched. Only positively identified product
shells receive the local photo-journal and Plant-Doctor enhancement scripts.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_SCRIPTS = (
    '<script src="/static/grow-photos.js?v=20261016-photo1"></script>',
    '<script src="/static/plant-doctor.js?v=20261016-doctor1"></script>',
)
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
        additions = [script for script in _SCRIPTS if script.split('src="', 1)[1].split('"', 1)[0].split('?', 1)[0] not in html]
        if additions:
            html = html.replace("</body>", "\n".join(additions) + "\n</body>", 1)

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
