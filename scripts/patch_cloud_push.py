#!/usr/bin/env python3
"""Render the additive Cloud account-bound push route patch; never installs it."""
from __future__ import annotations
import argparse
from pathlib import Path

MARKER = "# GROW_CENTRAL_BETA_ACCOUNT_PUSH_V1"
REQUIRED = ("app = FastAPI(", "def account_from_access(", "def get_device_for_account(",
            "engine = create_engine(")
APPEND = f"""

{MARKER}
from cloud_push import ensure_schema as _gc_push_schema
from cloud_push import build_router as _gc_push_router
_gc_push_schema(engine)
app.include_router(_gc_push_router(
    engine,
    account_from_access=account_from_access,
    get_device_for_account=get_device_for_account,
))
"""


def patch_app(source: str) -> str:
    if MARKER in source:
        if source.endswith(APPEND):
            return source
        raise ValueError("Existing Cloud Push integration differs; refusing patch")
    for anchor in REQUIRED:
        if anchor not in source:
            raise ValueError(f"Cloud backend structure changed: {anchor}")
    if "from cloud_push import" in source:
        raise ValueError("Conflicting Cloud Push integration")
    return source.rstrip() + "\n" + APPEND


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite existing backend")
    args.output.write_text(patch_app(args.source.read_text(encoding="utf-8")), encoding="utf-8")
    print("Cloud push patch rendered; not installed")


if __name__ == "__main__":
    raise SystemExit(main())
