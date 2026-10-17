"""GrowCentral product edition and capability model.

Local growing control stays available in every edition. Paid editions only add
online/comfort capabilities. Production entitlements must be enforced by the
cloud service; the local test override exists solely for validation on a test Pi.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/edition", tags=["edition"])

EDITIONS = ("FREE", "LINK", "PRO")
LEGACY_ALIASES = {"BASIC": "FREE", "PLUS": "LINK", "INTERNAL": "PRO"}
TEST_STATE_FILE = Path(os.getenv("GC_EDITION_TEST_STATE_FILE", "/var/lib/135er-grow-central/edition-test.json"))

LOCAL_FEATURES = {
    "local_control", "devices", "sensors", "local_automation", "local_history",
    "pwa", "local_api", "home_assistant", "homekit", "local_camera",
    "local_backup", "language_packs",
}
LINK_FEATURES = LOCAL_FEATURES | {
    "remote_access", "push_alerts", "email_alerts", "offsite_backup",
    "guided_restore", "cloud_history_12m", "cloud_offline_monitoring",
}
PRO_FEATURES = LINK_FEATURES | {
    "multi_site", "multi_user_rbac", "advanced_audit", "reports",
    "automated_exports", "extended_cloud_history", "pro_api",
}
FEATURE_MATRIX = {"FREE": LOCAL_FEATURES, "LINK": LINK_FEATURES, "PRO": PRO_FEATURES}


def _bool_env(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def normalize_edition(value: str | None) -> str:
    candidate = (value or "FREE").strip().upper()
    candidate = LEGACY_ALIASES.get(candidate, candidate)
    if candidate not in EDITIONS:
        return "FREE"
    return candidate


def test_mode_enabled() -> bool:
    return _bool_env("GC_EDITION_TEST_MODE", False)


def _read_test_override() -> str | None:
    if not test_mode_enabled():
        return None
    try:
        payload = json.loads(TEST_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    raw = str(payload.get("edition", "")).strip().upper()
    raw = LEGACY_ALIASES.get(raw, raw)
    return raw if raw in EDITIONS else None


def current_edition() -> tuple[str, str]:
    override = _read_test_override()
    if override:
        return override, "test_override"
    configured = normalize_edition(os.getenv("GC_EDITION", "FREE"))
    return configured, "environment" if os.getenv("GC_EDITION") else "default"


def edition_payload() -> dict[str, object]:
    edition, source = current_edition()
    features = FEATURE_MATRIX[edition]
    return {
        "edition": edition,
        "source": source,
        "test_mode": test_mode_enabled(),
        "features": {name: name in features for name in sorted(PRO_FEATURES)},
        "local_core_unrestricted": True,
    }


def has_feature(name: str) -> bool:
    edition, _ = current_edition()
    return name in FEATURE_MATRIX[edition]


class TestEditionBody(BaseModel):
    edition: str


@router.get("")
async def get_edition():
    return edition_payload()


@router.post("/test")
async def set_test_edition(body: TestEditionBody):
    if not test_mode_enabled():
        raise HTTPException(status_code=404, detail="Edition test mode is disabled")
    requested = body.edition.strip().upper()
    requested = LEGACY_ALIASES.get(requested, requested)
    if requested not in EDITIONS:
        raise HTTPException(status_code=422, detail="Unknown edition")
    TEST_STATE_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    tmp = TEST_STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"edition": requested}, separators=(",", ":")) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o640)
    os.replace(tmp, TEST_STATE_FILE)
    return edition_payload()


@router.delete("/test")
async def clear_test_edition():
    if not test_mode_enabled():
        raise HTTPException(status_code=404, detail="Edition test mode is disabled")
    TEST_STATE_FILE.unlink(missing_ok=True)
    return edition_payload()
