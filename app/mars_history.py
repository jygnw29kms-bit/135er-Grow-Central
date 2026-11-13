"""Persistent Mars Hydro measurements for grow-to-grow comparisons.

Five-minute passive BLE samples, SQLite WAL, append-only measurements.
No vendor writes, no guessed sensor readings, no silent data deletion.
"""
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sqlite3
from typing import Any

from bleak import BleakClient, BleakScanner
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.security import require_write_auth
from app.mars_hydro_ble import _capture_lock, MZF002_NOTIFY
from app.mars_legacy_telemetry import fc3000_telemetry, mzf002_telemetry

DB = Path(os.getenv("GC_MARS_HISTORY_DB", "/var/lib/135er-grow-central/mars-history.sqlite3"))
INTERVAL = max(120, int(os.getenv("GC_MARS_HISTORY_SECONDS", "300")))
router = APIRouter(prefix="/api/mars-history", tags=["Mars Hydro Messarchiv"],
                   dependencies=[Depends(require_write_auth)])
_task: asyncio.Task | None = None
FAN = "MZ_MZF002_68756_A0A3B35EFDC8"
LAMP = "MZ_MARS_68756_FCB467AEC260"

def connect() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=8)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=8000")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS samples(
        id INTEGER PRIMARY KEY, recorded_at TEXT NOT NULL, device TEXT NOT NULL,
        temperature_c REAL, humidity_rh REAL, rpm INTEGER, setpoint_percent INTEGER,
        power_on INTEGER, brightness_percent INTEGER, airflow_cfm REAL, pressure_pa REAL,
        airflow_pressure_source TEXT NOT NULL DEFAULT '', origin TEXT NOT NULL DEFAULT 'ble'
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS ix_mars_device_time ON samples(device,recorded_at)")
    db.execute("""CREATE TABLE IF NOT EXISTS grows(
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, crop TEXT NOT NULL DEFAULT '',
        started_at TEXT NOT NULL, ended_at TEXT, notes TEXT NOT NULL DEFAULT ''
    )""")
    db.commit()
    return db

def save(device: str, row: dict[str,Any]) -> None:
    if device not in ("fan","lamp"):return
    now=datetime.now(timezone.utc).isoformat()
    with connect() as db:
        db.execute("""INSERT INTO samples(recorded_at,device,temperature_c,humidity_rh,rpm,
                     setpoint_percent,power_on,brightness_percent,airflow_cfm,pressure_pa,
                     airflow_pressure_source) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                   (now,device,row.get("temperature_c"),row.get("humidity_rh"),
                    row.get("rpm"),row.get("setpoint_percent"),
                    int(row["power_on"]) if "power_on" in row else None,
                    row.get("brightness_percent"),row.get("airflow_cfm"),
                    row.get("pressure_pa"),row.get("airflow_pressure_source","")))
        db.commit()

async def sample_once() -> dict[str,bool]:
    result={"fan":False,"lamp":False}
    if _capture_lock.locked():return result
    async with _capture_lock:
        devices=await BleakScanner.discover(timeout=7)
        found={d.name:d for d in devices if d.name in (FAN,LAMP)}
        for name,role,parser in ((FAN,"fan",mzf002_telemetry),(LAMP,"lamp",fc3000_telemetry)):
            if name not in found:continue
            updates=[]
            try:
                async with BleakClient(found[name],timeout=12) as client:
                    def notify(_sender,data):
                        row=parser(bytes(data))
                        if row is not None:updates.append(row)
                    await asyncio.wait_for(client.start_notify(MZF002_NOTIFY,notify),timeout=6)
                    await asyncio.sleep(4)
                    await asyncio.wait_for(client.stop_notify(MZF002_NOTIFY),timeout=5)
                if updates:
                    await asyncio.to_thread(save,role,updates[-1])
                    result[role]=True
            except (Exception, asyncio.CancelledError) as exc:
                if isinstance(exc,asyncio.CancelledError):raise
                # Bluetooth may be held by the owner app; skip this cycle, never invent data.
                continue
    return result

async def sampler() -> None:
    # Startup delay avoids colliding with boot-time BLE enrollment and device discovery.
    await asyncio.sleep(25)
    while True:
        try:await asyncio.wait_for(sample_once(),timeout=80)
        except asyncio.CancelledError:raise
        except Exception:pass
        await asyncio.sleep(INTERVAL)

def install(app) -> None:
    @app.on_event("startup")
    async def start() -> None:
        global _task
        await asyncio.to_thread(connect_and_close)
        if _task is None or _task.done():
            _task=asyncio.create_task(sampler(),name="gc-mars-persistent-history")
    @app.on_event("shutdown")
    async def stop() -> None:
        global _task
        if _task:
            _task.cancel()
            try:await _task
            except asyncio.CancelledError:pass
            _task=None

def connect_and_close() -> None:
    db=connect()
    db.close()

def rows(sql: str, params: tuple=()) -> list[dict[str,Any]]:
    with connect() as db:return [dict(r) for r in db.execute(sql,params).fetchall()]

@router.get("/summary")
def summary():
    latest=rows("""SELECT s.* FROM samples s
                   WHERE s.id=(SELECT MAX(id) FROM samples q WHERE q.device=s.device)
                   ORDER BY device""")
    totals=rows("SELECT device,COUNT(*) AS samples,MIN(recorded_at) AS first_at,MAX(recorded_at) AS last_at FROM samples GROUP BY device")
    return {"latest":latest,"totals":totals,"interval_seconds":INTERVAL,
            "storage":"sqlite_persistent","estimated_values_are_not_sensors":True}

@router.get("/series")
def series(device: str = Query("fan",pattern="^(fan|lamp)$"),
           days: int = Query(7,ge=1,le=3660),limit:int=Query(1200,ge=1,le=10000)):
    cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
    values=rows("""SELECT * FROM (SELECT * FROM samples WHERE device=? AND recorded_at>=?
                   ORDER BY recorded_at DESC LIMIT ?) ORDER BY recorded_at""",(device,cutoff,limit))
    return {"device":device,"samples":values,"limit":limit,"days":days}

class GrowCreate(BaseModel):
    name: str=Field(min_length=1,max_length=90)
    crop: str=Field(default="",max_length=90)
    started_at: datetime
    ended_at: datetime | None = None
    notes: str=Field(default="",max_length=500)

@router.get("/grows")
def grows():
    return {"grows":rows("SELECT * FROM grows ORDER BY started_at DESC")}

@router.post("/grows")
def new_grow(body: GrowCreate):
    start=body.started_at.astimezone(timezone.utc).isoformat()
    end=body.ended_at.astimezone(timezone.utc).isoformat() if body.ended_at else None
    if end and end<=start:raise HTTPException(422,"Ende muss nach Start liegen.")
    with connect() as db:
        cur=db.execute("INSERT INTO grows(name,crop,started_at,ended_at,notes) VALUES (?,?,?,?,?)",
                       (body.name,body.crop,start,end,body.notes))
        db.commit()
        return {"id":cur.lastrowid,"name":body.name}

@router.get("/compare")
def compare(a:int=Query(ge=1),b:int=Query(ge=1)):
    selected=rows("SELECT * FROM grows WHERE id IN (?,?)",(a,b))
    if len(selected)!=2:raise HTTPException(404,"Grow-Durchläufe nicht gefunden.")
    result=[]
    for grow in selected:
        start=grow["started_at"]
        end=grow["ended_at"] or datetime.now(timezone.utc).isoformat()
        metrics=rows("""SELECT device,COUNT(*) count,
            ROUND(AVG(temperature_c),2) avg_temp_c,
            ROUND(MIN(temperature_c),2) min_temp_c,ROUND(MAX(temperature_c),2) max_temp_c,
            ROUND(AVG(humidity_rh),2) avg_humidity_rh,
            ROUND(AVG(rpm),0) avg_rpm,ROUND(AVG(setpoint_percent),2) avg_fan_percent,
            ROUND(AVG(brightness_percent),2) avg_light_percent
            FROM samples WHERE recorded_at>=? AND recorded_at<=?
            GROUP BY device""",(start,end))
        result.append({"grow":grow,"metrics":metrics})
    return {"comparisons":result,"note":"Vergleich der verfügbaren BLE-Messwerte; Wasser/Ertrag aus Raum- und Pflanzentagebuch separat."}
