"""Real TLS MQTT/ACL round trip with a software sensor, not physical hardware."""
import asyncio
import base64
from datetime import datetime, timedelta, timezone
import ipaddress
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import ssl
import subprocess

import aiomqtt
import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from fastapi import FastAPI
from app import rooms
from app.devices.gc_esp32 import GrowCentralEsp32Provider
from app.devices import gc_pairing
from app.devices.gc_trust import TrustStore
from app.devices.runtime import runtime
from app.security import require_write_auth

ID='gc-soil-tls-test'
BROKER=os.getenv('GC_TEST_MOSQUITTO') or shutil.which('mosquitto')
PASSWORD_TOOL=os.getenv('GC_TEST_MOSQUITTO_PASSWD') or shutil.which('mosquitto_passwd')


def signed(key,kind,sequence,body,device_id=ID):
    message=json.dumps({'device_id':device_id,'kind':kind,'seq':sequence,'body':body},separators=(',',':'))
    public=key.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
    return json.dumps({'schema':'gc-signed-v1','algorithm':'ecdsa-p256-sha256','public_key':base64.b64encode(public).decode(),'message':message,'signature':base64.b64encode(key.sign(message.encode(),ec.ECDSA(hashes.SHA256()))).decode()})


def announce(device_id=ID):
    return {'schema':'gc-device-v1','protocol':'gc-esp32-mqtt-v1','id':device_id,'name':'TLS Software Sensor','device_class':'sensor','firmware':'0.3.0','model':'test-node','capabilities':['soil_moisture']}


@pytest.mark.skipif(not BROKER or not PASSWORD_TOOL,reason='native Mosquitto tools required for TLS integration')
def test_real_tls_broker_acl_and_manual_sensor_acceptance(tmp_path,monkeypatch):
    ca_key=ec.generate_private_key(ec.SECP256R1());server_key=ec.generate_private_key(ec.SECP256R1())
    now=datetime.now(timezone.utc)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'GC Test CA')])
    ca=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),critical=False)
        .sign(ca_key,hashes.SHA256()))
    server=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')])).issuer_name(name)
        .public_key(server_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()),critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),critical=False)
        .sign(ca_key,hashes.SHA256()))
    for path,data in [(tmp_path/'ca.crt',ca.public_bytes(serialization.Encoding.PEM)),(tmp_path/'server.crt',server.public_bytes(serialization.Encoding.PEM)),(tmp_path/'server.key',server_key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))]:
        path.write_bytes(data);path.chmod(0o600)
    backend_password=secrets.token_urlsafe(24);node_password=secrets.token_urlsafe(24)
    passwords=tmp_path/'passwords';passwords.write_text(f'growcentral:{backend_password}\n{ID}:{node_password}\n');passwords.chmod(0o600)
    subprocess.run([PASSWORD_TOOL,'-U',str(passwords)],check=True,capture_output=True)
    assert passwords.read_text().startswith('growcentral:$7$')
    acl=tmp_path/'acl';acl.write_text(Path('deploy/mqtt/growcentral.acl.example').read_text())
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    conf=tmp_path/'mosquitto.conf';conf.write_text(f'listener {port} 127.0.0.1\nallow_anonymous false\npassword_file {passwords}\nacl_file {acl}\ncafile {tmp_path/"ca.crt"}\ncertfile {tmp_path/"server.crt"}\nkeyfile {tmp_path/"server.key"}\npersistence false\n')
    monkeypatch.setenv('GC_DEVICE_TRUST_DB',str(tmp_path/'trust.db'))
    monkeypatch.setenv('GC_MQTT_HOST','127.0.0.1');monkeypatch.setenv('GC_MQTT_PORT',str(port));monkeypatch.setenv('GC_MQTT_TLS','true');monkeypatch.setenv('GC_MQTT_CA_FILE',str(tmp_path/'ca.crt'));monkeypatch.setenv('GC_MQTT_USERNAME','growcentral');monkeypatch.setenv('GC_MQTT_PASSWORD',backend_password)
    monkeypatch.setattr(rooms,'DATA_FILE',tmp_path/'rooms.json');room_state=rooms.empty_state();room_state['rooms']=[{'id':'room1','name':'Test room'}];rooms.save_state(room_state)
    provider=GrowCentralEsp32Provider();original=runtime.get;monkeypatch.setattr(runtime,'get',lambda name:provider if name=='growcentral_esp32' else original(name))
    process=subprocess.Popen([BROKER,'-c',str(conf)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    async def run():
        ctx=ssl.create_default_context(cafile=str(tmp_path/'ca.crt'))
        for attempt in range(30):
            if process.poll() is not None:pytest.fail('test TLS broker exited')
            try:
                async with aiomqtt.Client('127.0.0.1',port=port,username=ID,password=node_password,tls_context=ctx) as node:
                    break
            except aiomqtt.MqttError:
                await asyncio.sleep(.05)
        else:pytest.fail('TLS broker did not start')
        with pytest.raises(aiomqtt.MqttError):
            async with aiomqtt.Client('127.0.0.1',port=port,tls_context=ctx):pass
        with pytest.raises(aiomqtt.MqttError):
            async with aiomqtt.Client('127.0.0.1',port=port,username=ID,password='incorrect-test-password',tls_context=ctx):pass
        with pytest.raises(aiomqtt.MqttError):
            async with aiomqtt.Client('127.0.0.1',port=port,username=ID,password=node_password,tls_context=ssl.create_default_context()):pass
        key=ec.generate_private_key(ec.SECP256R1())
        async with aiomqtt.Client('127.0.0.1',port=port,username=ID,password=node_password,tls_context=ctx) as node:
            await node.subscribe(f'growcentral/v1/devices/{ID}/challenge')
            await node.publish(f'growcentral/v1/devices/{ID}/announce',signed(key,'announce',1,announce()),qos=1,retain=True)
            other='gc-soil-forbidden'
            await node.publish(f'growcentral/v1/devices/{other}/announce',signed(key,'announce',1,announce(other),other),qos=1,retain=True)
            discovered=await provider.discover(timeout=.15)
            assert [d.native_id for d in discovered]==[ID]
            assert discovered[0].metadata['trust_status']=='DISCOVERED'
            with pytest.raises(PermissionError):await provider.state(ID)
            sequence=1
            async def respond():
                nonlocal sequence
                async for request in node.messages:
                    sequence+=1
                    nonce=json.loads(request.payload)['nonce']
                    await node.publish(f'growcentral/v1/devices/{ID}/proof',signed(key,'proof',sequence,{'nonce':nonce,'state':{'soil_moisture':42.5,'meta':{'raw':2710,'sensor_ok':True,'quality':'EXCELLENT'}}}),qos=1,retain=False)
            task=asyncio.create_task(respond())
            try:
                app=FastAPI();app.include_router(gc_pairing.router);app.dependency_overrides[require_write_auth]=lambda:None
                row=TrustStore().get(ID)
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://test') as api:
                    r=await api.post(f'/api/devices/trust/{ID}/accept',json={'name':'Pot left','room_id':'room1','fingerprint_confirmation':row['fingerprint'][-16:]})
                    assert r.status_code==200,r.text
                state=await provider.state(ID)
                assert state['soil_moisture']==42.5 and state['meta']['sensor_ok'] is True
                assert rooms.load_state()['assignments'][f'growcentral_esp32:{ID}']=='room1'
                TrustStore().transition(ID,'REVOKED')
                with pytest.raises(PermissionError):await provider.state(ID)
            finally:
                task.cancel()
                await asyncio.gather(task,return_exceptions=True)
    try:
        asyncio.run(run())
    finally:
        process.terminate();process.wait(timeout=5)
