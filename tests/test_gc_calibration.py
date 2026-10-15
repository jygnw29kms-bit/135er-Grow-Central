import os
import asyncio
from types import SimpleNamespace

import pytest

from app.devices.gc_calibration import CalibrationStore, derive_soil_reference_metrics, calibration_status
from app.devices.gc_trust import TrustStore
from app.devices import gc_calibration


def test_calibration_record_binds_identity_hardware_firmware(tmp_path):
    store=CalibrationStore(tmp_path/'calibration.db')
    row=store.record(device_id='gc-soil-aabbcc',fingerprint='a'*64,public_key='public-key',hardware_uid='0011223344556677',firmware_version='0.5.2',air_raw=3767,wet_raw=1310,substrate_raw=2500,quality={'status':'verified','signal_quality':'GOOD'})
    assert row['valid'] is True and row['points']['span_raw']==2457
    assert store.require_valid('gc-soil-aabbcc',fingerprint='a'*64,public_key='public-key',hardware_uid='0011223344556677',firmware_version='0.5.2')['valid']
    with pytest.raises(PermissionError):
        store.require_valid('gc-soil-aabbcc',hardware_uid='8899aabbccddeeff')
    invalid=store.get('gc-soil-aabbcc')
    assert invalid['valid'] is False and 'hardware' in invalid['invalidation_reason']
    if os.name != 'nt':
        assert (tmp_path/'calibration.db').stat().st_mode & 0o777 == 0o600


def test_calibration_rejects_implausible_span(tmp_path):
    with pytest.raises(ValueError):
        CalibrationStore(tmp_path/'cal.db').record(device_id='gc-soil-aabbcc',fingerprint='a'*64,public_key='k',hardware_uid='0011223344556677',firmware_version='0.5.2',air_raw=2000,wet_raw=1950,substrate_raw=1975,quality={})


def test_status_api_marks_missing_record_required(tmp_path,monkeypatch):
    monkeypatch.setenv('GC_DEVICE_TRUST_DB',str(tmp_path/'trust.db'))
    monkeypatch.setenv('GC_CALIBRATION_DB',str(tmp_path/'calibration.db'))
    trust=TrustStore()
    with trust.db() as db:
        db.execute('INSERT INTO devices VALUES(?,?,?,?,?,?,?,?,?,?)',('gc-soil-aabbcc','TRUSTED','key','f'*64,1,'{"model":"soil","firmware":"0.5.1","capabilities":["soil_moisture"],"reported_name":"Soil"}','Sensor','room1','now','now'))
    class Provider:
        async def health(self,_id): return SimpleNamespace(online=True)
    monkeypatch.setattr(gc_calibration.runtime,'get',lambda _:Provider())
    result=asyncio.run(calibration_status())
    assert result['devices'][0]['calibration_status']=='required'
    assert result['devices'][0]['reason']=='Kalibrierung erforderlich'
    assert result['devices'][0]['online'] is True


def test_three_point_reference_metrics_use_substrate_without_redefining_moisture():
    points={"air_raw":3770,"wet_raw":1180,"substrate_raw":2027}
    at_reference=derive_soil_reference_metrics(2027,points)
    assert at_reference["soil_moisture_percent"] == pytest.approx(67.297, abs=0.002)
    assert at_reference["soil_substrate_reference_percent"] == pytest.approx(67.297, abs=0.002)
    assert at_reference["soil_substrate_index_percent"] == pytest.approx(100.0)
    assert at_reference["soil_substrate_delta_pp"] == pytest.approx(0.0)
    assert at_reference["soil_substrate_state"] == "near_reference"
    dry=derive_soil_reference_metrics(3770,points)
    wet=derive_soil_reference_metrics(1180,points)
    assert dry["soil_moisture_percent"] == 0.0 and dry["soil_substrate_index_percent"] == 0.0
    assert wet["soil_moisture_percent"] == 100.0 and wet["soil_substrate_index_percent"] > 100.0


def test_three_point_reference_metrics_reject_invalid_geometry():
    with pytest.raises(ValueError):
        derive_soil_reference_metrics(2000,{"air_raw":2000,"wet_raw":1900,"substrate_raw":1950})
