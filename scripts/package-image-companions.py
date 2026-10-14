#!/usr/bin/env python3
"""Attach installable companions from the same source and firmware as the image."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

root = Path(__file__).resolve().parents[1]
out = Path(sys.argv[1]) if len(sys.argv) > 1 else root
out.mkdir(parents=True, exist_ok=True)
source_sha = os.getenv('SOURCE_SHA') or os.getenv('GITHUB_SHA') or subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip()
component = root / 'integrations/home_assistant/custom_components/grow_central'
ha_version = json.loads((component / 'manifest.json').read_text())['version']
with zipfile.ZipFile(out / f'grow-central-homeassistant-{ha_version}.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for p in sorted(component.rglob('*')):
        if p.is_file() and p.suffix in {'.py', '.json'}:
            z.write(p, 'custom_components/grow_central/' + str(p.relative_to(component)))
    z.write(root / 'docs/de/HOME_ASSISTANT.md', 'INSTALLATION.md')
    z.writestr('SOURCE.txt', source_sha + '\n')
firmware = root / 'firmware/gc-soil-node/dist'
manifest = json.loads((firmware / 'manifest.json').read_text())
with zipfile.ZipFile(out / f'gc-soil-node-{manifest["version"]}-test.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for name in [*manifest['files'], 'manifest.json']:
        z.write(firmware / name, name)
    z.write(root / 'docs/de/USB_SENSOR_SETUP.md', 'USB_SENSOR_SETUP.md')
    z.writestr('SOURCE.txt', source_sha + '\n')
    z.writestr('README.txt', 'XIAO ESP32-C3 ONLY; not a Raspberry Pi image.\nRecommended: use the GC USB setup wizard on the matching test image.\nManual flash offsets are in manifest.json. Preserve NVS; never erase_flash for an update.\nHardware testing remains pending; BLE provisioning is not implemented.\n')
checks = []
for p in out.glob('*.zip'):
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
    checks.append(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name)
(out / 'COMPANIONS.sha256').write_text('\n'.join(checks) + '\n')
