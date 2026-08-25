#!/usr/bin/env python3
from pathlib import Path

path = Path('.github/workflows/build-pi3-image.yml')
text = path.read_text(encoding='utf-8')
original = text

# Rebuild when cloud-link/deploy code changes.
anchor = "      - 'shared/**'\n"
if "      - 'local/**'" not in text:
    text = text.replace(anchor, anchor + "      - 'local/**'\n      - 'cloud/**'\n      - 'deploy/**'\n", 1)

# Kiosk stack must already be in the image; first boot may have no uplink.
base_packages = 'ffmpeg v4l-utils wtmpdb psmisc plymouth plymouth-themes locales keyboard-configuration console-setup tzdata'
gui_packages = base_packages + ' xserver-xorg-core xserver-xorg-input-libinput xinit openbox chromium unclutter x11-xserver-utils'
if 'xserver-xorg-core xserver-xorg-input-libinput xinit openbox chromium' not in text:
    if base_packages not in text:
        raise SystemExit('base package anchor missing')
    text = text.replace(base_packages, gui_packages, 1)

# Explicit credential-free closed-test link; remote commands stay disabled.
old_env = '''          GC_LOCAL_API_TOKEN=test
          GC_CLOUD_TOKEN=test
          GC_REMOTE_COMMANDS=false
          GC_CLOUD_ENABLED=false
          GC_SMARTHOME_ENABLED=true
'''
new_env = '''          GC_LOCAL_API_TOKEN=test
          GC_REMOTE_COMMANDS=false
          GC_CLOUD_ENABLED=true
          GC_CLOUD_TEST_MODE=true
          GC_CLOUD_URL=https://135ercloud.dezender.de
          GC_CLOUD_TOKEN=
          GC_DIAGNOSTIC_SYNC_SECONDS=120
          GC_DIAGNOSTIC_BUNDLE_SECONDS=300
          GC_SMARTHOME_ENABLED=true
'''
if old_env in text:
    text = text.replace(old_env, new_env, 1)
elif 'GC_CLOUD_TEST_MODE=true' not in text:
    raise SystemExit('closed-test environment anchor missing')

# Install the outbound cloud-link service with no cloud token. Local API token is
# only loopback auth between two processes on the same Pi; it is not Pi<->server auth.
smoke = '''          install -o root -g root -m 0755 \\
            /opt/135er-grow-central/image-builder/firstboot/cloud-smoke-test.sh \\
            /usr/local/sbin/grow-central-cloud-smoke-test
'''
cloud_install = smoke + '''
          cat >/opt/135er-grow-central/local/cloud_link/.env <<'EOF'
          GC_CLOUD_ENABLED=true
          GC_CLOUD_TEST_MODE=true
          GC_CLOUD_URL=https://135ercloud.dezender.de
          GC_CLOUD_TOKEN=
          GC_SITE_ID=closed-test
          GC_SYNC_SECONDS=30
          GC_DIAGNOSTIC_SYNC_SECONDS=120
          GC_DIAGNOSTIC_BUNDLE_SECONDS=300
          GC_REMOTE_COMMANDS=false
          GC_LOCAL_API=http://127.0.0.1:8080
          GC_LOCAL_API_TOKEN=test
          EOF
          chown root:growcentral /opt/135er-grow-central/local/cloud_link/.env
          chmod 0640 /opt/135er-grow-central/local/cloud_link/.env
          install -o root -g root -m 0644 \\
            /opt/135er-grow-central/deploy/systemd/135er-grow-central-cloud-link.service \\
            /etc/systemd/system/135er-grow-central-cloud-link.service
'''
if 'GC_SITE_ID=closed-test' not in text:
    if smoke not in text:
        raise SystemExit('cloud smoke install anchor missing')
    text = text.replace(smoke, cloud_install, 1)

# Enable cloud link anywhere the appliance services are enabled.
text = text.replace(
    'grow-central-support-bundle.path 135er-grow-central.service grow-central-http.socket grow-central-healthcheck.timer',
    'grow-central-support-bundle.path 135er-grow-central.service 135er-grow-central-cloud-link.service grow-central-http.socket grow-central-healthcheck.timer',
)

# Number the Actions artifact itself, not only the image file inside it.
text = text.replace(
    '          name: 135er-Grow-Central-RPi3Plus-Universal-Image\n',
    '          name: 135er-Grow-Central-RPi3Plus-Universal-Image-build-${{ github.run_number }}\n',
)

# Strengthen the image verification block where the old closed-test assertions live.
old_checks = '''          grep -qx 'GC_CLOUD_ENABLED=false' /opt/135er-grow-central/.env
          grep -qx 'GC_REMOTE_COMMANDS=false' /opt/135er-grow-central/.env
'''
new_checks = '''          grep -qx 'GC_CLOUD_ENABLED=true' /opt/135er-grow-central/.env
          grep -qx 'GC_CLOUD_TEST_MODE=true' /opt/135er-grow-central/.env
          grep -qx 'GC_CLOUD_TOKEN=' /opt/135er-grow-central/.env
          grep -qx 'GC_REMOTE_COMMANDS=false' /opt/135er-grow-central/.env
          test "$(systemctl is-enabled 135er-grow-central-cloud-link.service)" = enabled
          grep -qx 'GC_CLOUD_TEST_MODE=true' /opt/135er-grow-central/local/cloud_link/.env
          grep -qx 'GC_CLOUD_TOKEN=' /opt/135er-grow-central/local/cloud_link/.env
          grep -qx 'GC_REMOTE_COMMANDS=false' /opt/135er-grow-central/local/cloud_link/.env
          command -v startx
          command -v chromium
          command -v openbox
          test -x /opt/135er-grow-central/image-builder/firstboot/display-kiosk.sh
          /usr/bin/python3 -m py_compile /opt/135er-grow-central/app/entrypoint.py
          /usr/bin/python3 -m py_compile /opt/135er-grow-central/app/diagnostics.py
          /usr/bin/python3 -m py_compile /opt/135er-grow-central/local/cloud_link/agent.py
'''
if old_checks in text:
    text = text.replace(old_checks, new_checks, 1)

# Closed-test image must never install or enable remote-maintenance activation.
for forbidden in (
    'systemctl enable grow-central-remote-maintenance',
    'systemctl enable --now grow-central-remote-maintenance',
):
    if forbidden in text:
        raise SystemExit(f'forbidden remote-maintenance activation in image workflow: {forbidden}')

required = (
    "GC_CLOUD_TEST_MODE=true",
    "GC_CLOUD_TOKEN=",
    "GC_REMOTE_COMMANDS=false",
    "135er-grow-central-cloud-link.service",
    "xserver-xorg-core",
    "chromium",
    "135er-Grow-Central-RPi3Plus-Universal-Image-build-${{ github.run_number }}",
)
missing = [item for item in required if item not in text]
if missing:
    raise SystemExit('image hardening incomplete: ' + ', '.join(missing))

path.write_text(text, encoding='utf-8')
print('changed=' + str(text != original).lower())
