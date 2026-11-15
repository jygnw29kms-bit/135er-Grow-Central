"""Fail-closed beta release gate. No manual signoff can be inferred from tests."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_beta1_release.py"
spec = importlib.util.spec_from_file_location("beta_release_gate", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_beta_gates_block_unaccepted_release():
    import json
    data = json.loads((SCRIPT.parents[1] / "docs/BETA1_RELEASE_GATES.json").read_text())
    ready, blockers = mod.evaluate(data)
    assert not ready
    assert blockers
    assert any("cloud_guest_identity" in x for x in blockers)
    assert any("web_push" in x for x in blockers)


def test_gate_does_not_accept_missing_evidence_or_approval():
    data = {"status": "ready", "mandatory_gates": [
        {"id": "test", "status": "accepted", "manual_acceptance_required": True}
    ]}
    ready, blockers = mod.evaluate(data)
    assert not ready
    assert any("evidence" in x for x in blockers)
    assert any("operator acceptance" in x for x in blockers)


def test_all_acceptance_evidence_can_release():
    data = {"status": "ready", "mandatory_gates": [
        {"id": "gui", "status": "accepted", "evidence": "reviewed test run",
         "manual_acceptance_required": True, "accepted_by": "operator"},
        {"id": "backup", "status": "accepted", "evidence": "recovery test",
         "manual_acceptance_required": False},
    ]}
    ready, blockers = mod.evaluate(data)
    assert ready and not blockers
