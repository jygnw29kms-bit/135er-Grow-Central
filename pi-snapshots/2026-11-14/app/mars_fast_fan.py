import asyncio,time,os,logging,json
from pathlib import Path
from datetime import datetime,timezone
from bleak import BleakClient
from app.mars_hydro_ble import MZF002_NOTIFY,MZF002_WRITE
from app.mars_legacy_telemetry import mzf002_telemetry
log=logging.getLogger(__name__)
class FastFan:
 def __init__(self):
  self.client=None;self.last=None;self.at=0;self.seq=0
  self.event=asyncio.Event();self.lock=asyncio.Lock();self.task=None;self.saved_at=0
 def notify(self,_,raw):
  try:
   f=bytes(raw).decode('ascii').strip().split('|');v=mzf002_telemetry(bytes(raw))
   sid=os.getenv('GC_MZF002_ALLOWED_ID','').upper()
   if v and len(f)==23 and f[1].upper()==sid and f[2].upper()==sid and f[4]=='1.8' and len(f[5])==5 and f[5].isdigit():
    self.last=(f[5],v);self.at=time.monotonic();self.seq+=1;self.event.set()
    if self.at-self.saved_at>=2:
     self.saved_at=self.at
     # Only measured values and timestamp. Atomic replace for HomeKit reader.
     path=Path('/var/lib/135er-grow-central/mars-fan-live.json')
     tmp=path.with_suffix('.tmp')
     tmp.write_text(json.dumps({'timestamp':datetime.now(timezone.utc).isoformat(),
       'temperature_c':v['temperature_c'],'humidity_percent':v['humidity_rh'],
       'rpm':v['rpm'],'power_on':v['power_on'],
       'setpoint_percent':v['setpoint_percent']}))
     os.replace(tmp,path)
  except (ValueError,UnicodeError):pass
 async def run(self):
  while True:
   try:
    async with BleakClient('A0:A3:B3:5E:FD:CA',timeout=7) as c:
     await c.start_notify(MZF002_NOTIFY,self.notify);self.client=c
     log.info('MZF002 BLE ready')
     while c.is_connected:await asyncio.sleep(.5)
   except asyncio.CancelledError:raise
   except Exception as exc:log.warning('MZF002 reconnect %s',type(exc).__name__)
   finally:self.client=None;self.last=None;self.at=0
   await asyncio.sleep(4)
 async def control(self,action,value):
  async with self.lock:
   if not self.client or not self.client.is_connected or not self.last or time.monotonic()-self.at>8:return None
   code,old=self.last
   if action=='speed':
    if not 25<=value<=100 or not old['power_on']:raise ValueError('Speed unavailable')
    if old['setpoint_percent']==value:return dict(command_sent=False,device_report_confirmed=True,latest=old)
   elif action=='power':
    if value not in (0,1):raise ValueError('Invalid power')
    if old['power_on']==bool(value):return dict(command_sent=False,device_report_confirmed=True,latest=old)
   else:raise ValueError('Invalid action')
   kind=1 if action=='power' else 2
   serial=os.getenv('GC_MZF002_ALLOWED_ID','').upper()
   before=self.seq;start=time.monotonic()
   await asyncio.wait_for(self.client.write_gatt_char(MZF002_WRITE,f'{kind}|0|{code}|{serial}|{value}'.encode(),response=True),timeout=3)
   for _ in range(32):
    if self.seq>before and self.last:
     v=self.last[1]
     if (action=='power' and v['power_on']==bool(value)) or (action=='speed' and v['setpoint_percent']==value):
      return dict(command_sent=True,device_report_confirmed=True,latest=v,elapsed_ms=round((time.monotonic()-start)*1000))
    self.event.clear()
    try:await asyncio.wait_for(self.event.wait(),timeout=.125)
    except asyncio.TimeoutError:pass
   return dict(command_sent=True,device_report_confirmed=False,latest=self.last[1] if self.last else old,retry_attempted=False)
fast_fan=FastFan()
