"""Guest WebSocket patch must not loosen existing owner authentication."""
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/patch_cloud_guest_websocket.py"
spec = importlib.util.spec_from_file_location("gc_guest_patch", SCRIPT)
patch = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = patch
spec.loader.exec_module(patch)

SOURCE = '''
import asyncio
from fastapi import FastAPI, WebSocket
device_sockets: dict[str, WebSocket] = {}
socket_lock = asyncio.Lock()
app = FastAPI()
def account_from_access(raw):
    return raw
@app.websocket("/api/v2/remote/connect")
async def remote_connect(ws: WebSocket):
    return
async def device_connect():
    while True:
        payload = await ws.receive_text()
        await broadcast_to_clients(device_id, payload)
# GROW_CENTRAL_BETA_ROOM_COLLABORATION_V1
'''


def test_patch_adds_guest_response_diversion_without_changing_owner_login():
    patched = patch.patch_app(SOURCE)
    assert patched.count("await broadcast_to_clients(device_id, payload)") == 1
    assert "if await _gc_guest_remote.dispatch_device_result(device_id, payload):" in patched
    assert '@app.websocket("/api/v2/remote/connect")' in patched
    assert "app.include_router" not in patched
    assert "install_guest_remote" in patched


def test_guest_patch_is_idempotent_and_fails_closed():
    once = patch.patch_app(SOURCE)
    assert patch.patch_app(once) == once
    with pytest.raises(ValueError):
        patch.patch_app(once.replace("continue", "pass"))
    with pytest.raises(ValueError):
        patch.patch_app("app = FastAPI()")


def test_patch_requires_previous_account_membership_integration():
    with pytest.raises(ValueError, match="ROOM_COLLABORATION"):
        patch.patch_app(SOURCE.replace(
            "# GROW_CENTRAL_BETA_ROOM_COLLABORATION_V1", "# old feature"
        ))
