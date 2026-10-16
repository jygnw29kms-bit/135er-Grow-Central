from pathlib import Path

WORKFLOW = Path('.github/workflows/build-pi3-image.yml').read_text(encoding='utf-8')


def test_image_builder_repairs_and_verifies_sudo_integrity():
    assert 'chown root:root /usr/bin/sudo /etc/sudo.conf /etc/sudoers' in WORKFLOW
    assert 'chmod 4755 /usr/bin/sudo' in WORKFLOW
    assert 'chmod 0644 /etc/sudo.conf' in WORKFLOW
    assert 'chmod 0440 /etc/sudoers' in WORKFLOW
    assert WORKFLOW.count('visudo -c') >= 3


def test_published_pristine_image_rechecks_sudo_integrity():
    assert '''test "$(sudo stat -c '%U:%G:%a' "$ROOT/usr/bin/sudo")" = root:root:4755''' in WORKFLOW
    assert '''test "$(sudo stat -c '%U:%G:%a' "$ROOT/etc/sudo.conf")" = root:root:644''' in WORKFLOW
    assert '''test "$(sudo stat -c '%U:%G:%a' "$ROOT/etc/sudoers")" = root:root:440''' in WORKFLOW
    assert '''sudo chroot "$ROOT" visudo -c''' in WORKFLOW


def test_release_notes_match_current_sensor_commissioning():
    assert 'bundled firmware 0.5.2' in WORKFLOW
    assert 'FRESH_SUBSTRATE_CC' in WORKFLOW
    assert 'BLE remains a secure Recovery/Service path' in WORKFLOW
    assert 'firmware 0.4.1' not in WORKFLOW
    assert 'BLE credential provisioning is not implemented' not in WORKFLOW
