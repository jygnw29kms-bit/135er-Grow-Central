from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.grow_alerts import evaluate_grow_alerts
from app.rooms import RoomCreate

NOW=datetime(2026,10,15,18,0,tzinfo=timezone.utc)

def state(*, index=60.0, status="valid", age_minutes=1, low=70.0, high=140.0):
    room={"id":"r1","name":"Zelt 1","soil_reference_low_index_percent":low,"soil_reference_high_index_percent":high}
    sample={"room_id":"r1","timestamp":(NOW-timedelta(minutes=age_minutes)).isoformat(),"soil_substrate_index_percent":index,"soil_calibration_status":status}
    return {"rooms":[room],"sensor_history":[sample]}

def test_no_explicit_threshold_means_no_alert():
    payload=state(low=None,high=None)
    assert evaluate_grow_alerts(payload,now=NOW)==[]

def test_low_and_high_reference_thresholds_are_read_only_warnings():
    low=evaluate_grow_alerts(state(index=60),now=NOW)
    assert len(low)==1 and low[0]["kind"]=="soil_below_reference_threshold" and low[0]["threshold"]==70
    high=evaluate_grow_alerts(state(index=155),now=NOW)
    assert len(high)==1 and high[0]["kind"]=="soil_above_reference_threshold" and high[0]["threshold"]==140
    assert evaluate_grow_alerts(state(index=100),now=NOW)==[]

def test_stale_or_uncalibrated_data_never_raises_numeric_threshold_alert():
    stale=evaluate_grow_alerts(state(index=40,age_minutes=20),now=NOW)
    assert [row["kind"] for row in stale]==["soil_stale"]
    invalid=evaluate_grow_alerts(state(index=40,status="required"),now=NOW)
    assert [row["kind"] for row in invalid]==["soil_calibration_required"]

def test_room_threshold_order_is_validated():
    with pytest.raises(ValidationError):
        RoomCreate(name="Zelt",soil_reference_low_index_percent=120,soil_reference_high_index_percent=80)
    room=RoomCreate(name="Zelt",soil_reference_low_index_percent=70,soil_reference_high_index_percent=140)
    assert room.soil_reference_low_index_percent==70 and room.soil_reference_high_index_percent==140


def test_alert_api_exposes_read_only_policy(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.grow_alerts as alerts
    payload=state(index=60)
    payload["sensor_history"][0]["timestamp"]=datetime.now(timezone.utc).isoformat()
    monkeypatch.setattr(alerts,"load_state",lambda:payload)
    app=FastAPI();app.include_router(alerts.router)
    response=TestClient(app).get("/api/v1/grow-alerts")
    assert response.status_code==200
    body=response.json()
    assert body["policy"]=="explicit_thresholds_read_only"
    assert body["count"]==1 and body["alerts"][0]["kind"]=="soil_below_reference_threshold"
