"""Inject kiosk/touch runtime assets into local Grow Central HTML responses.

Uses the ASGI interface directly so HTML rewriting always emits an exact
Content-Length. This avoids the BaseHTTPMiddleware streaming edge case observed
on the Raspberry Pi while retaining no-cache handling for local UI assets.
"""
from __future__ import annotations

ASSETS = (
    '<link rel="stylesheet" href="/static/touch_keyboard.css?v=2">'
    '<script defer src="/static/touch_keyboard.js?v=2"></script>'
    '<script defer src="/static/runtime_health_fix.js?v=1"></script>'
)

_NO_CACHE = [
    (b"cache-control", b"no-store, no-cache, must-revalidate, max-age=0"),
    (b"pragma", b"no-cache"),
    (b"expires", b"0"),
]


class TouchKeyboardMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        no_cache = path.startswith(("/ui", "/login", "/static/"))
        start_message = None
        transform = False
        chunks: list[bytes] = []

        def adjusted_headers(headers, *, body_length: int | None = None):
            drop = {b"cache-control", b"pragma", b"expires"} if no_cache else set()
            if body_length is not None:
                drop |= {b"content-length", b"etag", b"content-md5"}
            result = [(k, v) for k, v in headers if k.lower() not in drop]
            if no_cache:
                result.extend(_NO_CACHE)
            if body_length is not None:
                result.append((b"content-length", str(body_length).encode("ascii")))
            return result

        async def wrapped_send(message):
            nonlocal start_message, transform
            if message["type"] == "http.response.start":
                start_message = message
                status = int(message.get("status", 200))
                headers = message.get("headers", [])
                content_type = next(
                    (v.decode("latin-1").lower() for k, v in headers if k.lower() == b"content-type"),
                    "",
                )
                transform = (
                    "text/html" in content_type
                    and scope.get("method", "GET").upper() != "HEAD"
                    and status not in {204, 304}
                )
                if not transform:
                    await send({**message, "headers": adjusted_headers(headers)})
                return

            if message["type"] != "http.response.body" or not transform:
                await send(message)
                return

            chunks.append(message.get("body", b""))
            if message.get("more_body", False):
                return

            body = b"".join(chunks)
            text = body.decode("utf-8", "replace")
            if "touch_keyboard.js" not in text:
                if "</head>" in text:
                    text = text.replace("</head>", ASSETS + "</head>", 1)
                elif "</body>" in text:
                    text = text.replace("</body>", ASSETS + "</body>", 1)
                else:
                    text += ASSETS
            body = text.encode("utf-8")

            assert start_message is not None
            headers = adjusted_headers(start_message.get("headers", []), body_length=len(body))
            await send({**start_message, "headers": headers})
            await send({"type": "http.response.body", "body": body, "more_body": False})

        await self.app(scope, receive, wrapped_send)
