#!/usr/bin/env python3
"""Package a locally built XIAO-C3 firmware; no downloaded unverified binaries."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

root = Path(__file__).resolve().parents[1]
build = root / 'firmware/gc-soil-node/.pio/build/seeed_xiao_esp32c3'
out = Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'firmware/gc-soil-node/dist'
out.mkdir(parents=True, exist_ok=True)
core = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home() / '.platformio'
files = {'bootloader.bin': (0, build / 'bootloader.bin'), 'partitions.bin': (0x8000, build / 'partitions.bin'),
         'boot_app0.bin': (0xe000, core / 'packages/framework-arduinoespressif32/tools/partitions/boot_app0.bin'),
         'firmware.bin': (0x10000, build / 'firmware.bin')}
version = re.search(r'FW_VERSION\[\] = "([0-9.]+)"', (root / 'firmware/gc-soil-node/src/main.cpp').read_text()).group(1)
manifest = {'version': version, 'chip': 'esp32c3', 'model': 'GC-SOIL-XIAO-C3-HW390', 'files': {}}
for name, (offset, source) in files.items():
    shutil.copyfile(source, out / name)
    manifest['files'][name] = {'offset': offset, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(f'Packaged {version} for XIAO ESP32-C3: {out}')
