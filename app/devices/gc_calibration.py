"""Persistent calibration records for native Grow-Central sensors."""
from __future__ import annotations
from contextlib import contextmanager, closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3

SCHEMA_VERSION = 1
CALIBRATION_KIND = "soil_air_water_engineering_reference"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CalibrationStore:
    def __init__(self, path: Path | None = None):
        self.path = path or Path(os.getenv("GC_CALIBRATION_DB", "/var/lib/135er-grow-central/sensor-calibration.db"))

    @contextmanager
    def db(self):
        self.path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        os.chmod(self.path, 0o600)
        with closing(sqlite3.connect(self.path, timeout=3)) as db, db:
            db.row_factory = sqlite3.Row
            db.execute("""CREATE TABLE IF NOT EXISTS calibrations (
                device_id TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL,
                public_key TEXT NOT NULL,
                hardware_uid TEXT NOT NULL,
                capability TEXT NOT NULL,
                schema_version INTEGER NOT NULL,
                calibration_kind TEXT NOT NULL,
                points TEXT NOT NULL,
                quality TEXT NOT NULL,
                calibrated_at TEXT NOT NULL,
                firmware_version TEXT NOT NULL,
                valid INTEGER NOT NULL,
                invalidation_reason TEXT
            )""")
            columns = {row[1] for row in db.execute('PRAGMA table_info(calibrations)')}
            if 'hardware_uid' not in columns:
                db.execute("ALTER TABLE calibrations ADD COLUMN hardware_uid TEXT NOT NULL DEFAULT ''")
            db.execute('BEGIN IMMEDIATE')
            yield db

    @staticmethod
    def public(row):
        if row is None:
            return None
        result = dict(row)
        result["points"] = json.loads(result["points"])
        result["quality"] = json.loads(result["quality"])
        result["valid"] = bool(result["valid"])
        return result

    def get(self, device_id: str):
        with self.db() as db:
            return self.public(db.execute('SELECT * FROM calibrations WHERE device_id=?', (device_id,)).fetchone())

    def list(self):
        with self.db() as db:
            return [self.public(row) for row in db.execute('SELECT * FROM calibrations ORDER BY calibrated_at DESC,device_id')]

    def record(self, *, device_id: str, fingerprint: str, public_key: str, hardware_uid: str, firmware_version: str,
               air_raw: int, wet_raw: int, quality: dict, capability: str = 'soil_moisture'):
        if air_raw <= wet_raw + 100:
            raise ValueError('calibration span too small')
        points = {"air_raw": int(air_raw), "wet_raw": int(wet_raw), "span_raw": int(air_raw - wet_raw)}
        row = (device_id, fingerprint, public_key, hardware_uid, capability, SCHEMA_VERSION, CALIBRATION_KIND,
               json.dumps(points, separators=(',', ':')), json.dumps(quality, separators=(',', ':')),
               now_iso(), firmware_version, 1, None)
        with self.db() as db:
            db.execute('INSERT OR REPLACE INTO calibrations (device_id,fingerprint,public_key,hardware_uid,capability,schema_version,calibration_kind,points,quality,calibrated_at,firmware_version,valid,invalidation_reason) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', row)
            return self.public(db.execute('SELECT * FROM calibrations WHERE device_id=?', (device_id,)).fetchone())

    def invalidate(self, device_id: str, reason: str):
        with self.db() as db:
            db.execute('UPDATE calibrations SET valid=0,invalidation_reason=? WHERE device_id=?', (reason[:240], device_id))
            return self.public(db.execute('SELECT * FROM calibrations WHERE device_id=?', (device_id,)).fetchone())

    def require_valid(self, device_id: str, *, fingerprint: str | None = None,
                      public_key: str | None = None, hardware_uid: str | None = None, firmware_version: str | None = None):
        row = self.get(device_id)
        if not row or not row['valid']:
            raise PermissionError('sensor calibration required')
        if fingerprint and row['fingerprint'] != fingerprint:
            self.invalidate(device_id, 'identity fingerprint changed')
            raise PermissionError('sensor calibration identity mismatch')
        if public_key and row['public_key'] != public_key:
            self.invalidate(device_id, 'public key changed')
            raise PermissionError('sensor calibration key mismatch')
        if hardware_uid and row.get('hardware_uid') != hardware_uid:
            self.invalidate(device_id, 'hardware uid changed')
            raise PermissionError('sensor calibration hardware mismatch')
        if firmware_version and row['firmware_version'] != firmware_version:
            self.invalidate(device_id, 'firmware version changed')
            raise PermissionError('sensor calibration firmware changed')
        return row


# Read-only status API; calibration writes remain limited to the USB commissioning path.
from fastapi import APIRouter
import asyncio
from .gc_trust import TrustStore
from .runtime import runtime

router = APIRouter(prefix='/api/v1/sensor-calibration', tags=['sensor calibration'])

@router.get('')
async def calibration_status():
    records = {row['device_id']: row for row in CalibrationStore().list()}
    devices = []
    for trust in TrustStore().list():
        metadata = trust.get('metadata') or {}
        if 'soil_moisture' not in metadata.get('capabilities', []):
            continue
        record = records.get(trust['id'])
        reason = None
        if trust['status'] != 'TRUSTED': reason = 'Sensor noch nicht vollständig aufgenommen'
        elif not record: reason = 'Kalibrierung erforderlich'
        elif not record['valid']: reason = record.get('invalidation_reason') or 'Kalibrierung ungültig'
        elif record.get('fingerprint') != trust.get('fingerprint'): reason = 'Sensoridentität geändert'
        elif record.get('firmware_version') != metadata.get('firmware'): reason = 'Firmware geändert'
        devices.append({
            'device_id': trust['id'], 'name': trust.get('name') or metadata.get('reported_name') or trust['id'],
            'room_id': trust.get('room_id'), 'status': trust['status'], 'fingerprint': (trust.get('fingerprint') or '')[-16:],
            'firmware': metadata.get('firmware'), 'calibration': record,
            'calibration_status': 'valid' if record and record['valid'] and reason is None else 'required',
            'reason': reason, 'online': False,
        })
    provider = runtime.get('growcentral_esp32')
    async def enrich(row):
        if row['status'] != 'TRUSTED': return row
        try: row['online'] = (await provider.health(row['device_id'])).online
        except Exception: row['online'] = False
        return row
    if devices:
        devices = list(await asyncio.gather(*(enrich(row) for row in devices)))
    return {'devices': devices}
