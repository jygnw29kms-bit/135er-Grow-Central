"""Cloud app integration must be additive, idempotent and fail closed."""
import importlib.util
import sys
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "scripts/patch_cloud_room_membership.py"
spec = importlib.util.spec_from_file_location("gc_cloud_member_patch", PATH)
patcher = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = patcher
spec.loader.exec_module(patcher)

SAMPLE = """
from fastapi import FastAPI
from sqlalchemy import create_engine
PUBLIC_URL='https://example.test'
engine = create_engine('sqlite:///:memory:')
app = FastAPI()
def init_db():
    pass
init_db()
def account_from_access(t):
    return t
def get_device_for_account(d,a):
    return {'id':d}
"""


def test_patch_adds_only_endpoint_registration():
    updated = patcher.patch_app(SAMPLE)
    assert "GROW_CENTRAL_BETA_ROOM_COLLABORATION_V1" in updated
    assert "app.include_router(_gc_room_router(" in updated
    assert "guest_remote_acl" not in updated
    assert "device_connect" not in updated
    assert updated.startswith(SAMPLE.strip())


def test_second_patch_is_idempotent():
    one = patcher.patch_app(SAMPLE)
    assert patcher.patch_app(one) == one


def test_unexpected_cloud_app_fails_without_patch():
    with pytest.raises(ValueError, match="Unexpected Cloud app structure"):
        patcher.patch_app("app = FastAPI()")


def test_modified_existing_integration_requires_review():
    changed = patcher.patch_app(SAMPLE).replace(
        "public_url=PUBLIC_URL,", "public_url='https://evil.invalid',")
    with pytest.raises(ValueError, match="manual review"):
        patcher.patch_app(changed)
