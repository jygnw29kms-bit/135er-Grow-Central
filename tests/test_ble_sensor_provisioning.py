import asyncio, base64, json
from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.provisioning import ble
from app.devices.gc_identity import verify_message
from app.devices.gc_trust import TrustStore
from app import rooms

ID='gc-soil-aabbcc'
ANN={'schema':'gc-device-v1','protocol':'gc-esp32-mqtt-v1','id':ID,'name':'GC Soil','device_class':'sensor','model':'GC-SOIL-XIAO-C3-HW390','firmware':'0.5.0','capabilities':['soil_moisture']}

class FakeSensor:
    def __init__(self,confirm=True):
        self.key=ec.generate_private_key(ec.SECP256R1());self.confirm=confirm;self.notify=None;self.nonce=None;self.shared=None;self.parts={};self.total=None;self.config=None;self.seq=0
    def signed(self,kind,body):
        self.seq+=1;raw=json.dumps({'device_id':ID,'kind':kind,'seq':self.seq,'body':body},separators=(',',':'))
        pub=self.key.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
        return json.dumps({'schema':'gc-signed-v1','algorithm':'ecdsa-p256-sha256','public_key':base64.b64encode(pub).decode(),'message':raw,'signature':base64.b64encode(self.key.sign(raw.encode(),ec.ECDSA(hashes.SHA256()))).decode()})
    def emit_proof(self,proof):
        width=120;parts=[proof[i:i+width] for i in range(0,len(proof),width)]
        for i,part in enumerate(parts):self.notify(0,f'P|{i}|{len(parts)}|{part}'.encode())
    async def write(self,data):
        value=bytes(data).decode()
        if value.startswith('H|'):
            _,self.nonce,peer=value.split('|',2);pi_pub=ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),base64.b64decode(peer))
            eph=ec.generate_private_key(ec.SECP256R1());secret=eph.exchange(ec.ECDH(),pi_pub)
            self.shared=HKDF(algorithm=hashes.SHA256(),length=32,salt=bytes.fromhex(self.nonce),info=ble.PROTOCOL.encode()).derive(secret)
            pub=eph.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
            self.emit_proof(self.signed('ble_proof',{'nonce':self.nonce,'protocol':ble.PROTOCOL,'ephemeral':base64.b64encode(pub).decode(),'announcement':ANN}))
        elif value.startswith('A|') and self.confirm:
            self.notify(0,('R|'+self.nonce).encode())
        elif value.startswith('C|'):
            _,idx,total,chunk=value.split('|',3);idx=int(idx);self.total=int(total);self.parts[idx]=chunk
            if len(self.parts)==self.total:
                raw=base64.b64decode(''.join(self.parts[i] for i in range(self.total)));plain=AESGCM(self.shared).decrypt(raw[:12],raw[12:],ID.encode()).decode();self.config=plain
                self.notify(0,('D|'+self.nonce).encode())
    def network_proof(self):return verify_message(self.signed('proof',{'nonce':'network','state':{'soil_moisture':42}}),kind='proof',device_id=ID)

class FakeClient:
    sensor=None
    def __init__(self,address):self.address=address
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    async def start_notify(self,uuid,callback):self.sensor.notify=callback
    async def write_gatt_char(self,uuid,data,response=True):await self.sensor.write(data)

class FakeScanner:
    @staticmethod
    async def discover(timeout,return_adv=True):
        adv=SimpleNamespace(service_uuids=[ble.SERVICE_UUID],local_name=ID,rssi=-42)
        return {'AA:BB':(SimpleNamespace(name=ID),adv)}

@pytest.fixture
def appenv(monkeypatch,tmp_path):
    ble._candidates.clear();sensor=FakeSensor();FakeClient.sensor=sensor
    monkeypatch.setattr(ble,'BleakClient',FakeClient);monkeypatch.setattr(ble,'BleakScanner',FakeScanner)
    monkeypatch.setenv('GC_DEVICE_TRUST_DB',str(tmp_path/'trust.db'));monkeypatch.setattr(rooms,'DATA_FILE',tmp_path/'rooms.json')
    rooms.save_state({**rooms.empty_state(),'rooms':[{'id':'room1','name':'Zelt'}]})
    calls=[]
    def broker(action,**kwargs):
        calls.append(action)
        if action=='info':return {'hosts':['192.168.1.20']}
        return {'host':'192.168.1.20','port':8883,'username':ID,'password':'mqtt-secret','ca':base64.b64encode(b'fake-der-ca').decode()}
    monkeypatch.setattr(ble,'request_broker',broker)
    from app.devices.runtime import runtime
    original=runtime.get
    monkeypatch.setattr(runtime,'get',lambda name:SimpleNamespace(prove_identity=lambda device_id:asyncio.sleep(0,result=sensor.network_proof())) if name=='growcentral_esp32' else original(name))
    app=FastAPI();app.include_router(ble.router);app.dependency_overrides[ble.require_write_auth]=lambda:None
    return TestClient(app),sensor,calls

def test_secure_ble_discovery_and_manual_provision(appenv):
    client,sensor,calls=appenv
    found=client.post('/api/devices/ble/scan?timeout=1').json()['devices'];assert found[0]['device_id']==ID
    inspected=client.post(f'/api/devices/ble/{ID}/inspect');assert inspected.status_code==200
    row=TrustStore().get(ID);assert row['status']=='DISCOVERED' and row['identity_verified'] is True
    response=client.post(f'/api/devices/ble/{ID}/provision',json={'ssid':'GrowWiFi','password':'wifi-secret','broker_host':'192.168.1.20','name':'Topf links','room_id':'room1'})
    assert response.status_code==200,response.text
    assert TrustStore().get(ID)['status']=='TRUSTED';assert rooms.load_state()['assignments']['growcentral_esp32:'+ID]=='room1'
    assert sensor.config.startswith('V1|') and 'wifi-secret' not in json.dumps(response.json()) and 'mqtt-secret' not in json.dumps(response.json())
    assert calls==['provision']

def test_rejected_sensor_never_receives_credentials(appenv):
    client,sensor,calls=appenv;client.post('/api/devices/ble/scan?timeout=1');client.post(f'/api/devices/ble/{ID}/inspect');TrustStore().transition(ID,'REJECTED')
    response=client.post(f'/api/devices/ble/{ID}/provision',json={'ssid':'GrowWiFi','password':'wifi-secret','broker_host':'192.168.1.20','name':'Topf','room_id':'room1'})
    assert response.status_code==409 and calls==[] and sensor.config is None

def test_missing_physical_boot_confirmation_blocks_secret_creation(appenv,monkeypatch):
    client,sensor,calls=appenv;sensor.confirm=False;monkeypatch.setattr(ble,'PAIR_TIMEOUT',0.05)
    client.post('/api/devices/ble/scan?timeout=1');client.post(f'/api/devices/ble/{ID}/inspect')
    response=client.post(f'/api/devices/ble/{ID}/provision',json={'ssid':'GrowWiFi','password':'wifi-secret','broker_host':'192.168.1.20','name':'Topf','room_id':'room1'})
    assert response.status_code==408 and calls==[] and TrustStore().get(ID)['status']=='DISCOVERED'
