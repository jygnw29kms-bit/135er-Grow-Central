#!/usr/bin/env python3
"""Update only the two room display assets on Build 369, with backups."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request

ROOT = Path('/opt/135er-grow-central')
SOURCE = 'ddd34b34bf6ca8a9f0c36bf3308ad1627bf92306'
FILES = {
    'console.html': ('9e2d61fada670c532b0fb5a92ca91da4a2f0793c7509f1767af154e57478f9ec', '2b00b55222a86a0541a4bbad368e12498a2f4fd3d0bd57dc432ce593c5a8309c'),
    'console.js': ('75ca6e87347ec1e35c081025a5dc8c2e2825a80fd0ea635ddec1e415bc25b7ce', 'd01929c25806bad257c92c202bd3813c819f9bbbc385aaace24bfc69ce06a95a'),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if not args.check_only and os.geteuid() != 0:
        raise SystemExit('Mit sudo python3 ausführen.')
    with tempfile.TemporaryDirectory(prefix='gc-soil-display-') as temporary:
        staged = Path(temporary)
        for name, (_, expected) in FILES.items():
            url = f'https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/{SOURCE}/web/{name}'
            with urllib.request.urlopen(url, timeout=25) as response:
                data = response.read(1024 * 1024 + 1)
            if len(data) > 1024 * 1024 or hashlib.sha256(data).hexdigest() != expected:
                raise RuntimeError('Download-Prüfsumme falsch: ' + name)
            (staged/name).write_bytes(data)
        if args.check_only:
            print('Beide UI-Dateien heruntergeladen und SHA256 geprüft.')
            return
        if (ROOT/'BUILD').read_text().strip() != '369':
            raise RuntimeError('UI-Hotfix ist für Build 369 vorgesehen.')
        for name, hashes in FILES.items():
            target = ROOT/'web'/name
            if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest() not in hashes:
                raise RuntimeError('Unbekannte lokale UI-Änderung; nicht überschrieben: ' + name)
        backups = Path('/var/backups/grow-central')
        backups.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix='soil-display-', dir=backups))
        for name in FILES:
            shutil.copy2(ROOT/'web'/name, backup/name)
        try:
            for name in FILES:
                target = ROOT/'web'/name
                shutil.copyfile(staged/name, target)
                target.chmod(0o644)
        except BaseException:
            for name in FILES:
                shutil.copy2(backup/name, ROOT/'web'/name)
            raise
        print('Bodenfeuchte-Anzeige installiert. Sicherung:', backup)
        print('Browser mit Strg+F5 neu laden. Raum wählen > Sensordaten > MESSWERTE JETZT.')
        print('Kein Dienstneustart, kein Sensorflash, keine Zugangsdaten geändert.')


if __name__ == '__main__':
    main()
