"""Real pseudo-terminal USB protocol with signed identities and API workflow."""
import base64
import hashlib
import json
import os
from pathlib import Path
import pty
import threading
import time
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.provisioning import usb
from app.devices.gc_identity import verify_message
from app.devices.gc_trust import TrustStore
from app import rooms


class Sensor:
    def __init__(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.counter = 0
        self.version = usb.VERSION
        self.commands = []
        self.master, self.slave = pty.openpty()
        self.path = os.ttyname(self.slave)
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def signed(self, nonce):
        self.counter += 1
        announcement = {'schema':'gc-device-v1','protocol':'gc-esp32-mqtt-v1','id':'gc-soil-aabbcc',
            'name':'Soil','device_class':'sensor','model':usb.MODEL,'firmware':self.version,'capabilities':['soil_moisture']}
        message = json.dumps({'device_id':'gc-soil-aabbcc','kind':'proof','seq':self.counter,
            'body':{'nonce':nonce,'announcement':announcement, 'state': {'soil_moisture':42}}})
        key = self.key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        return json.dumps({'schema':'gc-signed-v1','algorithm':'ecdsa-p256-sha256',
            'public_key':base64.b64encode(key).decode(),'message':message,
            'signature':base64.b64encode(self.key.sign(message.encode(), ec.ECDSA(hashes.SHA256()))).decode()})

    def serve(self):
        buffer = b''
        while not self.stop.is_set():
            try:
                buffer += os.read(self.master, 4096)
            except OSError:
                return
            while b'\n' in buffer:
                raw, buffer = buffer.split(b'\n', 1)
                command = raw.decode().strip()
                self.commands.append(command)
                if command.startswith('USB ID '):
                    response = 'GC_USB_ID ' + self.signed(command[7:])
                elif command.startswith('NET CA '): response = 'OK broker CA stored'
                elif command.startswith('NET MQTT '): response = 'OK MQTT configuration saved'
                elif command.startswith('NET WIFI '): response = 'OK WiFi configuration saved'
                else: response = 'UNKNOWN COMMAND'
                os.write(self.master, (response+'\n').encode())

    def close(self):
        self.stop.set()
        os.close(self.master)
        os.close(self.slave)


@pytest.fixture
def setup(monkeypatch, tmp_path):
    sensor = Sensor()
    monkeypatch.setattr(usb, 'ports', lambda: [{'id':'port-1','port':sensor.path,'label':'USB test','serial':'fixture'}])
    monkeypatch.setattr(usb, 'manager', usb.USBManager())
    monkeypatch.setenv('GC_DEVICE_TRUST_DB', str(tmp_path / 'trust.db'))
    monkeypatch.setattr(rooms, 'DATA_FILE', tmp_path/'rooms.json')
    rooms.save_state({**rooms.empty_state(), 'rooms':[{'id':'room-1','name':'Test room'}]})
    firmware = tmp_path/'firmware'
    firmware.mkdir()
    manifest = {'model':usb.MODEL,'chip':'esp32c3','version':usb.VERSION,'files':{}}
    for name, offset in usb.OFFSETS.items():
        content = b'firmware-test-fixture'
        (firmware/name).write_bytes(content)
        manifest['files'][name] = {'offset':offset,'sha256':hashlib.sha256(content).hexdigest()}
    (firmware/'manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setenv('GC_USB_FIRMWARE_DIR', str(firmware))
    broker_calls = []
    def broker(action, **values):
        broker_calls.append(action)
        if action == 'info': return {'ok':True,'hosts':['192.168.1.20']}
        return {'ok':True,'host':'192.168.1.20','port':8883,'username':'gc-soil-aabbcc',
            'password':'individual-test-password','ca':'public-test-certificate'}
    monkeypatch.setattr(usb,'request_broker',broker)
    class Provider:
        async def prove_identity(self, device_id):
            return verify_message(sensor.signed('b'*64), kind='proof',device_id=device_id)
    from app.devices.runtime import runtime
    monkeypatch.setattr(runtime,'get',lambda _:Provider())
    app = FastAPI()
    app.include_router(usb.router)
    app.dependency_overrides[usb.require_write_auth] = lambda: None
    with TestClient(app) as client:
        yield client, sensor, firmware, broker_calls
    sensor.close()


def wait(client):
    for _ in range(100):
        state = client.get('/api/devices/usb').json()['devices'][0]
        if not state['busy']: return state
        time.sleep(.02)
    pytest.fail('USB job did not finish')


def test_complete_real_serial_workflow(setup):
    client, sensor, _, broker_calls = setup
    assert client.get('/api/devices/usb').json()['devices'][0]['state'] == 'DETECTED'
    assert client.post('/api/devices/usb/port-1/inspect').status_code == 200
    assert wait(client)['state'] == 'NETWORK'
    assert TrustStore().get('gc-soil-aabbcc')['status'] == 'DISCOVERED'
    response = client.post('/api/devices/usb/port-1/network',json={'ssid':'home','password':'wifi-test-password','broker_host':'192.168.1.20'})
    assert response.status_code == 200
    state = wait(client)
    assert state['state'] == 'ASSIGN'
    assert 'individual-test-password' not in json.dumps(state)
    assert TrustStore().get('gc-soil-aabbcc')['status'] == 'DISCOVERED'
    assert client.post('/api/devices/usb/port-1/assign',json={'name':'  Soil A  ','room_id':'room-1'}).status_code == 200
    assert wait(client)['state'] == 'READY'
    assert TrustStore().get('gc-soil-aabbcc')['name'] == 'Soil A'
    assert rooms.load_state()['assignments']['growcentral_esp32:gc-soil-aabbcc'] == 'room-1'
    assert broker_calls == ['provision']
    assert any(command.startswith('NET CA ') for command in sensor.commands)
    assert any(command.startswith('NET MQTT 192.168.1.20|8883|gc-soil-aabbcc|') for command in sensor.commands)


def test_flash_uses_fixed_safe_ranges_and_preserves_nvs(setup, monkeypatch):
    client, _, _, _ = setup
    commands = []
    def execute(args, **kwargs):
        commands.append(args)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(usb.subprocess, 'run', execute)
    assert client.post('/api/devices/usb/port-1/flash',json={'board':'seeed_xiao_esp32c3','confirmed':False}).status_code == 422
    assert not commands
    assert client.post('/api/devices/usb/port-1/flash',json={'board':'seeed_xiao_esp32c3','confirmed':True}).status_code == 200
    assert wait(client)['state'] == 'NETWORK'
    args = commands[0]
    assert '--chip' in args and args[args.index('--chip')+1] == 'esp32c3'
    assert 'erase_flash' not in args and '0x9000' not in args
    assert all(hex(offset) in args for offset in usb.OFFSETS.values())


@pytest.mark.parametrize('mutation', ['hash','offset','extra','model'])
def test_tampered_package_prevents_flash(setup, monkeypatch, mutation):
    client, _, directory, _ = setup
    p = directory/'manifest.json'
    manifest=json.loads(p.read_text())
    if mutation=='hash': (directory/'firmware.bin').write_bytes(b'tampered')
    if mutation=='offset': manifest['files']['firmware.bin']['offset']=0x9000
    if mutation=='extra': manifest['files']['nvs.bin']={'offset':0x9000,'sha256':'0'*64}
    if mutation=='model': manifest['model']='other-board'
    p.write_text(json.dumps(manifest))
    monkeypatch.setattr(usb.subprocess,'run',lambda *a,**k:pytest.fail('must not execute flash'))
    assert client.post('/api/devices/usb/port-1/flash',json={'board':'seeed_xiao_esp32c3','confirmed':True}).status_code==503


def test_old_firmware_is_not_assumed_ready(setup):
    client,sensor,_,_ = setup
    sensor.version='0.3.0'
    client.post('/api/devices/usb/port-1/inspect')
    assert wait(client)['state']=='NEEDS_FIRMWARE'
    assert TrustStore().get('gc-soil-aabbcc') is None
    assert client.post('/api/devices/usb/port-1/assign',json={'name':'Soil','room_id':'room-1'}).status_code==409


def test_key_swap_prevents_credentials_and_acceptance(setup):
    client,sensor,_,calls=setup
    client.post('/api/devices/usb/port-1/inspect');wait(client)
    sensor.key=ec.generate_private_key(ec.SECP256R1())
    client.post('/api/devices/usb/port-1/network',json={'ssid':'home','password':'wifi-test-password','broker_host':'192.168.1.20'})
    assert wait(client)['state']=='BLOCKED'
    assert not calls
    assert TrustStore().get('gc-soil-aabbcc')['status']=='DISCOVERED'


def test_rejected_sensor_stays_blocked(setup):
    client,_,_,_=setup
    client.post('/api/devices/usb/port-1/inspect');wait(client)
    TrustStore().transition('gc-soil-aabbcc','REJECTED')
    client.post('/api/devices/usb/port-1/inspect')
    assert wait(client)['state']=='BLOCKED'
    assert TrustStore().get('gc-soil-aabbcc')['status']=='REJECTED'


def test_unknown_port_and_unverified_network_are_denied(setup):
    client,_,_,_=setup
    assert client.post('/api/devices/usb/not-a-path/inspect').status_code==404
    assert client.post('/api/devices/usb/port-1/network',json={'ssid':'home','password':'wifi-test-password','broker_host':'192.168.1.20'}).status_code==409


def test_input_errors_never_echo_password(setup):
    client,_,_,_=setup
    for password in ['SECRET\nCOMMAND','short']:
        response=client.post('/api/devices/usb/port-1/network',json={'ssid':'home','password':password,'broker_host':'192.168.1.20'})
        assert response.status_code==422
        assert password not in response.text and 'input' not in response.text


def test_usb_api_requires_auth(monkeypatch):
    monkeypatch.setattr('app.security.configured_api_token',lambda:'t'*40)
    monkeypatch.setattr('app.security.authenticated',lambda _:False)
    app=FastAPI();app.include_router(usb.router)
    with TestClient(app) as client:
        assert client.get('/api/devices/usb').status_code==401


def test_port_identity_stays_stable_when_tty_number_changes(monkeypatch):
    import importlib
    module=importlib.import_module('app.provisioning.usb')
    port=SimpleNamespace(vid=0x303a,pid=0x1001,device='/dev/ttyACM0',serial_number='abc',location='1-1',description='<img src=x>')
    monkeypatch.setattr(module.list_ports,'comports',lambda:[port])
    first=module.ports()[0]['id']
    port.device='/dev/ttyACM8'
    assert module.ports()[0]['id']==first
    port.device='/tmp/user-selected-device'
    assert module.ports()==[]


def test_disconnected_job_status_remains_queryable(setup, monkeypatch):
    client,_,_,_=setup
    client.post('/api/devices/usb/port-1/inspect');wait(client)
    monkeypatch.setattr(usb,'ports',lambda:[])
    result=client.get('/api/devices/usb').json()
    assert result['devices']==[]
    assert result['sessions'][0]['state']=='NETWORK'
    assert client.post('/api/devices/usb/port-1/connection').status_code==404


def test_network_key_mismatch_never_advances_to_assignment(setup, monkeypatch):
    client,sensor,_,_=setup
    client.post('/api/devices/usb/port-1/inspect');wait(client)
    other=Sensor()
    class WrongNetwork:
        async def prove_identity(self,id):return verify_message(other.signed('b'*64),kind='proof',device_id=id)
    from app.devices.runtime import runtime
    monkeypatch.setattr(runtime,'get',lambda _:WrongNetwork())
    try:
        client.post('/api/devices/usb/port-1/connection')
        assert wait(client)['state']=='BLOCKED'
        assert TrustStore().get('gc-soil-aabbcc')['status']=='DISCOVERED'
    finally:other.close()


def test_network_timeout_keeps_verified_sensor_at_network_step():
    import asyncio
    async def scenario():
        manager=usb.USBManager()
        session=usb.Session('port',state='CONNECTING',public_key='pinned-key',firmware=usb.VERSION)
        async def fail():raise TimeoutError('no network proof')
        manager.start(session,fail)
        await session.task
        assert session.state=='ERROR' and session.resume=='NETWORK'
        assert session.public_key=='pinned-key' and session.firmware==usb.VERSION
        assert 'LAN-IP' in session.message
    asyncio.run(scenario())


def test_mdns_broker_rejected_before_secret_transfer():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        usb.NetworkRequest(ssid='Test',password='test-password',broker_host='135er-grow-central.local')
    assert usb.NetworkRequest(ssid='Test',password='test-password',broker_host='192.168.178.80').broker_host=='192.168.178.80'
