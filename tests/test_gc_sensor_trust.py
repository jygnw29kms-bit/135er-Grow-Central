import asyncio
import base64
import json
from types import SimpleNamespace
from pathlib import Path
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.devices.gc_identity import verify_message
from app.devices.gc_trust import TrustStore
from app.devices.gc_esp32_protocol import parse_announcement, device_topic
from app.devices.gc_esp32 import GrowCentralEsp32Provider
from app.devices.gc_calibration import CalibrationStore
from app.devices import gc_pairing
from app.security import require_write_auth
from app import rooms

ID='gc-soil-test'
HARDWARE_UID='0011223344556677'
ANNOUNCE={'schema':'gc-device-v1','protocol':'gc-esp32-mqtt-v1','id':ID,'name':'Soil node','device_class':'sensor','model':'GC-SOIL-XIAO-C3-HW390','firmware':'0.3.0','hardware_uid':HARDWARE_UID,'calibration':{'ready':True,'air_done':True,'wet_done':True,'substrate_done':True,'air_raw':3767,'wet_raw':1310,'substrate_raw':2500},'capabilities':['soil_moisture']}

def packet(key, kind='announce', seq=1, body=None, device_id=ID):
    raw=json.dumps({'device_id':device_id,'kind':kind,'seq':seq,'body':ANNOUNCE if body is None else body},separators=(',',':'))
    public=key.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
    return json.dumps({'schema':'gc-signed-v1','algorithm':'ecdsa-p256-sha256','public_key':base64.b64encode(public).decode(),'message':raw,'signature':base64.b64encode(key.sign(raw.encode(),ec.ECDSA(hashes.SHA256()))).decode()}).encode()

@pytest.fixture
def discovered(tmp_path,monkeypatch):
    monkeypatch.setenv('GC_DEVICE_TRUST_DB',str(tmp_path/'trust.db'))
    monkeypatch.setenv('GC_CALIBRATION_DB',str(tmp_path/'calibration.db'))
    key=ec.generate_private_key(ec.SECP256R1());message=verify_message(packet(key),kind='announce')
    store=TrustStore();row=store.discover(parse_announcement(json.dumps(ANNOUNCE)),message)
    return store,key,row


def add_calibration(row):
    return CalibrationStore().record(device_id=ID,fingerprint=row['fingerprint'],public_key=row['public_key'],hardware_uid=HARDWARE_UID,firmware_version='0.3.0',air_raw=3767,wet_raw=1310,substrate_raw=2500,quality={'status':'verified','signal_quality':'GOOD'})

def accept(store,row,assign=lambda:None):
    return store.accept(ID,name='Topf links',room_id='room1',fingerprint=row['fingerprint'][-16:],proved_key=row['public_key'],assign=assign)


def test_discovery_does_not_grant_access_and_survives_restart(discovered):
    store,key,row=discovered
    assert row['status']=='DISCOVERED' and row['name'] is None and row['room_id'] is None
    with pytest.raises(PermissionError):store.require_trusted(ID)
    assert TrustStore(store.path).get(ID)['fingerprint']==row['fingerprint']
    assert store.path.stat().st_mode & 0o777 == 0o600

@pytest.mark.parametrize('state',['REJECTED','REVOKED'])
def test_decisions_survive_rediscovery_and_need_manual_release(discovered,state):
    store,key,row=discovered
    if state=='REVOKED':accept(store,row)
    store.transition(ID,state)
    assert store.discover(parse_announcement(json.dumps(ANNOUNCE)),verify_message(packet(key,seq=2),kind='announce'))['status']==state
    with pytest.raises(ValueError):accept(store,row)
    with pytest.raises(PermissionError):store.require_trusted(ID)
    assert store.transition(ID,'DISCOVERED')['status']=='DISCOVERED'
    assert accept(store,row)['status']=='TRUSTED'


def test_unsigned_legacy_sensor_is_visible_but_not_admitted(tmp_path):
    store=TrustStore(tmp_path/'trust.db');row=store.discover(parse_announcement(json.dumps(ANNOUNCE)),None)
    assert row['status']=='DISCOVERED' and row['identity_verified'] is False
    with pytest.raises(PermissionError):store.accept(ID,name='Pot',room_id='room',fingerprint='0'*16,proved_key=None,assign=lambda:None)


def test_room_save_failure_never_grants_trust(discovered):
    store,key,row=discovered
    def fail():raise OSError('room storage failed')
    with pytest.raises(OSError):accept(store,row,fail)
    assert store.get(ID)['status']=='DISCOVERED'


def test_fingerprint_and_live_proof_key_must_match(discovered):
    store,key,row=discovered
    for fingerprint,proved in [('0'*16,row['public_key']),(row['fingerprint'][-16:],'another key')]:
        with pytest.raises(PermissionError):store.accept(ID,name='Pot',room_id='room',fingerprint=fingerprint,proved_key=proved,assign=lambda:None)
    assert store.get(ID)['status']=='DISCOVERED'


def test_identity_cannot_be_replaced_by_same_id(discovered):
    store,key,row=discovered;other=ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(PermissionError):store.discover(parse_announcement(json.dumps(ANNOUNCE)),verify_message(packet(other,seq=2),kind='announce'))
    with pytest.raises(PermissionError):store.discover(parse_announcement(json.dumps(ANNOUNCE)),None)
    assert store.get(ID)['fingerprint']==row['fingerprint']


def test_signed_payload_topic_kind_and_tampering_are_checked(discovered):
    store,key,row=discovered
    envelope=json.loads(packet(key));envelope['message']=envelope['message'].replace('Soil node','Impostor')
    with pytest.raises(ValueError):verify_message(json.dumps(envelope),kind='announce')
    with pytest.raises(ValueError):verify_message(packet(key),kind='state')
    with pytest.raises(ValueError):verify_message(packet(key),kind='announce',device_id='gc-soil-other')
    with pytest.raises(ValueError):verify_message(json.dumps(ANNOUNCE),kind='announce')


def test_replay_and_revocation_fail_closed(discovered):
    store,key,row=discovered;accept(store,row)
    body={'nonce':'x','state':{'soil_moisture':42}}
    newer=verify_message(packet(key,'proof',seq=100,body=body),kind='proof')
    receipt=store.receive(newer);assert store.receive(newer)==receipt
    for seq,value in [(99,42),(100,70)]:
        with pytest.raises(PermissionError):store.receive(verify_message(packet(key,'proof',seq=seq,body={'nonce':'x','state':{'soil_moisture':value}}),kind='proof'))
    store.transition(ID,'REVOKED')
    with pytest.raises(PermissionError):store.receive(verify_message(packet(key,'proof',seq=101,body=body),kind='proof'))


def test_unauthorized_state_never_contacts_broker(discovered,monkeypatch):
    provider=GrowCentralEsp32Provider()
    monkeypatch.setattr(provider,'_client',lambda:pytest.fail('unauthorized sensor must not be read'))
    with pytest.raises(PermissionError):asyncio.run(provider.state(ID))


@pytest.mark.parametrize("value", [42, None, 101, float("nan"), True, "42"])
def test_provider_uses_live_nonce_and_ignores_replayed_proof(discovered,monkeypatch,value):
    store,key,row=discovered;accept(store,row);add_calibration(row);provider=GrowCentralEsp32Provider();calls=[]
    class FakeClient:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def subscribe(self,topic):calls.append(('subscribe',topic))
        async def publish(self,topic,payload,**kwargs):
            assert kwargs['retain'] is False
            self.nonce=json.loads(payload)['nonce'];calls.append(('publish',topic))
        @property
        def messages(self):
            async def stream():
                for n,seq in [('replayed',2),(self.nonce,3)]:
                    yield SimpleNamespace(topic=device_topic(provider.root,ID,'proof'),payload=packet(key,'proof',seq=seq,body={'nonce':n,'hardware_uid':HARDWARE_UID,'calibration':ANNOUNCE['calibration'],'state':{'soil_moisture':value,'meta':{'firmware':'0.3.0','sensor_ok':True,'quality':'GOOD'}}}))
            return stream()
    monkeypatch.setattr(provider,'_client',FakeClient)
    if value is None or type(value) is int and value == 42:
        result=asyncio.run(provider.state(ID)); assert result['soil_moisture']==value and result['meta']['calibration_status']=='valid' and result['online'] is True
    else:
        with pytest.raises(ValueError):asyncio.run(provider.state(ID))
    assert calls[0][0]=='subscribe' and calls[1][0]=='publish'
    assert store.get(ID)['status']=='TRUSTED'


def test_manual_accept_api_requires_name_room_proof_and_authorization(discovered,monkeypatch,tmp_path):
    store,key,row=discovered;add_calibration(row);monkeypatch.setattr(rooms,'DATA_FILE',tmp_path/'rooms.json')
    state=rooms.empty_state();state['rooms']=[{'id':'room1','name':'Zelt'}];rooms.save_state(state)
    app=FastAPI();app.include_router(gc_pairing.router)
    body={'name':'Topf links','room_id':'room1','fingerprint_confirmation':row['fingerprint'][-16:]}
    assert TestClient(app).post(f'/api/devices/trust/{ID}/accept',json=body).status_code in (401,503)
    app.dependency_overrides[require_write_auth]=lambda:None
    async def prove(device_id):return verify_message(packet(key,'proof',seq=2,body={'nonce':'fresh','hardware_uid':HARDWARE_UID,'calibration':ANNOUNCE['calibration'],'state':{'meta':{'firmware':'0.3.0','sensor_ok':True,'quality':'GOOD'}}}),kind='proof')
    from app.devices.runtime import runtime
    monkeypatch.setattr(runtime.get('growcentral_esp32'),'prove_identity',prove)
    client=TestClient(app)
    assert client.post(f'/api/devices/trust/{ID}/accept',json={**body,'name':'   '}).status_code==422
    assert client.post(f'/api/devices/trust/{ID}/accept',json={**body,'room_id':'missing'}).status_code==404
    r=client.post(f'/api/devices/trust/{ID}/accept',json=body)
    assert r.status_code==200,r.text
    assert r.json()['device']['status']=='TRUSTED' and r.json()['credential_transfer']=='disabled'
    assert rooms.load_state()['assignments'][f'growcentral_esp32:{ID}']=='room1'
    assert client.post(f'/api/devices/trust/{ID}/revoke').status_code==200
    with pytest.raises(PermissionError):store.require_trusted(ID)


def test_unknown_sensor_cannot_be_assigned_directly(discovered,monkeypatch,tmp_path):
    monkeypatch.setattr(rooms,'DATA_FILE',tmp_path/'rooms.json')
    state=rooms.empty_state();state['rooms']=[{'id':'room1','name':'Zelt'}];rooms.save_state(state)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:asyncio.run(rooms.assign_device('room1',rooms.DeviceAssignment(device_id=f'growcentral_esp32:{ID}')))
    assert exc.value.status_code==403 and rooms.load_state()['assignments']=={}


def test_factory_reset_retires_old_key_and_requires_new_acceptance(discovered):
    store,key,row=discovered
    accept(store,row)
    with pytest.raises(ValueError):store.reset_identity(ID,row['fingerprint'][-16:])
    store.transition(ID,'REVOKED')
    reset=store.reset_identity(ID,row['fingerprint'][-16:])
    assert reset['status']=='DISCOVERED' and not reset['identity_verified']
    with pytest.raises(PermissionError):store.discover(parse_announcement(json.dumps(ANNOUNCE)),verify_message(packet(key,seq=2),kind='announce'))
    replacement=ec.generate_private_key(ec.SECP256R1())
    new=store.discover(parse_announcement(json.dumps(ANNOUNCE)),verify_message(packet(replacement),kind='announce'))
    assert new['status']=='DISCOVERED' and new['fingerprint']!=row['fingerprint']
    assert accept(store,new)['status']=='TRUSTED'


def test_native_room_collection_excludes_untrusted_sensor(discovered,monkeypatch):
    from app.devices.provider import DiscoveredDevice
    from app.devices.models import DeviceClass, Capability
    from app.devices.runtime import runtime
    class FakeProvider:
        async def discover(self,timeout):
            return [DiscoveredDevice('growcentral_esp32',ID,'Unknown',DeviceClass.SENSOR,(Capability.SOIL_MOISTURE,),'mqtt')]
        async def state(self,_id):pytest.fail('untrusted sensor must not enter room data')
        async def health(self,_id):pytest.fail('untrusted sensor must not enter room data')
    original=runtime.get
    monkeypatch.setattr(runtime,'get',lambda name:FakeProvider() if name=='growcentral_esp32' else original(name))
    assert asyncio.run(rooms._native_gc_devices())==[]


def test_trusted_sensor_never_receives_actuator_commands(discovered,monkeypatch):
    store,key,row=discovered;accept(store,row)
    provider=GrowCentralEsp32Provider()
    monkeypatch.setattr(provider,'_client',lambda:pytest.fail('sensor pairing cannot publish actuator commands'))
    from app.devices.models import Capability
    with pytest.raises(PermissionError):asyncio.run(provider.command(ID,Capability.POWER,True))


def test_legacy_native_alias_cannot_bypass_trust_for_room_history(discovered,monkeypatch,tmp_path):
    monkeypatch.setattr(rooms,'DATA_FILE',tmp_path/'rooms.json')
    state=rooms.empty_state();state['rooms']=[{'id':'room1','name':'Test'}];state['assignments'][f'growcentral_esp32:{ID}']='room1';rooms.save_state(state)
    async def legacy(*,refresh):return {'devices':[{'id':f'growcentral_esp32:{ID}','online':True,'state':{'soil_moisture':90}}]}
    async def native(timeout):return []
    monkeypatch.setattr(rooms,'device_overview',legacy);monkeypatch.setattr(rooms,'_native_gc_devices',native)
    assert asyncio.run(rooms.capture_room_sensors_once())==0
    assert rooms.load_state()['sensor_history']==[]


def test_sensor_acceptance_without_hex_typing_requires_confirmation_and_fresh_key(discovered, monkeypatch, tmp_path):
    store,key,row=discovered;add_calibration(row)
    monkeypatch.setattr(rooms,'DATA_FILE',tmp_path/'rooms.json')
    state=rooms.empty_state();state['rooms']=[{'id':'room1','name':'Test'}];rooms.save_state(state)
    app=FastAPI();app.include_router(gc_pairing.router);app.dependency_overrides[require_write_auth]=lambda:None
    from app.devices.runtime import runtime
    calls=[]
    async def prove(device_id):
        calls.append(device_id)
        return verify_message(packet(key,'proof',seq=2,body={'nonce':'fresh','hardware_uid':HARDWARE_UID,'calibration':ANNOUNCE['calibration'],'state':{'meta':{'firmware':'0.3.0','sensor_ok':True,'quality':'GOOD'}}}),kind='proof')
    monkeypatch.setattr(runtime.get('growcentral_esp32'),'prove_identity',prove)
    client=TestClient(app)
    body={'name':'Boden','room_id':'room1','fingerprint_confirmation':row['fingerprint']}
    assert client.post(f'/api/devices/trust/{ID}/accept',json=body).status_code==403
    assert client.post(f'/api/devices/trust/{ID}/accept',json={**body,'identity_confirmed':'yes'}).status_code==422
    assert client.post(f'/api/devices/trust/{ID}/accept',json={**body,'identity_confirmed':True,'fingerprint_confirmation':'0'*64}).status_code==403
    assert not calls
    response=client.post(f'/api/devices/trust/{ID}/accept',json={**body,'identity_confirmed':True})
    assert response.status_code==200,response.text
    assert calls==[ID] and store.get(ID)['status']=='TRUSTED'


def test_revoke_and_release_remove_native_room_assignment(discovered, monkeypatch, tmp_path):
    store, key, row = discovered
    monkeypatch.setattr(rooms, 'DATA_FILE', tmp_path / 'rooms.json')
    state = rooms.empty_state(); state['rooms'] = [{'id': 'room1', 'name': 'Zelt'}]; rooms.save_state(state)
    def assign():
        with rooms.edit_state() as current:
            current['assignments'][f'growcentral_esp32:{ID}'] = 'room1'
    accept(store, row, assign)
    assert rooms.load_state()['assignments'][f'growcentral_esp32:{ID}'] == 'room1'
    asyncio.run(gc_pairing._transition(ID, 'REVOKED'))
    assert store.get(ID)['status'] == 'REVOKED'
    assert f'growcentral_esp32:{ID}' not in rooms.load_state()['assignments']
    asyncio.run(gc_pairing._transition(ID, 'DISCOVERED'))
    assert store.get(ID)['status'] == 'DISCOVERED'
    assert f'growcentral_esp32:{ID}' not in rooms.load_state()['assignments']


def test_room_counter_ignores_stale_untrusted_native_assignment(discovered, monkeypatch, tmp_path):
    store, key, row = discovered
    monkeypatch.setattr(rooms, 'DATA_FILE', tmp_path / 'rooms.json')
    state = rooms.empty_state(); state['rooms'] = [{'id': 'room1', 'name': 'Zelt'}]
    state['assignments'][f'growcentral_esp32:{ID}'] = 'room1'; rooms.save_state(state)
    result = asyncio.run(rooms.list_rooms())
    assert result['rooms'][0]['device_count'] == 0
    accept(store, row)
    result = asyncio.run(rooms.list_rooms())
    assert result['rooms'][0]['device_count'] == 1


def test_provider_derives_three_point_reference_from_signed_filtered_raw(discovered,monkeypatch):
    store,key,row=discovered;accept(store,row)
    CalibrationStore().record(device_id=ID,fingerprint=row['fingerprint'],public_key=row['public_key'],hardware_uid=HARDWARE_UID,firmware_version='0.3.0',air_raw=3770,wet_raw=1180,substrate_raw=2027,quality={'status':'verified'})
    provider=GrowCentralEsp32Provider()
    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def subscribe(self,topic): pass
        async def publish(self,topic,payload,**kwargs): self.nonce=json.loads(payload)['nonce']
        @property
        def messages(self):
            async def stream():
                body={'nonce':self.nonce,'hardware_uid':HARDWARE_UID,'calibration':ANNOUNCE['calibration'],'state':{'soil_moisture':12.3,'meta':{'filtered_raw':2027.0,'firmware':'0.3.0','sensor_ok':True,'quality':'GOOD'}}}
                yield SimpleNamespace(topic=device_topic(provider.root,ID,'proof'),payload=packet(key,'proof',seq=3,body=body))
            return stream()
    monkeypatch.setattr(provider,'_client',FakeClient)
    result=asyncio.run(provider.state(ID))
    assert result['soil_moisture'] == pytest.approx(67.297, abs=0.002)
    assert result['soil_substrate_reference_percent'] == pytest.approx(67.297, abs=0.002)
    assert result['soil_substrate_index_percent'] == pytest.approx(100.0)
    assert result['soil_substrate_delta_pp'] == pytest.approx(0.0)
    assert result['meta']['calculation_source'] == 'server_three_point_reference'
    assert result['meta']['sensor_reported_soil_moisture'] == 12.3
    assert result['meta']['calibration_consistency_pp'] > 50
