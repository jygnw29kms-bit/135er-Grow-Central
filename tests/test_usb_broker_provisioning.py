import asyncio
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import time
from types import SimpleNamespace

import aiomqtt
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
import pytest

from app.provisioning import broker_service as broker

PASSWD = os.getenv('GC_TEST_MOSQUITTO_PASSWD') or shutil.which('mosquitto_passwd')
BINARY = os.getenv('GC_TEST_MOSQUITTO') or shutil.which('mosquitto')


@pytest.fixture
def service(monkeypatch, tmp_path):
    base=tmp_path/'broker'
    mosquitto=tmp_path/'mosquitto'
    (mosquitto/'conf.d').mkdir(parents=True)
    monkeypatch.setattr(broker,'BASE',base)
    monkeypatch.setattr(broker,'MOSQUITTO',mosquitto)
    monkeypatch.setattr(broker,'local_hosts',lambda:['127.0.0.1','135er-grow-central.local'])
    monkeypatch.setattr(broker.grp,'getgrnam',lambda _:SimpleNamespace(gr_gid=os.getgid()))
    monkeypatch.setattr(broker.os,'chown',lambda *a:None)
    monkeypatch.setattr(broker.os,'fchown',lambda *a:None)
    original_run=subprocess.run
    calls=[]
    def execute(args, **kwargs):
        if args[0]=='/usr/bin/systemctl':
            calls.append(args)
            return SimpleNamespace(returncode=0)
        return original_run(args,**kwargs)
    monkeypatch.setattr(broker.subprocess,'run',execute)
    original_which=shutil.which
    monkeypatch.setattr(broker.shutil,'which',lambda name:PASSWD if name=='mosquitto_passwd' else original_which(name))
    return base,mosquitto,calls


def test_ca_and_server_have_valid_scope_and_private_modes(service):
    base,_,_=service
    ca=broker.certificates(['127.0.0.1','135er-grow-central.local'])
    server=x509.load_pem_x509_certificate((base/'server.crt').read_bytes())
    ca.public_key().verify(server.signature,server.tbs_certificate_bytes,ec.ECDSA(server.signature_hash_algorithm))
    san=server.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert '135er-grow-central.local' in san.get_values_for_type(x509.DNSName)
    assert str(san.get_values_for_type(x509.IPAddress)[0])=='127.0.0.1'
    assert server.not_valid_after_utc>datetime.now(timezone.utc)
    assert (base/'ca.key').stat().st_mode & 0o777==0o600
    original=(base/'ca.crt').read_bytes()
    broker.certificates(['127.0.0.1','192.168.1.20'])
    assert (base/'ca.crt').read_bytes()==original
    updated=x509.load_pem_x509_certificate((base/'server.crt').read_bytes())
    assert '192.168.1.20' in {str(ip) for ip in updated.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.IPAddress)}


@pytest.mark.parametrize('device_id,host',[('other-user','127.0.0.1'),('gc-soil-aabbcc','attacker.example'),('../path','127.0.0.1')])
def test_nonlocal_targets_and_arbitrary_users_are_rejected(service,device_id,host):
    with pytest.raises(ValueError): broker.configure(device_id,host)
    assert not service[0].exists()


def test_existing_tls_listener_is_not_overwritten(service):
    base,mosquitto,calls=service
    existing=mosquitto/'conf.d/manual.conf'
    existing.write_text('listener 8883\nallow_anonymous false\n')
    with pytest.raises(RuntimeError):broker.configure('gc-soil-aabbcc','127.0.0.1')
    assert not base.exists() and not calls
    assert existing.read_text()=='listener 8883\nallow_anonymous false\n'


@pytest.mark.skipif(not PASSWD,reason='native mosquitto_passwd required')
def test_individual_credentials_are_stable_and_hashes_preserved(service):
    base,_,calls=service
    first=broker.configure('gc-soil-aabbcc','127.0.0.1')
    saved=(base/'passwords').read_text().splitlines()[0]
    second=broker.configure('gc-soil-ddeeff','127.0.0.1')
    repeated=broker.configure('gc-soil-aabbcc','127.0.0.1')
    assert first['password']==repeated['password']!=second['password']
    assert (base/'passwords').read_text().splitlines()[0]==saved
    assert first['password'] not in (base/'passwords').read_text()
    assert (base/'accounts.json').stat().st_mode & 0o777==0o600
    assert x509.load_der_x509_certificate(base64.b64decode(first['ca']))
    assert all(args==['/usr/bin/systemctl','restart','mosquitto.service'] for args in calls)


@pytest.mark.skipif(not PASSWD or not BINARY,reason='native TLS broker required')
def test_generated_broker_certificates_accounts_and_acl_work(service):
    async def scenario():
        base,mosquitto,_=service
        account=broker.configure('gc-soil-aabbcc','127.0.0.1')
        with socket.socket() as reserve:
            reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
        conf=mosquitto/'test.conf'
        conf.write_text('per_listener_settings true\n'+(mosquitto/'conf.d/grow-central-usb-tls.conf').read_text().replace('listener 8883 0.0.0.0',f'listener {port} 127.0.0.1'))
        process=subprocess.Popen([BINARY,'-c',str(conf)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            for _ in range(100):
                try:
                    with socket.create_connection(('127.0.0.1',port),timeout=.1):break
                except OSError:time.sleep(.02)
            context=ssl.create_default_context(cafile=str(base/'ca.crt'))
            async with aiomqtt.Client('127.0.0.1',port=port,tls_context=context,username=account['username'],password=account['password']) as client:
                await client.subscribe('growcentral/v1/devices/gc-soil-aabbcc/challenge')
                await client.publish('growcentral/v1/devices/gc-soil-aabbcc/state','{"soil_moisture":42}',retain=True,qos=1)
            with pytest.raises(aiomqtt.MqttError):
                async with aiomqtt.Client('127.0.0.1',port=port,tls_context=context,username=account['username'],password='wrong-password'):
                    pass
            with pytest.raises(aiomqtt.MqttError):
                async with aiomqtt.Client('127.0.0.1',port=port,tls_context=context):pass
            assert 'pattern write growcentral/v1/devices/%u/state' in (base/'acl').read_text()
            assert '/set' not in (base/'acl').read_text()
        finally:
            process.terminate();process.wait(timeout=5)
    asyncio.run(scenario())
