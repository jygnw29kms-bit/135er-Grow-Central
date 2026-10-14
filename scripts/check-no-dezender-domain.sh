#!/usr/bin/env bash
set -euo pipefail

# Independent projects and their server operations do not use the Grow domain.
# Explicit exceptions do not exempt Grow runtime, website or documentation.
python3 - <<'PY'
from pathlib import Path
import re
import subprocess
import sys

host = 'dezender' + '.de'
pattern = re.compile(re.escape(host), re.I)
independent_workflows = {
    'deploy-dyson-v11-bms-apt-sftp.yml', 'deploy-godseye-web.yml',
    'deploy-touran.yml', 'check-touran-logs.yml', 'diagnose-dezender-access.yml',
    'diagnose-erp-staging-host.yml', 'lightmeter-apps.yml',
}
external_downloads = {
    'https://' + host + '/godseye/grow-light-meter/GrowLightMeter-iOS-Sideload.zip',
    'https://' + host + '/godseye/grow-light-meter/GrowLightMeter-Android.zip',
}
paths = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
failed = False
for name in paths:
    if not name or name.startswith(('standalone/', 'touran-deploy/')):
        continue
    path = Path(name)
    if path.parts[:2] == ('.github', 'workflows') and path.name in independent_workflows:
        continue
    if not path.is_file(): continue
    data = path.read_bytes()
    if b'\0' in data: continue
    text = data.decode('utf-8', errors='replace')
    for number, line in enumerate(text.splitlines(), 1):
        # Only the two existing external app downloads are permitted on the website.
        checked = line
        if name == 'website/index.html':
            for url in external_downloads:
                checked = checked.replace('href="' + url + '"', 'href="external-app-download"')
        if pattern.search(checked):
            print(f'{name}:{number}: legacy Grow domain reference')
            failed = True
if failed:
    print('ERROR: Replace legacy Grow Central addresses with the canonical Grow domain.', file=sys.stderr)
    sys.exit(1)
print('Domain guard passed: Grow addresses are canonical; independent projects remain separate.')
PY
