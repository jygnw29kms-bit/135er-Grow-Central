"""Room telemetry should capture signed soil faults without stale percentages."""
import asyncio
from app import rooms


def test_fault_does_not_repeat_stale_soil_percent(tmp_path,monkeypatch):
    monkeypatch.setattr(rooms, "DATA_FILE", tmp_path/"rooms.json")
    state=rooms.empty_state()
    state["rooms"]=[{"id":"room_1","name":"Grow Zelt"}]
    state["assignments"]={"growcentral_esp32:gc-soil-test":"room_1"}
    rooms.append_sensor(state,"room_1",{"soil_moisture_percent":100.0,"source":"historical"})
    rooms.save_state(state)
    async def overview(*,refresh): return {"devices":[]}
    async def native(*,timeout):
        return [{"id":"growcentral_esp32:gc-soil-test","online":True,
                 "state":{"soil_moisture":None,"meta":{"calibration_status":"valid",
                       "sensor_ok":False,"measurement_status":"sensor_fault"}}}]
    monkeypatch.setattr(rooms,"device_overview",overview)
    monkeypatch.setattr(rooms,"_native_gc_devices",native)
    assert asyncio.run(rooms.capture_room_sensors_once())==1
    after=rooms.load_state()
    latest=rooms._latest_sensor_snapshot(after,"room_1")
    assert latest.get("soil_moisture_percent") is None
    assert latest["soil_measurement_status"]=="sensor_fault"
    assert latest["soil_calibration_status"]=="valid"
    assert after["sensor_history"][-2]["soil_moisture_percent"]==100.0
    assert after["sensor_history"][-1]["soil_moisture_percent"] is None
