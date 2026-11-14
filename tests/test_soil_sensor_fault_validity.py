"""Faulty ADC readings must never become a valid 100 % soil measurement."""
import asyncio
from types import SimpleNamespace

import pytest
from app.devices import gc_esp32


@pytest.mark.parametrize("sensor_meta,expected_status", [
    ({"sensor_ok":False,"quality":"POOR","moisture_state":"SENSOR_FAULT","filtered_raw":669.0},"sensor_fault"),
    ({"sensor_ok":True,"quality":"GOOD","moisture_state":"WET","filtered_raw":669.0},"out_of_calibration_range"),
    ({"sensor_ok":True,"quality":"EXCELLENT","moisture_state":"DRY","filtered_raw":3710.0},None),
])
def test_suppress_failed_and_out_of_range_soil_sensor(monkeypatch,sensor_meta,expected_status):
    class Trust:
        def require_trusted(self,unused):
            return {"fingerprint":"abc","metadata":{"capabilities":["soil_moisture"]}}
        def receive(self,unused):pass
    class Calibration:
        def require_valid(self,*args,**kwargs):
            return {"points":{"air_raw":3770,"wet_raw":1180,"substrate_raw":2027},"calibrated_at":"2026-11-14T10:00:00Z"}
    monkeypatch.setattr(gc_esp32,"TrustStore",lambda:Trust())
    monkeypatch.setattr(gc_esp32,"CalibrationStore",lambda:Calibration())
    provider=gc_esp32.GrowCentralEsp32Provider()
    async def proof(unused):
        return SimpleNamespace(public_key="key",body={
            "hardware_uid":"0011223344556677",
            "state":{"soil_moisture":100.0,"meta":{"firmware":"0.5.3",**sensor_meta}},
            "calibration":{"ready":True},
        })
    monkeypatch.setattr(provider,"prove_identity",proof)
    result=asyncio.run(provider.state("gc-soil-test"))
    assert result["meta"]["calibration_status"]=="valid"
    if expected_status:
        assert result["soil_moisture"] is None
        assert result["meta"]["measurement_status"]==expected_status
    else:
        assert 0 <= result["soil_moisture"] < 5.0
        assert result["meta"].get("measurement_status") is None
