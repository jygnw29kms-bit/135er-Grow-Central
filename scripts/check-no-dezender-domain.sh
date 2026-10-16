#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
from pathlib import Path
import re, subprocess, sys
host = 'dezender' + '.de'
pattern = re.compile(re.escape(host), re.I)
paths = subprocess.check_output(['git','ls-files','-z']).decode().split('\0')
failed=False
for name in paths:
    if not name:
        continue
    path=Path(name)
    if not path.is_file():
        continue
    data=path.read_bytes()
    if b'\0' in data:
        continue
    text=data.decode('utf-8',errors='replace')
    for number,line in enumerate(text.splitlines(),1):
        if pattern.search(line):
            print(f'{name}:{number}: legacy Grow Central domain reference')
            failed=True
if failed:
    print('ERROR: Replace legacy Grow Central addresses with canonical grow-central.de.',file=sys.stderr)
    sys.exit(1)
print('Domain guard passed: no legacy domain references remain in tracked Grow-Central files.')
PY
