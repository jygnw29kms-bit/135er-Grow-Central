"""Beta 1.0 operator scope contract: private single tent, secure Cloud, current brand."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATES = json.loads((ROOT / "docs/BETA1_RELEASE_GATES.json").read_text(encoding="utf-8"))
FREEZE = (ROOT / "docs/BETA1_FINAL_SCOPE_AND_FREEZE_2026-11-16.md").read_text(encoding="utf-8")
LOCAL = (ROOT / "web/gc-final.html").read_text(encoding="utf-8")
CLOUD = (ROOT / "cloud/portal/cloud-master.html").read_text(encoding="utf-8")


def test_private_single_tent_does_not_disable_secure_cloud_access():
    scope = GATES["scope_freeze"]
    assert scope["operator_model"] == "private_single_tent"
    assert scope["local_offline_control_required"] is True
    assert scope["secure_cloud_pwa_required"] is True
    assert scope["users_are_scoped_to_same_tent"] is True
    assert scope["new_features_allowed"] is False


def test_known_failure_count_and_release_block():
    scope = GATES["scope_freeze"]
    checks = scope["manual_gui_acceptance"]
    assert sum(checks[k] for k in ("ok", "failed", "not_tested")) == checks["total_checks"]
    assert checks["total_checks"] == 110
    assert GATES["status"] == "blocked"
    assert GATES["mandatory_gates"]
    assert all(g["manual_acceptance_required"] for g in GATES["mandatory_gates"])


def test_new_branding_is_same_on_local_and_cloud():
    for document in (LOCAL, CLOUD):
        assert 'gc-sidebar-brand-title' in document
        assert 'gc-sidebar-brand-subtitle' in document
        assert 'ENVIRONMENT CONTROL SYSTEM' in document
        assert 'gc-sidebar-brand-symbol' in document
    assert "135er-Grow Central" in FREEZE
