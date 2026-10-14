#!/usr/bin/env python3
"""Update MQTT server identity compatibility without replacing CA/device keys."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import py_compile
import shutil
import subprocess
import tempfile
import urllib.request

SOURCE = '1fcf82f70f24797eabbbdd8bde9ac709d21fdd2e'
EXPECTED = '040a39f951ca1a1c974b10de2a27bddf29d4f9ccea4cdf82a391512ab2bff1e8'
BASE_HASH = '305194d05513c0d43b539555c44a56de8a281dc01779262d125557c2488402bf'
ROOT = Path('/opt/135er-grow-central')
CERTS = Path('/etc/mosquitto/grow-central-sensor-broker')
BACKUPS = Path('/var/backups/grow-central')
RELATIVE = 'app/provisioning/broker_service.py'
UNITS = ('grow-central-provisioning.service', 'mosquitto.service')


def run(*args, **kwargs):
    subprocess.run(args, check=True, **kwargs)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    if not args.check_only and os.geteuid()!=0:
        raise SystemExit('Mit sudo python3 ausführen.')
    with tempfile.TemporaryDirectory(prefix='gc-tls-fix-') as temporary:
        staged=Path(temporary)/'broker_service.py'
        url='https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/'+SOURCE+'/'+RELATIVE
        with urllib.request.urlopen(url,timeout=25) as response:data=response.read(1024*1024+1)
        if len(data)>1024*1024 or hashlib.sha256(data).hexdigest()!=EXPECTED:
            raise RuntimeError('Download-Prüfsumme stimmt nicht.')
        staged.write_bytes(data)
        py_compile.compile(str(staged),doraise=True)
        if args.check_only:
            print('Gepinnter Download, SHA256 und Syntax geprüft; keine Installation geändert.')
            return
        if (ROOT/'BUILD').read_text().strip()!='369':
            raise RuntimeError('Hotfix ist für Build 369 vorgesehen.')
        target=ROOT/RELATIVE
        if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest() not in (BASE_HASH,EXPECTED):
            raise RuntimeError('Lokale Broker-Codeänderung erkannt; nicht überschrieben.')
        for name in ['ca.crt','ca.key','server.crt','server.key']:
            if not (CERTS/name).is_file():raise RuntimeError('Broker-Zertifikat fehlt: '+name)
        ca_hash=hashlib.sha256((CERTS/'ca.crt').read_bytes()).hexdigest()
        BACKUPS.mkdir(parents=True,exist_ok=True)
        backup=Path(tempfile.mkdtemp(prefix='mqtt-ip-san-',dir=BACKUPS))
        shutil.copy2(target,backup/'broker_service.py')
        for name in ['server.crt','server.key']:shutil.copy2(CERTS/name,backup/name)
        print('Sicherung:',backup,flush=True)
        try:
            shutil.copyfile(staged,target)
            target.chmod(0o644)
            run(str(ROOT/'.venv/bin/python'),'-c',
                'from app.provisioning.broker_service import certificates, local_hosts; certificates(local_hosts())',cwd=ROOT)
            if hashlib.sha256((CERTS/'ca.crt').read_bytes()).hexdigest()!=ca_hash:
                raise RuntimeError('CA unerwartet geändert; Abbruch.')
            run('openssl','verify','-CAfile',str(CERTS/'ca.crt'),str(CERTS/'server.crt'))
            run('systemctl','restart',*UNITS)
            for unit in UNITS:run('systemctl','is-active',unit)
        except BaseException:
            shutil.copy2(backup/'broker_service.py',target)
            for name in ['server.crt','server.key']:shutil.copy2(backup/name,CERTS/name)
            subprocess.run(['systemctl','restart',*UNITS],check=False)
            raise
        print('TLS-HOTFIX AKTIV: CA unverändert; Zertifikatsprüfung bleibt aktiv; kein Sensor-Flash nötig.')
        print('Sensor bis zu 60 Sekunden für Wiederverbindung geben. Danach vorhandene Verbindung in GC prüfen.')


if __name__=='__main__':main()
