#!/usr/bin/env python3
from pathlib import Path

path = Path('.github/workflows/build-pi3-image.yml')
text = path.read_text(encoding='utf-8')
original = text

# Keep the appliance strictly headless. The web UI is served by uvicorn/systemd;
# no local browser, X server, window manager or kiosk helper belongs in the image.
kiosk_packages = (
    ' xserver-xorg-core xserver-xorg-input-libinput xinit openbox chromium '
    'unclutter x11-xserver-utils'
)
text = text.replace(kiosk_packages, '')

# Remove legacy positive kiosk assertions from Customize image verification.
for line in (
    '          command -v startx\n',
    '          command -v chromium\n',
    '          command -v openbox\n',
    '          test -x /opt/135er-grow-central/image-builder/firstboot/display-kiosk.sh\n',
):
    text = text.replace(line, '')

# Add negative guarantees so a future patch cannot silently reintroduce the kiosk.
anchor = "          grep -qx 'GC_REMOTE_COMMANDS=false' /opt/135er-grow-central/local/cloud_link/.env\n"
headless_checks = '''          for forbidden_cmd in startx chromium openbox; do
            if command -v "$forbidden_cmd" >/dev/null 2>&1; then
              echo "Unexpected kiosk command in headless image: $forbidden_cmd" >&2
              exit 1
            fi
          done
          for forbidden_pkg in xserver-xorg-core xserver-xorg-input-libinput xinit openbox chromium unclutter x11-xserver-utils; do
            if dpkg-query -W -f='${Status}' "$forbidden_pkg" 2>/dev/null | grep -q 'install ok installed'; then
              echo "Unexpected kiosk package in headless image: $forbidden_pkg" >&2
              exit 1
            fi
          done
          test ! -e /opt/135er-grow-central/image-builder/firstboot/display-kiosk.sh
          test ! -e /opt/135er-grow-central/image-builder/firstboot/display-setup.sh
'''
if headless_checks not in text:
    if anchor not in text:
        raise SystemExit('headless verification anchor missing')
    text = text.replace(anchor, anchor + headless_checks, 1)

# The workflow must still contain the core local-first appliance guarantees.
required = (
    'GC_CLOUD_TEST_MODE=true',
    'GC_CLOUD_TOKEN=',
    'GC_REMOTE_COMMANDS=false',
    '135er-grow-central-cloud-link.service',
    'grow-central-headless-firstboot.service',
    'grow-central-http.socket',
    'grow-central-healthcheck.timer',
    'NetworkManager.service',
    'avahi-daemon.service',
    'ffmpeg',
    'v4l-utils',
    'plymouth',
    '135er-Grow-Central-RPi3Plus-Universal-Image-build-${{ github.run_number }}',
)
missing = [item for item in required if item not in text]
if missing:
    raise SystemExit('image appliance contract incomplete: ' + ', '.join(missing))

# Kiosk/X11 material is forbidden in active workflow code after this patch.
for forbidden in (
    'xserver-xorg-core',
    'xserver-xorg-input-libinput',
    ' xinit ',
    ' openbox ',
    ' chromium ',
    ' unclutter ',
    'x11-xserver-utils',
    'command -v startx',
    'command -v chromium',
    'command -v openbox',
    'test -x /opt/135er-grow-central/image-builder/firstboot/display-kiosk.sh',
):
    # Negative verification lines intentionally mention package/command names.
    # Reject only old positive install/assertion forms that remain outside them.
    if forbidden.startswith('command -v ') and f'          {forbidden}\n' in text:
        raise SystemExit(f'legacy kiosk assertion still present: {forbidden}')
    if forbidden.startswith('test -x ') and f'          {forbidden}\n' in text:
        raise SystemExit('legacy kiosk script assertion still present')

install_line = next((line for line in text.splitlines() if 'apt-get install -y --no-install-recommends' in line), '')
for pkg in ('xserver-xorg-core', 'xserver-xorg-input-libinput', 'xinit', 'openbox', 'chromium', 'unclutter', 'x11-xserver-utils'):
    if pkg in install_line.split():
        raise SystemExit(f'kiosk package still installed: {pkg}')

path.write_text(text, encoding='utf-8')
print('changed=' + str(text != original).lower())
