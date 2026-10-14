#!/usr/bin/env python3
"""Apply the tested sensor/support UI hotfix to stock Grow Central build 369."""
import argparse
import grp
import hashlib
import json
import os
from pathlib import Path
import py_compile
import shutil
import subprocess
import tempfile
import time
import urllib.request

SOURCE = '66c12a1502d701004aeadc2d7b5bd059e6e7dd89'
FILES = {'app/devices/gc_pairing.py': {'new': '6bbbbf36b7110aadee078e8533aced600d2349aa21b74b1215403c12a8c51b02', 'base': 'c2752b3594ed39181fcc794fd48fa165e51338b97d04ff2a1e5de0c1bffe21ec'}, 'app/diagnostics.py': {'new': '9e75dbb123070f8a9950e2e469eee9d1405d063e2471e997c760a14a710453f3', 'base': '56f6696579a248d0af2defa19cc2a039e76b77d8168f3475418492307e6f2974'}, 'web/app.js': {'new': 'e1791d0e8cf2399dee53e93310e71fc93be40642fd42554e99ef879a603f71ac', 'base': 'b2b3db2811204e92af5bb343888de57f46d5aeab781d67786ebccffcc58730d2'}, 'web/sensor_pairing.js': {'new': '4f48074f628ed3c2de10de5de671883d42347087be50f130dde17b7b0831b56f', 'base': '7ed6de33da2821a45768e3d1c1341382f946728a0cd83007dfc373a492812548'}, 'web/usb_onboarding.js': {'new': 'e62924f9bf90969afd529709851f887cead035fa49d474135b36a5364c7ec1a1', 'base': '34f4c3dd6398c22822ba217e39797a410902d7a43041cb8757e8f15ccb9a48aa'}}
ROOT = Path('/opt/135er-grow-central')
UNIT = '135er-grow-central.service'
BACKUP_ROOT = Path('/var/backups/grow-central')


def run(*args):
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-only', action='store_true', help='Download, verify and compile only; do not change the installation')
    args = parser.parse_args()
    if not args.check_only and os.geteuid() != 0:
        raise SystemExit('Bitte mit sudo python3 ausführen.')
    with tempfile.TemporaryDirectory(prefix='gc-ui-hotfix-') as temporary:
        stage = Path(temporary)
        for name, hashes in FILES.items():
            url = 'https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/' + SOURCE + '/' + name
            with urllib.request.urlopen(url, timeout=25) as response:
                data = response.read(1024 * 1024 + 1)
            if len(data) > 1024 * 1024 or hashlib.sha256(data).hexdigest() != hashes['new']:
                raise RuntimeError('Prüfsumme/Dateigröße ungültig: ' + name)
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            if target.suffix == '.py': py_compile.compile(str(target), doraise=True)
        if args.check_only:
            print('Alle fünf Downloads, SHA256-Werte und Python-Syntax geprüft; Installation unverändert.')
            return
        if not (ROOT/'BUILD').is_file() or (ROOT/'BUILD').read_text().strip() != '369':
            raise RuntimeError('Dieser Hotfix ist ausschließlich für Build 369 vorgesehen.')
        all_current = True
        for name, hashes in FILES.items():
            path = ROOT/name
            if path.is_symlink() or not path.is_file(): raise RuntimeError('Installationsdatei fehlt/ist unerwartet verknüpft: ' + name)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest not in (hashes['base'], hashes['new']):
                raise RuntimeError('Lokale Änderung erkannt; nicht überschrieben: ' + name)
            all_current = all_current and digest == hashes['new']
        if all_current:
            print('Dieser UI-Hotfix ist bereits installiert.')
            return
        backup_root = BACKUP_ROOT
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix='ui-hotfix-', dir=backup_root))
        for name in FILES:
            saved = backup/name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/name, saved)
        (backup/'manifest.json').write_text(json.dumps({'source':SOURCE,'files':FILES},indent=2))
        gid = grp.getgrnam('growcentral').gr_gid
        print('Sicherung:', backup, flush=True)
        run('systemctl', 'stop', UNIT)
        try:
            for name in FILES:
                target = ROOT/name
                shutil.copyfile(stage/name, target)
                os.chown(target, 0, gid)
                target.chmod(0o644)
            run('systemctl', 'start', UNIT)
            healthy = False
            for _ in range(20):
                try:
                    with urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=2) as response:
                        healthy = json.loads(response.read(65536)).get('ok') is True
                    if healthy: break
                except (OSError, ValueError): pass
                time.sleep(1)
            if not healthy: raise RuntimeError('Grow Central wurde nach dem Update nicht gesund; Dateien werden zurückgesetzt.')
        except BaseException:
            subprocess.run(['systemctl','stop',UNIT],check=False)
            for name in FILES: shutil.copy2(backup/name,ROOT/name)
            subprocess.run(['systemctl','start',UNIT],check=False)
            raise
        print('HOTFIX AKTIV: USB-Sensor bleibt sichtbar; Aufnahme ohne Hex-Tippen; stabiler Supportdownload und Diagnose zum Kopieren.')
        print('Browser mit Strg+F5 neu laden. Sensor angeschlossen lassen; USB-Einrichtung fortsetzen.')
        print('Image-Build bleibt 369. Quellstand des Hotfix:',SOURCE)


if __name__ == '__main__': main()
