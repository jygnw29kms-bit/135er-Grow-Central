"""Durable local time-series archive for Grow Central.

SQLite WAL; no raw BLE frames or private device/session identifiers are stored.
Samples remain available across restarts. A point records measurement origin and
source kind (measured, reported setpoint, calculated display estimate).
"""
from __future__ import annotations

import csv
import io
import math
import os
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from app.security import require_write_auth

DATA_FILE = Path(os.getenv("GC_HISTORY_DB", "/var/lib/135er-grow-central/history.sqlite3"))
router = APIRouter(prefix="/api/v1/history", tags=["permanent history"], dependencies=[Depends(require_write_auth)])
UNITS = {
    "temperature_c": ("°C","measured"),
    "humidity_percent": ("% rF","measured"),
    "soil_moisture_percent": ("%","measured"),
    "soil_temperature_c": ("°C","measured"),
    "co2_ppm": ("ppm","measured"),
    "ppfd_umol_m2_s": ("µmol/m²/s","measured"),
    "ec_ms_cm": ("mS/cm","measured"),
    "ph": ("pH","measured"),
    "vpd_kpa": ("kPa","calculated"),
    "power_w": ("W","measured"),
    "energy_wh": ("Wh","measured"),
    "fan_rpm": ("RPM","measured"),
    "fan_setpoint_percent": ("%","reported_setpoint"),
    "fan_power_on": ("bool","reported_state"),
    "lamp_brightness_percent": ("%","reported_setpoint"),
    "lamp_power_on": ("bool","reported_state"),
    "airflow_cfm": ("CFM","estimated_show_only"),
    "pressure_pa": ("Pa","estimated_show_only"),
}
def connect():
    DATA_FILE.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(DATA_FILE,timeout=10)
    db.row_factory=sqlite3.Row
    db.execute("PRAGMA busy_timeout=10000")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("""CREATE TABLE IF NOT EXISTS points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recorded_at TEXT NOT NULL,
        room_id TEXT,
        grow_id TEXT,
        plant_id TEXT,
        device TEXT NOT NULL,
        metric TEXT NOT NULL,
        value REAL NOT NULL,
        unit TEXT NOT NULL,
        source_kind TEXT NOT NULL
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_points_lookup ON points(metric,recorded_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_points_grow ON points(grow_id,recorded_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_points_room ON points(room_id,recorded_at)")
    return db

def append(device: str, values: dict[str,Any], *, room_id: str|None=None,
           grow_id: str|None=None, plant_id: str|None=None, source: str="") -> int:
    if not isinstance(device,str) or len(device)>96 or not device:return 0
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    batch=[]
    for metric,value in values.items():
        if metric not in UNITS or value is None:continue
        if type(value) is bool: value=int(value)
        if type(value) not in (int,float) or not math.isfinite(value):continue
        unit,kind=UNITS[metric]
        # Display-only fan model must never masquerade as a sensor.
        if metric in ("airflow_cfm","pressure_pa") and source!="estimated_from_setpoint_show_only":continue
        batch.append((now,room_id,grow_id,plant_id,device,metric,float(value),unit,kind))
    if not batch:return 0
    with closing(connect()) as db,db:
        db.executemany("""INSERT INTO points
          (recorded_at,room_id,grow_id,plant_id,device,metric,value,unit,source_kind)
          VALUES (?,?,?,?,?,?,?,?,?)""",batch)
    return len(batch)

def rows(*,metric: str|None=None, room_id: str|None=None,grow_id: str|None=None,
         start: str|None=None, end: str|None=None,limit: int=500) -> list[dict]:
    where=[];args=[]
    for column,val in (("metric",metric),("room_id",room_id),("grow_id",grow_id),
                       ("recorded_at",None)):
        if val is not None:
            where.append(column+" = ?");args.append(val)
    if start:where.append("recorded_at >= ?");args.append(start)
    if end:where.append("recorded_at <= ?");args.append(end)
    sql="SELECT recorded_at,room_id,grow_id,plant_id,device,metric,value,unit,source_kind FROM points"
    if where:sql+=" WHERE "+" AND ".join(where)
    sql+=" ORDER BY recorded_at DESC,id DESC LIMIT ?";args.append(limit)
    with closing(connect()) as db:
        return [dict(v) for v in db.execute(sql,args)]

@router.get("/points")
def get_points(metric: str|None=None,room_id: str|None=None,grow_id: str|None=None,
               start: str|None=None,end: str|None=None,
               limit: int=Query(default=500,ge=1,le=10000)):
    if metric and metric not in UNITS:raise HTTPException(422,"Unbekannte Messgröße")
    return {"points":list(reversed(rows(metric=metric,room_id=room_id,grow_id=grow_id,
                                        start=start,end=end,limit=limit)))}

@router.get("/summary")
def get_summary(room_id: str|None=None,grow_id: str|None=None,
                start: str|None=None,end: str|None=None):
    data=rows(room_id=room_id,grow_id=grow_id,start=start,end=end,limit=10000)
    result={}
    for name in UNITS:
        vals=[p["value"] for p in data if p["metric"]==name]
        if vals:
            result[name]={"count":len(vals),"min":min(vals),"max":max(vals),
                          "mean":round(sum(vals)/len(vals),3),"unit":UNITS[name][0],
                          "source_kind":UNITS[name][1]}
    return {"samples_evaluated":len(data),"truncated":len(data)==10000,"metrics":result}

@router.get("/export.csv")
def export_csv(room_id: str|None=None,grow_id: str|None=None,metric: str|None=None,
               start: str|None=None,end: str|None=None):
    if metric and metric not in UNITS:raise HTTPException(422,"Unbekannte Messgröße")
    values=list(reversed(rows(room_id=room_id,grow_id=grow_id,metric=metric,
                              start=start,end=end,limit=50000)))
    result=io.StringIO(newline="")
    cols=["recorded_at","room_id","grow_id","plant_id","device","metric","value","unit","source_kind"]
    writer=csv.DictWriter(result,fieldnames=cols,delimiter=";")
    writer.writeheader();writer.writerows(values)
    return Response(result.getvalue(),media_type="text/csv",headers={
        "Content-Disposition":'attachment; filename="grow-central-history.csv"',
        "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"})

@router.get("/status")
def status():
    with closing(connect()) as db:
        count=db.execute("SELECT count(*) FROM points").fetchone()[0]
        first=db.execute("SELECT min(recorded_at) FROM points").fetchone()[0]
        last=db.execute("SELECT max(recorded_at) FROM points").fetchone()[0]
    return {"ok":True,"total_points":count,"first":first,"last":last,
            "database":"local_sqlite_wal","persistent":True}
