#!/usr/bin/env python3
"""Render an additive isolated guest-WebSocket integration for Cloud v4.

The owner WebSocket remains owner-only. Device responses whose random internal
request_id belongs to a guest are consumed privately and never broadcast.
Requires independently tested Cloud membership module and database schema.
"""
from __future__ import annotations

import argparse
from pathlib import Path

MARKER = "# GROW_CENTRAL_BETA_GUEST_WEBSOCKET_V1"
ANCHOR = "            await broadcast_to_clients(device_id, payload)"
GUARD = """            # Private Cloud room-guest replies are never broadcast to owner
            # device-wide subscribers or unrelated guest sessions.
            if await _gc_guest_remote.dispatch_device_result(device_id, payload):
                continue
            await broadcast_to_clients(device_id, payload)"""
APPEND = f'''

{MARKER}
from cloud_guest_remote import install_guest_remote as _gc_install_guest_remote
_gc_guest_remote = _gc_install_guest_remote(
    app, engine=engine, account_from_access=account_from_access,
    device_sockets=device_sockets, socket_lock=socket_lock,
)
'''


def patch_app(source: str) -> str:
    if MARKER in source:
        if source.endswith(APPEND) and GUARD in source:
            return source
        raise ValueError("Existing guest WebSocket patch differs; manual review required")
    if source.count(ANCHOR) != 1:
        raise ValueError("Unexpected Cloud device broadcast loop")
    for item in (
        "# GROW_CENTRAL_BETA_ROOM_COLLABORATION_V1",
        "def account_from_access(",
        "device_sockets: dict[str, WebSocket]",
        "@app.websocket(\"/api/v2/remote/connect\")",
        "socket_lock = asyncio.Lock()",
    ):
        if item not in source:
            raise ValueError(f"Missing Cloud owner-only integration anchor: {item}")
    return source.replace(ANCHOR, GUARD).rstrip() + "\n" + APPEND


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be a new file")
    patched = patch_app(args.source.read_text(encoding="utf-8"))
    args.output.write_text(patched, encoding="utf-8")
    print("Rendered guest WebSocket isolation patch; not installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
