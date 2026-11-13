#!/usr/bin/env python3
"""One-shot periodic Mars Hydro BLE history collector (read only).

Invoked by a systemd timer. Never writes BLE commands, never toggles devices.
If an app holds a BLE connection, skip that device and resume next interval.
"""
from __future__ import annotations
import asyncio
import os
import sys
from bleak import BleakScanner, BleakClient

from app.history_archive import append
from app.mars_legacy_telemetry import mzf002_telemetry, fc3000_telemetry
from app.mars_hydro_ble import MZF002_NOTIFY

FAN_ID="MZ_MZF002_68756_A0A3B35EFDC8"
LAMP_ID="MZ_MARS_68756_FCB467AEC260"

async def observe(device, kind):
    parser=mzf002_telemetry if kind=="fan" else fc3000_telemetry
    received=[]
    try:
        async with BleakClient(device,timeout=10) as client:
            def notify(_,data):
                result=parser(bytes(data))
                if result:received.append(result)
            await asyncio.wait_for(client.start_notify(MZF002_NOTIFY,notify),timeout=6)
            await asyncio.sleep(4)
            if client.is_connected:
                await asyncio.wait_for(client.stop_notify(MZF002_NOTIFY),timeout=3)
    except Exception as exc:
        print(kind+"_unavailable",type(exc).__name__,flush=True)
        return 0
    if not received:
        print(kind+"_no_status",flush=True)
        return 0
    v=received[-1]
    if kind=="fan":
        values={"temperature_c":v["temperature_c"],"humidity_percent":v["humidity_rh"],
                "fan_rpm":v["rpm"],"fan_setpoint_percent":v["setpoint_percent"],
                "fan_power_on":v["power_on"],"airflow_cfm":v["airflow_cfm"],
                "pressure_pa":v["pressure_pa"]}
        label="mars-hydro-mzf002"
        source=v.get("airflow_pressure_source","")
    else:
        values={"lamp_brightness_percent":v["brightness_percent"],"lamp_power_on":v["power_on"]}
        label="mars-hydro-fc3000"
        source=""
    count=append(label,values,source=source)
    print(kind+"_saved",count,flush=True)
    return count

async def run():
    found=await BleakScanner.discover(timeout=7)
    devices={x.name:x for x in found if x.name in (FAN_ID,LAMP_ID)}
    total=0
    for name,kind in ((FAN_ID,"fan"),(LAMP_ID,"lamp")):
        if name in devices:total+=await observe(devices[name],kind)
        else:print(kind+"_not_advertising",flush=True)
    print("saved_points",total,flush=True)

if __name__=="__main__":
    try:asyncio.run(run())
    except Exception as exc:
        print("collector_error",type(exc).__name__,flush=True)
        sys.exit(1)
