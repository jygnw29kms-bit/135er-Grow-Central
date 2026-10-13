"""Interpret agent heartbeats consistently for desktop and mobile clients."""
from datetime import datetime, timezone
import math


def connection_state(runtime: dict, *, enabled: bool, origin: str | None = None,
                     now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    age = None
    try:
        updated = datetime.fromisoformat(runtime["updated_at"])
        if updated.tzinfo is not None:
            age = (now - updated).total_seconds()
    except (KeyError, TypeError, ValueError, OverflowError):
        pass
    try:
        interval = float(runtime.get("retry_seconds", 30))
        if not math.isfinite(interval):
            interval = 30
    except (TypeError, ValueError, OverflowError):
        interval = 30
    # Allow for diagnostics (35s), bundle uploads (90s) and scheduling delays.
    max_age = max(180, 3 * min(max(interval, 10), 3600) + 180)
    runtime_origin = runtime.get("cloud_origin")
    mismatch = origin is not None and (not isinstance(runtime_origin, str) or runtime_origin.rstrip("/") != origin)
    stale = bool(runtime) and (age is None or age < -30 or age > max_age or mismatch)
    state = "disabled" if not enabled else (
        "stale" if stale else str(runtime.get("state") or "starting")
    )
    detail = str(runtime.get("detail") or "")
    if not enabled:
        detail = "Cloud-Link deaktiviert"
    elif stale:
        detail = "Cloud-Status gehört zu einem anderen Server" if mismatch else "Cloud-Status ist nicht aktuell"
    return {
        "state": state,
        "connected": enabled and state == "connected",
        "stale": stale,
        "age_seconds": round(max(0, age), 1) if age is not None else None,
        "updated_at": runtime.get("updated_at"),
        "detail": detail,
    }
