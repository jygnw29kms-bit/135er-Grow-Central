"""Read-only grow alerts derived from explicit room thresholds."""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from typing import Any

from fastapi import APIRouter

from app.rooms import load_state

router = APIRouter(prefix="/api/v1/grow-alerts", tags=["grow alerts"])
FRESH_SECONDS = 15 * 60


def _age_seconds(timestamp: Any, now: datetime) -> float | None:
    if not isinstance(timestamp, str) or not timestamp.strip():
        return None
    try:
        value = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max(0.0, (now - value.astimezone(timezone.utc)).total_seconds())


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if isfinite(result) else None


def evaluate_grow_alerts(state: dict[str, Any], *, now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    alerts: list[dict[str, Any]] = []
    history = state.get("sensor_history") or []
    for room in state.get("rooms") or []:
        low = _number(room.get("soil_reference_low_index_percent"))
        high = _number(room.get("soil_reference_high_index_percent"))
        if low is None and high is None:
            continue
        latest = next((row for row in reversed(history) if row.get("room_id") == room.get("id")), None)
        base = {"room_id": room.get("id"), "room_name": room.get("name") or room.get("id"), "source": "soil_reference"}
        if not latest:
            alerts.append({**base, "kind": "soil_no_data", "severity": "warning", "message": "Keine Bodenfeuchte-Messung f\u00fcr konfigurierte Warnschwellen."})
            continue
        age = _age_seconds(latest.get("timestamp"), now)
        if age is None or age > FRESH_SECONDS:
            alerts.append({**base, "kind": "soil_stale", "severity": "warning", "timestamp": latest.get("timestamp"), "age_seconds": age, "message": "Bodenfeuchte-Messung ist zu alt f\u00fcr eine sichere Schwellenbewertung."})
            continue
        if latest.get("soil_calibration_status") != "valid":
            alerts.append({**base, "kind": "soil_calibration_required", "severity": "warning", "timestamp": latest.get("timestamp"), "message": "Dreipunkt-Kalibrierung ist f\u00fcr die Soil-Warnschwellen nicht g\u00fcltig."})
            continue
        index = _number(latest.get("soil_substrate_index_percent"))
        if index is None:
            alerts.append({**base, "kind": "soil_reference_missing", "severity": "warning", "timestamp": latest.get("timestamp"), "message": "Frischsubstrat-Index fehlt trotz konfigurierter Warnschwelle."})
            continue
        if low is not None and index < low:
            alerts.append({**base, "kind": "soil_below_reference_threshold", "severity": "warning", "timestamp": latest.get("timestamp"), "value": round(index, 2), "threshold": low, "message": f"Frischsubstrat-Index {index:.0f} % liegt unter der Warnschwelle {low:.0f} %."})
        if high is not None and index > high:
            alerts.append({**base, "kind": "soil_above_reference_threshold", "severity": "warning", "timestamp": latest.get("timestamp"), "value": round(index, 2), "threshold": high, "message": f"Frischsubstrat-Index {index:.0f} % liegt \u00fcber der Warnschwelle {high:.0f} %."})
    return alerts


@router.get("")
async def grow_alerts():
    alerts = evaluate_grow_alerts(load_state())
    return {"alerts": alerts, "count": len(alerts), "policy": "explicit_thresholds_read_only"}
