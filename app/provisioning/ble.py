"""Secure local BLE bootstrap for autonomous Grow-Central sensor nodes.

BLE is discovery/credential transport only. A sensor becomes TRUSTED only after
an explicit operator action, physical BOOT-button confirmation, encrypted
provisioning and a fresh signed MQTT proof using the same long-term key.
"""
from __future__ import annotations

import asyncio, base64, json, re, secrets, time
from dataclasses import dataclass
from typing import Any

from bleak import BleakClient, BleakScanner
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, SecretStr, field_validator

from app.audit import append_audit
from app.security import require_write_auth
from app.devices.gc_identity import verify_message
from app.devices.gc_esp32_protocol import parse_announcement
from app.devices.gc_trust import TrustStore
from app.devices.gc_calibration import CalibrationStore
from .broker import request_broker

SERVICE_UUID='7b0d0001-6f2a-4c2d-9d8a-135e2c000001'
CONTROL_UUID='7b0d0002-6f2a-4c2d-9d8a-135e2c000001'
STATUS_UUID='7b0d0003-6f2a-4c2d-9d8a-135e2c000001'
PROTOCOL='gc-ble-provision-v1'
PAIR_TIMEOUT=60.0
MAX_FRAME=8192
CHUNK=140
ID_RE=re.compile(r'^gc-soil-[0-9a-f]{6}$')

@dataclass
class Candidate:
    address:str; device_id:str; name:str; rssi:int|None; last_seen:float

_candidates:dict[str,Candidate]={}
router=APIRouter(prefix='/api/devices/ble',tags=['BLE sensor setup'],dependencies=[Depends(require_write_auth)])


def _candidate_id(name:str)->str|None:
    value=name.strip().lower()
    if value.startswith('gc-soil-') and ID_RE.fullmatch(value): return value
    if value.startswith('gcsoil-'):
        value='gc-soil-'+value[7:]
        if ID_RE.fullmatch(value): return value
    return None

async def scan(timeout:float=3.0)->list[dict[str,Any]]:
    found=await BleakScanner.discover(timeout=max(.5,min(timeout,8.0)),return_adv=True)
    now=time.monotonic()
    for address,(dev,adv) in found.items():
        uuids={str(u).lower() for u in (adv.service_uuids or [])}
        if SERVICE_UUID not in uuids: continue
        name=(adv.local_name or dev.name or '').strip()
        device_id=_candidate_id(name)
        if not device_id: continue
        _candidates[device_id]=Candidate(address,device_id,name,adv.rssi,now)
    for key,row in list(_candidates.items()):
        if now-row.last_seen>120: _candidates.pop(key,None)
    return [vars(x) for x in sorted(_candidates.values(),key=lambda x:-(x.rssi or -999))]

class ProvisionRequest(BaseModel):
    ssid:str=Field(min_length=1,max_length=32)
    password:SecretStr
    broker_host:str=Field(min_length=1,max_length=253)
    name:str=Field(min_length=1,max_length=120)
    room_id:str=Field(min_length=1,max_length=80)
    @field_validator('ssid','broker_host','name')
    @classmethod
    def safe(cls,v):
        if any(ord(c)<32 for c in v): raise ValueError('Ungültige Steuerzeichen.')
        return v.strip()
    @field_validator('broker_host')
    @classmethod
    def broker_target(cls,v):
        if v.lower().endswith('.local') or '|' in v:
            raise ValueError('Für Sensoren die LAN-IP des Pi als Broker verwenden.')
        return v
    @field_validator('password')
    @classmethod
    def password_rules(cls,v):
        raw=v.get_secret_value().encode()
        if raw and not 8<=len(raw)<=63: raise ValueError('WLAN-Kennwort benötigt 8–63 Bytes.')
        return v

class _Channel:
    def __init__(self): self.queue=asyncio.Queue(maxsize=128);self.fragments={}
    def notify(self,_sender,data):
        raw=bytes(data)
        if len(raw)>512:return
        try:self.queue.put_nowait(raw.decode())
        except (UnicodeDecodeError,asyncio.QueueFull):pass
    async def next(self,prefix:str,timeout:float):
        end=time.monotonic()+timeout
        while True:
            left=end-time.monotonic()
            if left<=0:raise TimeoutError(prefix)
            value=await asyncio.wait_for(self.queue.get(),left)
            if value.startswith(prefix):return value

async def _write_chunks(client:BleakClient,payload:str):
    parts=[payload[i:i+CHUNK] for i in range(0,len(payload),CHUNK)]
    if len(parts)>64: raise ValueError('BLE provisioning payload too large')
    for i,part in enumerate(parts):
        await client.write_gatt_char(CONTROL_UUID,f'C|{i}|{len(parts)}|{part}'.encode(),response=True)

async def _read_proof(channel:_Channel,timeout:float):
    pieces={};total=None;end=time.monotonic()+timeout
    while time.monotonic()<end:
        raw=await channel.next('P|',end-time.monotonic())
        try:_,idx,count,chunk=raw.split('|',3);idx=int(idx);count=int(count)
        except ValueError:continue
        if not 0<=idx<count<=64:continue
        total=count;pieces[idx]=chunk
        if len(pieces)==total:
            payload=''.join(pieces[i] for i in range(total))
            if len(payload)>MAX_FRAME:raise ValueError('BLE proof too large')
            return payload
    raise TimeoutError('BLE identity proof timed out')

async def inspect_candidate(device_id:str,timeout:float=10.0):
    candidate=_candidates.get(device_id)
    if not candidate: raise KeyError(device_id)
    nonce=secrets.token_hex(32)
    private=ec.generate_private_key(ec.SECP256R1())
    public=private.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
    channel=_Channel()
    async with BleakClient(candidate.address) as client:
        await client.start_notify(STATUS_UUID,channel.notify)
        hello='H|'+nonce+'|'+base64.b64encode(public).decode()
        await client.write_gatt_char(CONTROL_UUID,hello.encode(),response=True)
        envelope=await _read_proof(channel,timeout)
        proof=verify_message(envelope,kind='ble_proof',device_id=device_id)
        if proof.body.get('nonce')!=nonce or proof.body.get('protocol')!=PROTOCOL: raise PermissionError('BLE challenge mismatch')
        announcement=parse_announcement(json.dumps(proof.body.get('announcement')))
        if announcement.id!=device_id: raise PermissionError('BLE identity mismatch')
        peer_raw=base64.b64decode(proof.body.get('ephemeral',''),validate=True)
        peer=ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),peer_raw)
        shared=private.exchange(ec.ECDH(),peer)
        key=HKDF(algorithm=hashes.SHA256(),length=32,salt=bytes.fromhex(nonce),info=PROTOCOL.encode()).derive(shared)
        row=await asyncio.to_thread(TrustStore().discover,announcement,proof)
        return row,key,nonce,channel,client

@router.post('/scan')
async def scan_api(timeout:float=3.0): return {'devices':await scan(timeout),'ble_available':True}

@router.get('')
async def candidates(): return {'devices':[vars(x) for x in _candidates.values()],'ble_available':True}

@router.post('/{device_id}/inspect')
async def inspect_api(device_id:str):
    try:
        row,_,_,_,_=await inspect_candidate(device_id)
        return {'ok':True,'device':row,'physical_confirmation':'required_for_credentials'}
    except KeyError as exc: raise HTTPException(404,'BLE-Sensor nicht gefunden; erneut suchen.') from exc
    except (ValueError,PermissionError,TimeoutError) as exc: raise HTTPException(409,'BLE-Identität konnte nicht sicher bestätigt werden.') from exc


@router.get('/broker')
async def broker_options():
    try:
        result=await asyncio.to_thread(request_broker,'info')
        return {'ready':True,'hosts':result['hosts']}
    except (OSError,RuntimeError):
        return {'ready':False,'hosts':[],'message':'Lokaler Broker-Einrichtungsdienst nicht verfügbar.'}


def install_observer(app):
    if getattr(app.state,'gc_ble_observer_installed',False): return
    app.state.gc_ble_observer_installed=True
    import contextlib
    async def observe():
        while True:
            try:
                rows=await scan(3.0)
                for candidate in rows:
                    device_id=candidate['device_id']
                    current=await asyncio.to_thread(TrustStore().get,device_id)
                    if current and current['status'] in {'TRUSTED','REJECTED','REVOKED'}: continue
                    if current and current['identity_verified']: continue
                    try: await inspect_candidate(device_id,8.0)
                    except (KeyError,ValueError,PermissionError,TimeoutError,OSError): pass
            except Exception: pass
            await asyncio.sleep(12)
    async def start(): app.state.gc_ble_observer=asyncio.create_task(observe())
    async def stop():
        task=getattr(app.state,'gc_ble_observer',None)
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError): await task
    app.router.add_event_handler('startup',start);app.router.add_event_handler('shutdown',stop)

@router.post('/{device_id}/provision')
async def provision(device_id:str,body:ProvisionRequest):
    from app import rooms
    candidate=_candidates.get(device_id)
    if not candidate: raise HTTPException(404,'BLE-Sensor nicht gefunden; erneut suchen.')
    existing=await asyncio.to_thread(TrustStore().get,device_id)
    if not existing or existing['status']!='DISCOVERED': raise HTTPException(409,'Sensor muss auf „Neu – Entscheidung offen“ stehen.')
    rooms.room_or_404(rooms.load_state(),body.room_id)
    metadata=existing.get('metadata') or {}
    if 'soil_moisture' in metadata.get('capabilities',[]):
        calibration=await asyncio.to_thread(CalibrationStore().get,device_id)
        if not calibration or not calibration.get('valid') or calibration.get('fingerprint')!=existing.get('fingerprint'):
            raise HTTPException(409,'Neue Bodenfeuchtesensoren zuerst vollständig per USB prüfen und kalibrieren; BLE ist nur Recovery.')
    nonce=secrets.token_hex(32);private=ec.generate_private_key(ec.SECP256R1())
    public=private.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
    channel=_Channel()
    try:
        async with BleakClient(candidate.address) as client:
            await client.start_notify(STATUS_UUID,channel.notify)
            await client.write_gatt_char(CONTROL_UUID,('H|'+nonce+'|'+base64.b64encode(public).decode()).encode(),response=True)
            envelope=await _read_proof(channel,12)
            proof=verify_message(envelope,kind='ble_proof',device_id=device_id)
            announcement=parse_announcement(json.dumps(proof.body.get('announcement')))
            if announcement.id!=device_id or proof.body.get('protocol')!=PROTOCOL:
                raise PermissionError('BLE protocol or announcement mismatch')
            if proof.public_key!=existing['public_key'] or proof.body.get('nonce')!=nonce: raise PermissionError('sensor key changed')
            peer=ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),base64.b64decode(proof.body['ephemeral'],validate=True))
            shared=private.exchange(ec.ECDH(),peer)
            key=HKDF(algorithm=hashes.SHA256(),length=32,salt=bytes.fromhex(nonce),info=PROTOCOL.encode()).derive(shared)
            # The connected physical XIAO must confirm locally before any secret is created/transferred.
            await client.write_gatt_char(CONTROL_UUID,('A|'+nonce).encode(),response=True)
            ready=await channel.next('R|',PAIR_TIMEOUT)
            if ready!='R|'+nonce: raise PermissionError('physical confirmation mismatch')
            credentials=await asyncio.to_thread(request_broker,'provision',device_id=device_id,host=body.broker_host)
            def b64(value:str)->str: return base64.b64encode(value.encode()).decode()
            # Compact delimiter-safe plaintext; secrets are inside AES-GCM and never logged.
            plain=('V1|'+b64(body.ssid)+'|'+b64(body.password.get_secret_value())+'|'+b64(credentials['host'])+'|'+
                   str(credentials['port'])+'|'+b64(credentials['username'])+'|'+b64(credentials['password'])+'|'+
                   credentials['ca']+'|'+b64(body.name)).encode()
            iv=secrets.token_bytes(12);aad=device_id.encode()
            encrypted=iv+AESGCM(key).encrypt(iv,plain,aad)
            await _write_chunks(client,base64.b64encode(encrypted).decode())
            done=await channel.next('D|',15)
            if done!='D|'+nonce: raise RuntimeError('sensor did not commit BLE config')
        from app.devices.runtime import runtime
        network_proof=await runtime.get('growcentral_esp32').prove_identity(device_id)
        if network_proof.public_key!=existing['public_key']: raise PermissionError('network identity changed')
        if 'soil_moisture' in metadata.get('capabilities',[]):
            state=network_proof.body.get('state') or {}; meta=state.get('meta') if isinstance(state,dict) else {}
            firmware=meta.get('firmware') if isinstance(meta,dict) else metadata.get('firmware')
            await asyncio.to_thread(CalibrationStore().require_valid,device_id,fingerprint=existing.get('fingerprint'),public_key=network_proof.public_key,hardware_uid=network_proof.body.get('hardware_uid'),firmware_version=firmware)
            if not (network_proof.body.get('calibration') or {}).get('ready'):
                raise PermissionError('sensor calibration no longer valid')
        def assign():
            with rooms.edit_state() as state:
                rooms.room_or_404(state,body.room_id)
                state['assignments']['growcentral_esp32:'+device_id]=body.room_id
        row=await asyncio.to_thread(TrustStore().accept,device_id,name=body.name,room_id=body.room_id,
                                    fingerprint=existing['fingerprint'][-16:],proved_key=network_proof.public_key,assign=assign)
        append_audit('ble.sensor.accepted',device_id=device_id,room_id=body.room_id)
        return {'ok':True,'device':row}
    except TimeoutError as exc: raise HTTPException(408,'Pairing abgebrochen: BOOT-Taster am Sensor nicht rechtzeitig bestätigt oder Verbindung verloren.') from exc
    except PermissionError as exc: raise HTTPException(403,'Sensoridentität hat sich geändert oder die physische Bestätigung war ungültig.') from exc
    except (ValueError,RuntimeError,OSError) as exc: raise HTTPException(409,'Sichere BLE-Einrichtung fehlgeschlagen; Sensor bleibt nicht vertrauenswürdig.') from exc
