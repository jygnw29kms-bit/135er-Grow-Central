from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_maintenance_helper_is_strictly_whitelisted():
    helper = (ROOT / "image-builder/firstboot/growcentral-maint").read_text(encoding="utf-8")
    assert 'case "${1:-}" in' in helper
    for action in ("status)", "restart-core)", "restart-cloud)", "restart-homekit)", "restart-all)"):
        assert action in helper
    assert "eval " not in helper
    assert 'systemctl restart "$1"' not in helper
    assert "${2" not in helper


def test_image_installs_only_explicit_nopasswd_actions():
    workflow = (ROOT / ".github/workflows/build-pi3-image.yml").read_text(encoding="utf-8")
    expected = (
        "status",
        "restart-core",
        "restart-cloud",
        "restart-homekit",
        "restart-all",
    )
    for action in expected:
        assert f"GrowCentral ALL=(root) NOPASSWD: /usr/local/sbin/growcentral-maint {action}" in workflow
    assert "NOPASSWD: ALL" not in workflow
    assert "growcentral-maint *" not in workflow
    assert "visudo -cf /etc/sudoers.d/growcentral-maint" in workflow
