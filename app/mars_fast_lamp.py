"""Persistent, readback-verified local FC3000 BLE session."""
import asyncio
import logging
import os
import time
import json
from pathlib import Path
from datetime import datetime,timezone
from bleak import BleakClient, BleakScanner
from app.mars_fc3000_trial import context_from_live_status, encode_command
from app.mars_hydro_ble import MZF002_NOTIFY, MZF002_WRITE, MZF002_SERVICE
from app.mars_ble_connect_gate import CONNECT_GATE, reconnect_delay

log=logging.getLogger(__name__)
NAME="MZ_MARS_68756_FCB467AEC260"
class FastLamp:
    def __init__(self):
        self.client=None
        self.latest=None
        self.at=0
        self.seq=0
        self.changed=asyncio.Event()
        self.lock=asyncio.Lock()
        self.task=None
        self.saved_at=0
    def notify(self, sender, data):
        parsed=context_from_live_status(bytes(data))
        if parsed:
            self.latest=parsed
            self.at=time.monotonic()
            self.seq+=1
            self.changed.set()
            if self.at-self.saved_at>=2:
                self.saved_at=self.at
                # Share only controller-reported state with the paired HomeKit process.
                status=parsed[1]
                target=Path('/var/lib/135er-grow-central/mars-lamp-live.json')
                tmp=target.with_suffix('.tmp')
                tmp.write_text(json.dumps({'timestamp':datetime.now(timezone.utc).isoformat(),
                    'power_on':status['power_on'],
                    'brightness_percent':status['brightness_percent']}))
                os.replace(tmp,target)
    async def runner(self):
        failures=0
        while True:
            client=None
            try:
                target=os.getenv("GC_FC3000_BLE_ADDRESS","FC:B4:67:AE:C2:62")
                # Avoid overlapping BlueZ connection attempts to the fan.
                async with CONNECT_GATE:
                    client=BleakClient(target,timeout=10)
                    try:
                        await client.connect()
                        uuids={str(s.uuid).lower() for s in client.services}
                        if MZF002_SERVICE not in uuids:
                            raise ValueError("Unexpected service")
                        await client.start_notify(MZF002_NOTIFY,self.notify)
                    except BaseException:
                        if client.is_connected:
                            await client.disconnect()
                        raise
                self.client=client
                failures=0
                log.info("FC3000 fast BLE connected")
                while client.is_connected:
                    await asyncio.sleep(.5)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                failures+=1
                log.warning("FC3000 fast BLE reconnect %s: %s",type(exc).__name__,str(exc)[:140])
            finally:
                self.client=None
                self.latest=None
                self.at=0
                if client is not None and client.is_connected:
                    try:await asyncio.wait_for(client.disconnect(),timeout=5)
                    except Exception as exc:
                        log.warning("FC3000 BLE disconnect %s",type(exc).__name__)
            await asyncio.sleep(reconnect_delay(max(1,failures),base=3.0,cap=45.0))
    async def control(self,action,value,allowed):
        async with self.lock:
            client=self.client
            if not client or not client.is_connected or not self.latest:return None
            if time.monotonic()-self.at>8:return None
            code,previous=self.latest
            packet=encode_command(code=code,device_id=allowed,action=action,value=value)
            before=self.seq
            start=time.monotonic()
            await asyncio.wait_for(client.write_gatt_char(MZF002_WRITE,packet,response=True),timeout=3)
            for _ in range(32):
                if self.seq>before and self.latest:
                    state=self.latest[1]
                    if ((action=="power" and state["power_on"]==bool(value)) or
                        (action=="brightness" and state["brightness_percent"]==value)):
                        return {"command_sent":True,"device_report_confirmed":True,
                                "latest":state,"path":"persistent_ble",
                                "elapsed_ms":round((time.monotonic()-start)*1000)}
                self.changed.clear()
                try:await asyncio.wait_for(self.changed.wait(),timeout=.125)
                except asyncio.TimeoutError:pass
            return {"command_sent":True,"device_report_confirmed":False,
                    "latest":self.latest[1] if self.latest else previous,
                    "path":"persistent_ble","retry_attempted":False}
fast_lamp=FastLamp()
