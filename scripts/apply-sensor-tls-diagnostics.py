#!/usr/bin/env python3
"""Stage verified firmware 0.4.1 for the existing USB wizard; never flash here."""
import argparse
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
import zipfile

SOURCE = 'eaa44594c5b36b5415c20452d5affb5e9244457e'
BASE = 'https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/' + SOURCE + '/'
ZIP_SHA = 'c99662d6574d8ef7d044ea761e1cbbce98446375980f68863505d3b34d08c264'
CODE_SHA = 'fe6f9bb6df11df13c230eb72688db3cd98edbf8afa21495334673714e5b1404e'
PREVIOUS_SHA = 'f55ddd216fa64ff14cce8d0cdb72f4aefb30b758e0413dcb5f722cf86e119924'
OLD_SHA = '21858aae7267e737425b8ff76495bb325304b20a8ae6fcc26f8a3cbd9f0b2580'
UNIT = '135er-grow-central.service'
ROOT = Path('/opt/135er-grow-central')
BACKUPS = Path('/var/backups/grow-central')
FILES = {'bootloader.bin': 0, 'partitions.bin': 0x8000,
         'boot_app0.bin': 0xe000, 'firmware.bin': 0x10000}


def download(relative, target, digest):
    with urllib.request.urlopen(BASE + relative, timeout=30) as response:
        data = response.read(3 * 1024 * 1024 + 1)
    if len(data) > 3 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != digest:
        raise RuntimeError('Download-Prüfsumme stimmt nicht: ' + relative)
    target.write_bytes(data)


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if not args.check_only and os.geteuid() != 0:
        raise SystemExit('Mit sudo python3 ausführen.')
    with tempfile.TemporaryDirectory(prefix='gc-fw041-') as temporary:
        temp = Path(temporary)
        archive, code, dist = temp/'firmware.zip', temp/'usb.py', temp/'dist'
        download('firmware/gc-soil-node/candidates/gc-soil-node-0.4.1-test.zip', archive, ZIP_SHA)
        download('app/provisioning/usb.py', code, CODE_SHA)
        py_compile.compile(str(code), doraise=True)
        dist.mkdir()
        with zipfile.ZipFile(archive) as z:
            if len(z.namelist()) != 5 or set(z.namelist()) != set(FILES) | {'manifest.json'}:
                raise RuntimeError('Unerwarteter Archivinhalt.')
            if sum(info.file_size for info in z.infolist()) > 3 * 1024 * 1024:
                raise RuntimeError('Firmwarearchiv zu groß.')
            z.extractall(dist)
        manifest = json.loads((dist/'manifest.json').read_text())
        if (manifest['version'], manifest['chip'], manifest['model']) != ('0.4.1', 'esp32c3', 'GC-SOIL-XIAO-C3-HW390'):
            raise RuntimeError('Falsches Firmwareziel.')
        if set(manifest['files']) != set(FILES):
            raise RuntimeError('Unvollständiges Firmwaremanifest.')
        for name, offset in FILES.items():
            item = manifest['files'][name]
            if item['offset'] != offset or hashlib.sha256((dist/name).read_bytes()).hexdigest() != item['sha256']:
                raise RuntimeError('Firmwareprüfung fehlgeschlagen: ' + name)
        if args.check_only:
            print('Download, SHA256, Archiv, Firmwaremanifest und Python-Syntax geprüft.')
            return
        if (ROOT/'BUILD').read_text().strip() != '369':
            raise RuntimeError('Installer ist für Build 369 vorgesehen.')
        target = ROOT/'app/provisioning/usb.py'
        destination = ROOT/'firmware/gc-soil-node/dist'
        if target.is_symlink() or destination.is_symlink() or any((destination/name).is_symlink() for name in [*FILES, 'manifest.json']):
            raise RuntimeError('Unerwarteter symbolischer Link.')
        if hashlib.sha256(target.read_bytes()).hexdigest() not in (OLD_SHA, PREVIOUS_SHA, CODE_SHA):
            raise RuntimeError('USB-Code unbekannt. Zuerst den bisherigen UI-Hotfix installieren; lokale Änderungen werden nicht überschrieben.')
        backups = BACKUPS
        backups.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix='sensor-041-', dir=backups))
        run('systemctl', 'stop', UNIT)
        copied_code = copied_dist = changed = False
        try:
            shutil.copy2(target, backup/'usb.py')
            copied_code = True
            if destination.exists():
                shutil.copytree(destination, backup/'dist')
                copied_dist = True
            changed = True
            shutil.copyfile(code, target)
            target.chmod(0o644)
            destination.mkdir(parents=True, exist_ok=True)
            for src in dist.iterdir():
                shutil.copyfile(src, destination/src.name)
                (destination/src.name).chmod(0o644)
            run(str(ROOT/'.venv/bin/python'), '-c',
                'from app.provisioning.usb import firmware_files; print("Firmware geprüft:", firmware_files())')
            run('systemctl', 'start', UNIT)
            for attempt in range(20):
                try:
                    with urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=2) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(1)
            else:
                raise RuntimeError('GC startet nach Update nicht gesund.')
        except BaseException:
            if changed and copied_code:
                subprocess.run(['systemctl', 'stop', UNIT], check=False)
                shutil.copy2(backup/'usb.py', target)
                if copied_dist:
                    shutil.rmtree(destination)
                    shutil.copytree(backup/'dist', destination)
                else:
                    for name in [*FILES, 'manifest.json']:
                        (destination/name).unlink(missing_ok=True)
            subprocess.run(['systemctl', 'restart', UNIT], check=False)
            raise
        print('Firmware 0.4.1 bereitgestellt. Sicherung:', backup)
        print('Sensor wurde NICHT geflasht. Bei bereits installierter 0.4.1 ist kein Flash nötig.')
        print('Bei älterer Sensorfirmware: GC neu laden und im USB-Assistenten Firmware installieren.')
        print('NVS/Identität/WLAN/Zugang bleiben beim Flash erhalten; kein erase_flash verwenden.')


if __name__ == '__main__':
    main()
