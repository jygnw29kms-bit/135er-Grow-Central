"""Cloud Push preflight must be read-only and fail closed on missing dependencies."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "gc_cloud_push_readiness", ROOT / "scripts/check_cloud_push_readiness.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_preflight_reports_missing_backend_modules_without_leaking_secrets(tmp_path):
    app = tmp_path / "app.py"
    app.write_text("app = FastAPI()\n# GROW_CENTRAL_BETA_ROOM_COLLABORATION_V1\n")
    result = mod.check(app, Path(sys.executable), tmp_path / "gc-push-worker.js")
    assert result["cloud_collaboration_router"] is True
    assert result["cloud_push_router"] is False
    assert result["cloud_push_module"] is False
    assert result["push_service_worker"] is False
    assert "GC_CLOUD_VAPID_PRIVATE_KEY" not in str(result)
    assert "token" not in str(result)


def test_preflight_detects_installed_route_markers(tmp_path):
    app = tmp_path / "app.py"
    app.write_text("# GROW_CENTRAL_BETA_ROOM_COLLABORATION_V1\n"
                   "# GROW_CENTRAL_BETA_ACCOUNT_PUSH_V1\n")
    (tmp_path / "cloud_push.py").touch()
    (tmp_path / "cloud_room_membership.py").touch()
    result = mod.check(app, Path(sys.executable))
    assert result["cloud_push_router"]
    assert result["cloud_push_module"]
    assert result["cloud_room_membership_module"]
