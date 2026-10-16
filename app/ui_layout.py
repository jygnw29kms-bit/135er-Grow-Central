"""Persist and serve the editable Grow-Central Final-Master layout."""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.audit import append_audit
from app.security import require_write_auth

router = APIRouter(prefix="/api/v1/ui-layout", tags=["UI layout"])
LAYOUT_FILE = Path(os.getenv("GC_UI_LAYOUT_FILE", "/var/lib/135er-grow-central/ui-layout.json"))
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_ALLOWED_TYPES = {"hero", "status", "metric", "panel", "table", "filters", "camera", "spacer"}
_ALLOWED_HEIGHTS = {"s", "m", "l"}
_MAX_PAGES = 64
_MAX_WIDGETS = 128
_MAX_BYTES = 256 * 1024


def _text(value: Any, limit: int = 300) -> str:
    text = str(value or "")
    if len(text) > limit:
        raise ValueError("text field too long")
    return text


def validate_layout(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("layout must be an object")
    if int(payload.get("version") or 0) != 2:
        raise ValueError("unsupported layout version")
    shell = payload.get("shell")
    pages = payload.get("pages")
    if not isinstance(shell, dict) or not isinstance(pages, list) or not pages or len(pages) > _MAX_PAGES:
        raise ValueError("invalid shell/pages")

    clean_shell = {
        "brand": _text(shell.get("brand"), 80),
        "sidebarWidth": max(160, min(360, int(shell.get("sidebarWidth") or 224))),
        "gap": max(0, min(40, int(shell.get("gap") or 10))),
        "topbar": shell.get("topbar") is not False,
        "sidebar": shell.get("sidebar") is not False,
        "rounded": shell.get("rounded") is not False,
    }

    seen_pages: set[str] = set()
    seen_widgets: set[str] = set()
    clean_pages: list[dict[str, Any]] = []
    default_seen = False
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("invalid page")
        page_id = _text(page.get("id"), 64)
        target = _text(page.get("target") or page_id, 64)
        if not _ID_RE.fullmatch(page_id) or not _ID_RE.fullmatch(target) or page_id in seen_pages:
            raise ValueError("invalid/duplicate page id")
        seen_pages.add(page_id)
        widgets = page.get("widgets")
        if not isinstance(widgets, list) or len(widgets) > _MAX_WIDGETS:
            raise ValueError("invalid widgets")
        clean_widgets: list[dict[str, Any]] = []
        for widget in widgets:
            if not isinstance(widget, dict):
                raise ValueError("invalid widget")
            widget_id = _text(widget.get("id"), 64)
            kind = _text(widget.get("type"), 32)
            if not _ID_RE.fullmatch(widget_id) or widget_id in seen_widgets or kind not in _ALLOWED_TYPES:
                raise ValueError("invalid/duplicate widget")
            seen_widgets.add(widget_id)
            width = int(widget.get("width") or 12)
            height = _text(widget.get("height") or "m", 8)
            if not 1 <= width <= 12 or height not in _ALLOWED_HEIGHTS:
                raise ValueError("invalid widget geometry")
            binding = _text(widget.get("binding"), 64)
            if binding and not _ID_RE.fullmatch(binding):
                raise ValueError("invalid binding")
            clean_widgets.append({
                "id": widget_id,
                "type": kind,
                "title": _text(widget.get("title"), 160),
                "kicker": _text(widget.get("kicker"), 100),
                "text": _text(widget.get("text"), 600),
                "width": width,
                "height": height,
                "binding": binding,
                "visible": widget.get("visible") is not False,
                "advanced": bool(widget.get("advanced")),
            })
        parent = page.get("parent")
        parent = _text(parent, 64) if parent else None
        if parent and not _ID_RE.fullmatch(parent):
            raise ValueError("invalid parent")
        is_default = bool(page.get("default")) and not default_seen
        default_seen = default_seen or is_default
        clean_pages.append({
            "id": page_id,
            "label": _text(page.get("label") or page_id, 80),
            "title": _text(page.get("title") or page.get("label") or page_id, 120),
            "icon": _text(page.get("icon"), 12),
            "target": target,
            "parent": parent,
            "visible": page.get("visible") is not False,
            "advanced": bool(page.get("advanced")),
            "default": is_default,
            "widgets": clean_widgets,
        })
    valid_ids = {page["id"] for page in clean_pages}
    for page in clean_pages:
        if page["parent"] not in valid_ids:
            page["parent"] = None
    if not any(page["default"] for page in clean_pages):
        clean_pages[0]["default"] = True

    result = {
        "version": 2,
        "source": "grow-central-platform",
        "updatedAt": _text(payload.get("updatedAt"), 64),
        "shell": clean_shell,
        "pages": clean_pages,
    }
    if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > _MAX_BYTES:
        raise ValueError("layout too large")
    return result


def load_layout() -> dict[str, Any] | None:
    try:
        return validate_layout(json.loads(LAYOUT_FILE.read_text(encoding="utf-8")))
    except FileNotFoundError:
        return None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def save_layout(layout: dict[str, Any]) -> None:
    LAYOUT_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    data = json.dumps(layout, ensure_ascii=False, separators=(",", ":")) + "\n"
    descriptor, name = tempfile.mkstemp(prefix=".ui-layout-", suffix=".json", dir=LAYOUT_FILE.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, 0o640)
        os.replace(name, LAYOUT_FILE)
    finally:
        try:
            if os.path.exists(name):
                os.unlink(name)
        except OSError:
            pass


@router.get("")
async def get_layout():
    return {"layout": load_layout()}


@router.put("", dependencies=[Depends(require_write_auth)])
async def put_layout(body: dict[str, Any]):
    try:
        layout = validate_layout(body)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    save_layout(layout)
    append_audit("ui.layout.saved", pages=len(layout["pages"]))
    return {"ok": True, "layout": layout}


@router.delete("", dependencies=[Depends(require_write_auth)])
async def delete_layout():
    LAYOUT_FILE.unlink(missing_ok=True)
    append_audit("ui.layout.reset")
    return {"ok": True}
