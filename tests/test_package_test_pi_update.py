from pathlib import Path

import importlib.util

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("package_test_pi_update", ROOT / "scripts/package-test-pi-update.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def test_safe_hot_update_paths():
    assert MOD.safe_path("app/entrypoint.py")
    assert MOD.safe_path("local/cloud_link/agent_v2.py")
    assert MOD.safe_path("web/menu-live.js")
    assert MOD.safe_path("shared/contracts.py")
    for bad in (
        "/etc/shadow",
        "app/../.env",
        "app/.hidden.py",
        "scripts/install.sh",
        "local/cloud_link/run.sh",
        "local/cloud_link/requirements.txt",
        "web/evil.exe",
        "web\\menu-live.js",
    ):
        assert not MOD.safe_path(bad)


def test_packager_policy_matches_root_helper():
    helper = (ROOT / "image-builder/firstboot/growcentral-maint").read_text(encoding="utf-8")
    for prefix in ("app/*", "local/cloud_link/*", "web/*", "shared/*"):
        assert prefix in helper
    assert f"MAX_FILES={MOD.MAX_FILES}" in helper
    assert str(MOD.MAX_BYTES // (1024 * 1024)) + " * 1024 * 1024" in helper
