#!/usr/bin/env python3
"""Render an additive, auditable Cloud collaboration API integration patch.

No credentials, tokens, databases or running services are inspected here.
Never install a patched app without Python syntax, rollback and HTTP tests.
"""
from __future__ import annotations

import argparse
from pathlib import Path

MARKER = "# GROW_CENTRAL_BETA_ROOM_COLLABORATION_V1"
REQUIRED = (
    "app = FastAPI(",
    "def account_from_access(",
    "def get_device_for_account(",
    "init_db()",
    "PUBLIC_URL",
    "engine = create_engine(",
)
APPEND = f'''

{MARKER}
# Additive account-bound room invitations; does NOT enable guest WebSockets.
from cloud_room_membership import ensure_schema as _gc_room_schema
from cloud_room_membership import build_router as _gc_room_router
_gc_room_schema(engine)
app.include_router(_gc_room_router(
    engine,
    account_from_access=account_from_access,
    get_device_for_account=get_device_for_account,
    public_url=PUBLIC_URL,
))
'''


def patch_app(source: str) -> str:
    if MARKER in source:
        if source.endswith(APPEND):
            return source
        raise ValueError("Existing collaboration block differs; manual review required")
    for anchor in REQUIRED:
        if anchor not in source:
            raise ValueError(f"Unexpected Cloud app structure: {anchor}")
    if "cloud_room_membership" in source:
        raise ValueError("Cloud app already contains a different membership import")
    return source.rstrip() + "\n" + APPEND


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be a new file; refusing overwrite")
    result = patch_app(args.source.read_text(encoding="utf-8"))
    args.output.write_text(result, encoding="utf-8")
    print("Rendered additive Cloud room-membership integration; not installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
