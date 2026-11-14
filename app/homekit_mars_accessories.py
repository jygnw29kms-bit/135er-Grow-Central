"""HomeKit control surface for locally connected, owner-approved Mars devices."""
import asyncio
import json
import logging
import os
import time
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from pyhap.accessory import Accessory

log=logging.getLogger(__name__)
from pyhap.characteristic import Characteristic
_original_client_update=Characteristic.client_update_value
def _logged_client_update(self,value,sender_client_addr=None):
    # Incoming HAP client PUT, never triggered by local set_value telemetry.
    peer=sender_client_addr[0] if sender_client_addr else "unknown"
    log.warning("HomeKit inbound characteristic=%s value=%s peer=%s",
                self.display_name,value,peer)
    return _original_client_update(self,value,sender_client_addr)
Characteristic.client_update_value=_logged_client_update
ROOT=Path('/var/lib/135er-grow-central')
TOKEN=ROOT/'local-api-token'
API='http://127.0.0.1:8080/api/mars-hydro/ble/'
def snapshot(kind):
    try:
        data=json.loads((ROOT/f'mars-{kind}-live.json').read_text())
        dt=datetime.fromisoformat(data['timestamp'].replace('Z','+00:00'))
        data['fresh']=0 <= (datetime.now(timezone.utc)-dt).total_seconds() <= 30
        return data
    except (OSError,ValueError,TypeError,KeyError):
        return {'fresh':False}
def request(kind,action,value):
    route='fast-lamp-control' if kind=='lamp' else 'fast-fan-control'
    payload=json.dumps({'action':action,'value':value,'confirm_physical_change':True}).encode()
    req=Request(API+route,data=payload,headers={'Content-Type':'application/json','X-API-Token':TOKEN.read_text().strip()},method='POST')
    with urlopen(req,timeout=9) as response:
        result=json.load(response)
    if not result.get('device_report_confirmed'):
        raise RuntimeError('No controller status confirmation')
    return result['latest']
class MarsAccessory(Accessory):
    category=5
    kind='lamp'
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.on=None
        self.level=None
        self._job=asyncio.Lock()
        self._last_action_at=0
        self._last_action=None
        self._recent_actions=[]
        self._homekit_off_until=0.0
        self._lamp_off_epoch=0
        self._hap_reported_power=None
    def set_on(self,value):
        value=bool(value)
        log.info("HomeKit incoming %s power=%s",self.kind,value)
        if self.kind=='lamp' and not value:
            # Synchronously invalidate pending slider writes before they are run.
            self._lamp_off_epoch+=1
            self._homekit_off_until=time.monotonic()+15
        self.driver.add_job(self._write('power',int(value),self._lamp_off_epoch))
    def set_level(self,value):
        n=int(round(float(value)))
        log.info("HomeKit incoming %s level=%s",self.kind,n)
        if self.kind=='lamp' and (not snapshot('lamp').get('power_on',False)
                                  or time.monotonic()<self._homekit_off_until):
            # HAP already updated its in-memory characteristic; restore the
            # real controller status rather than echo a fictional new level.
            self.update(snapshot('lamp'))
            return
        if self.kind=='fan' and n==0:
            self.driver.add_job(self._write('power',0))
            return
        if self.kind=='fan':n=max(25,min(100,n))
        else:n=max(10,min(100,n))
        self.driver.add_job(self._write('speed' if self.kind=='fan' else 'brightness',
                                        n,self._lamp_off_epoch))
    def update(self,data):
        if not data.get('fresh'):return
        if isinstance(data.get('power_on'),bool):self.on.set_value(data['power_on'])
        value=data.get('brightness_percent' if self.kind=='lamp' else 'setpoint_percent')
        if value is not None:self.level.set_value(int(value))
    async def _write(self,action,value,epoch=None):
        async with self._job:
            # A pending slider update must never run after a later OFF event.
            if self.kind=='lamp' and action=='brightness' and (
                epoch != self._lamp_off_epoch or time.monotonic()<self._homekit_off_until):
                log.info("HomeKit lamp queued brightness discarded after OFF")
                self.update(snapshot('lamp'))
                return
            # Safety interlock: keep HomeKit telemetry published, but prevent
            # repeated actuator commands until owner enables writes explicitly.
            if os.getenv('GC_HOMEKIT_MARS_WRITES_ENABLED') != '1':
                log.warning('HomeKit Mars write blocked (safety): %s %s %s',self.kind,action,value)
                self.update(snapshot(self.kind))
                return
            now=time.monotonic()
            if self.kind=='lamp':
                if action=='brightness' and not snapshot('lamp').get('power_on',False):
                    log.info("HomeKit lamp brightness ignored while OFF")
                    return
                if action=='power' and value==1 and now<self._homekit_off_until:
                    log.warning("HomeKit lamp ON blocked for 30s after OFF")
                    self.update(snapshot('lamp'))
                    return
            # An accessory can be controlled from scenes/automations, too.
            # Prevent feedback loops from repeatedly toggling real equipment.
            self._recent_actions=[t for t in self._recent_actions if now-t<60]
            if not (action=='power' and value==0) and (
                len(self._recent_actions)>=3 or (self._last_action and
                self._last_action!=(action,value) and now-self._last_action_at<15)):
                log.error('HomeKit Mars command circuit breaker: %s',self.kind)
                self.update(snapshot(self.kind))
                return
            current=snapshot(self.kind)
            if current.get('fresh'):
                if action=='power' and current.get('power_on')==bool(value):
                    self.update(current)
                    return
                if action=='brightness' and current.get('brightness_percent')==value:
                    self.update(current)
                    return
                if action=='speed' and current.get('power_on') and current.get('setpoint_percent')==value:
                    self.update(current)
                    return
            self._recent_actions.append(now)
            if self.kind=='lamp' and action=='power' and value==0:
                self._homekit_off_until=now+30
            self._last_action=(action,value)
            self._last_action_at=now
            try:
                result=await asyncio.to_thread(request,self.kind,action,value)
                result['fresh']=True
                self.update(result)
            except Exception as exc:
                log.warning('HomeKit Mars %s write not confirmed: %s',self.kind,type(exc).__name__)
                self.update(snapshot(self.kind))
    async def run(self):
        while True:
            try:self.update(snapshot(self.kind))
            except Exception as exc:log.warning('HomeKit Mars telemetry: %s',type(exc).__name__)
            await asyncio.sleep(2)
class MarsLampAccessory(MarsAccessory):
    category=5
    kind='lamp'
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        status=snapshot('lamp')
        service=self.add_preload_service('Lightbulb',chars=['Brightness'])
        self.on=service.configure_char('On',value=bool(status.get('power_on',False)),
                                       setter_callback=self.set_on)
        self.level=service.configure_char('Brightness',
            value=int(status.get('brightness_percent',10)),
            setter_callback=self.set_level)

class MarsFanAccessory(MarsAccessory):
    category=3
    kind='fan'
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        status=snapshot('fan')
        service=self.add_preload_service('Fan',chars=['RotationSpeed'])
        self.on=service.configure_char('On',value=bool(status.get('power_on',False)),
                                       setter_callback=self.set_on)
        self.level=service.configure_char('RotationSpeed',
            value=float(status.get('power_on') and status.get('setpoint_percent',25) or 0),
            setter_callback=self.set_level)
    def update(self,data):
        if not data.get('fresh'):return
        if isinstance(data.get('power_on'),bool):self.on.set_value(data['power_on'])
        percent=data.get('setpoint_percent')
        if percent is not None:self.level.set_value(float(percent if data.get('power_on') else 0))
