from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_maintenance_helper_is_strictly_whitelisted():
    helper = (ROOT / "image-builder/firstboot/growcentral-maint").read_text(encoding="utf-8")
    assert 'case "${1:-}" in' in helper
    for action in ("status)", "restart-core)", "restart-cloud)", "restart-homekit)", "restart-all)", "apply-staged)"):
        assert action in helper
    assert "eval " not in helper
    assert 'systemctl restart "$1"' not in helper
    assert "${2" not in helper
    assert "safe_relative_path" in helper
    assert 'app/*|local/cloud_link/*|web/*|shared/*' in helper
    assert 'find "$payload" -type l' in helper
    assert '"requirements.txt"' in helper
    assert "sha256sum -c ../SHA256SUMS" in helper
    assert "MAX_FILES=500" in helper
    assert "50 * 1024 * 1024" in helper


def test_image_installs_only_explicit_nopasswd_actions():
    workflow = (ROOT / ".github/workflows/build-pi3-image.yml").read_text(encoding="utf-8")
    for action in ("status", "restart-core", "restart-cloud", "restart-homekit", "restart-all"):
        assert f"GrowCentral ALL=(root) NOPASSWD: /usr/local/sbin/growcentral-maint {action}" in workflow
    assert "growcentral ALL=(root) NOPASSWD: /usr/local/sbin/growcentral-maint status" in workflow
    assert "growcentral ALL=(root) NOPASSWD: /usr/local/sbin/growcentral-maint restart" not in workflow
    assert "gcmaint ALL=(root) NOPASSWD: /usr/local/sbin/growcentral-maint apply-staged" in workflow
    assert "NOPASSWD: ALL" not in workflow
    assert "growcentral-maint *" not in workflow
    assert "visudo -cf /etc/sudoers.d/growcentral-maint" in workflow
    assert "ssh-keygen -A >/dev/null" in workflow
    assert "rm -f /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub" in workflow
    assert "! find /etc/ssh -maxdepth 1 -type f -name 'ssh_host_*_key*'" in workflow


def test_test_maintenance_access_is_build_scoped_and_key_only():
    workflow = (ROOT / ".github/workflows/build-pi3-image.yml").read_text(encoding="utf-8")
    assert "github.event_name == 'workflow_dispatch'" in workflow
    assert 'enable_test_maintenance:' in workflow
    assert 'inputs.enable_test_maintenance == true' in workflow
    assert "startsWith(github.ref_name, 'image/firstboot-')" not in workflow
    assert "secrets.GC_TEST_PI_MAINTENANCE_PUBKEY" in workflow
    assert "AuthenticationMethods publickey" in workflow
    assert "PasswordAuthentication no" in workflow
    assert "AllowTcpForwarding no" in workflow
    assert "192.168.0.0/16 to any port 22 proto tcp" in workflow
    assert "\n          ufw allow 22/tcp\n" not in workflow
