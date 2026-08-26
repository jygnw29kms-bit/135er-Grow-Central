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

# Harden the real boot/reboot test against systemd-machined registration races.
# The appliance itself is still required to boot twice and expose both HTTP paths.
old_boot = '''          check_boot() {
            local phase="$1"
            sudo systemd-nspawn --quiet --boot --register=yes --machine="$MACHINE" --directory="$ROOT" --private-network &
            local nspawn_pid=$!
            local ready=0
            for attempt in $(seq 1 90); do
              if sudo systemd-run --quiet --wait --pipe --machine="$MACHINE" /bin/bash -c \\
                "/usr/bin/curl --fail --silent --max-time 3 http://127.0.0.1:8080/api/health | /usr/bin/jq -e '.ok == true and .version == \\\"0.7.5\\\"' >/dev/null && /usr/bin/curl --fail --silent --max-time 3 http://127.0.0.1/api/health | /usr/bin/jq -e '.ok == true and .version == \\\"0.7.5\\\"' >/dev/null" >/dev/null 2>&1; then
                ready=1
                break
              fi
              sleep 1
            done
            if [ "$ready" -ne 1 ]; then
              sudo systemd-run --quiet --wait --pipe --machine="$MACHINE" /usr/bin/systemctl status 135er-grow-central.service --no-pager -l || true
              sudo systemd-run --quiet --wait --pipe --machine="$MACHINE" /usr/bin/journalctl -u 135er-grow-central.service -b --no-pager -n 200 || true
              echo "Image ${phase} boot did not expose healthy application and simple-login endpoints on ports 8080 and 80" >&2
              exit 1
            fi
            sudo systemd-run --quiet --wait --pipe --machine="$MACHINE" /usr/bin/systemctl is-active 135er-grow-central.service
            sudo systemd-run --quiet --wait --pipe --machine="$MACHINE" /usr/bin/systemctl is-active grow-central-http.socket
            sudo machinectl poweroff "$MACHINE"
            wait "$nspawn_pid" || true
          }
'''
new_boot = '''          sudo systemctl start systemd-machined.service
          sudo systemctl is-active --quiet systemd-machined.service

          wait_machine_gone() {
            for attempt in $(seq 1 30); do
              if ! sudo machinectl show "$MACHINE" >/dev/null 2>&1; then
                return 0
              fi
              sleep 1
            done
            sudo machinectl status "$MACHINE" --no-pager || true
            return 1
          }

          check_boot() {
            local phase="$1"
            local nspawn_log="/tmp/${MACHINE}-${phase}.log"
            local registered=0
            local ready=0

            sudo machinectl terminate "$MACHINE" >/dev/null 2>&1 || true
            wait_machine_gone || true
            : >"$nspawn_log"
            sudo systemd-nspawn --boot --register=yes --machine="$MACHINE" --directory="$ROOT" --private-network >"$nspawn_log" 2>&1 &
            local nspawn_pid=$!

            for attempt in $(seq 1 45); do
              if ! kill -0 "$nspawn_pid" 2>/dev/null; then
                echo "systemd-nspawn exited before ${phase} registered" >&2
                cat "$nspawn_log" >&2 || true
                wait "$nspawn_pid" || true
                return 1
              fi
              state="$(sudo machinectl show "$MACHINE" -p State --value 2>/dev/null || true)"
              if [ "$state" = running ]; then
                registered=1
                break
              fi
              sleep 1
            done
            if [ "$registered" -ne 1 ]; then
              echo "Image ${phase} boot never registered as a running nspawn machine" >&2
              cat "$nspawn_log" >&2 || true
              sudo machinectl list --no-pager || true
              sudo machinectl terminate "$MACHINE" >/dev/null 2>&1 || true
              wait "$nspawn_pid" || true
              return 1
            fi

            for attempt in $(seq 1 120); do
              if sudo systemd-run --quiet --wait --pipe --machine="$MACHINE" /bin/bash -c \\
                "/usr/bin/curl --fail --silent --max-time 3 http://127.0.0.1:8080/api/health | /usr/bin/jq -e '.ok == true and .version == \\\"0.7.5\\\"' >/dev/null && /usr/bin/curl --fail --silent --max-time 3 http://127.0.0.1/api/health | /usr/bin/jq -e '.ok == true and .version == \\\"0.7.5\\\"' >/dev/null" >/dev/null 2>&1; then
                ready=1
                break
              fi
              sleep 1
            done
            if [ "$ready" -ne 1 ]; then
              sudo systemd-run --quiet --wait --pipe --machine="$MACHINE" /usr/bin/systemctl status 135er-grow-central.service grow-central-http.socket grow-central-setup-ap.service grow-central-firstboot-firewall.service --no-pager -l || true
              sudo systemd-run --quiet --wait --pipe --machine="$MACHINE" /usr/bin/journalctl -b --no-pager -n 300 || true
              cat "$nspawn_log" >&2 || true
              echo "Image ${phase} boot did not expose healthy application endpoints on ports 8080 and 80" >&2
              sudo machinectl terminate "$MACHINE" >/dev/null 2>&1 || true
              wait "$nspawn_pid" || true
              return 1
            fi

            sudo systemd-run --quiet --wait --pipe --machine="$MACHINE" /usr/bin/systemctl is-active 135er-grow-central.service
            sudo systemd-run --quiet --wait --pipe --machine="$MACHINE" /usr/bin/systemctl is-active grow-central-http.socket
            sudo machinectl poweroff "$MACHINE"
            wait "$nspawn_pid" || true
            wait_machine_gone
          }
'''
if old_boot in text:
    text = text.replace(old_boot, new_boot, 1)
elif 'wait_machine_gone()' not in text:
    raise SystemExit('boot smoke-test anchor missing')

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
    "wait_machine_gone()",
    "systemctl start systemd-machined.service",
    "machinectl show \"$MACHINE\" -p State --value",
)
missing = [item for item in required if item not in text]
if missing:
    raise SystemExit('image hardening incomplete: ' + ', '.join(missing))

path.write_text(text, encoding='utf-8')
print('changed=' + str(text != original).lower())
