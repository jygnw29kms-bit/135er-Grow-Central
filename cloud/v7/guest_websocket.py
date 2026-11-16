"""Isolated Cloud room-guest WebSocket.

Must be installed *together with* a matching device-response diversion hook.
Guest sockets never join the device-wide owner client_sockets broadcast set.
Each message checks the live Cloud account token and current room membership.
"""
from __future__ import annotations

import asyncio
import json
import secrets
from dataclasses import dataclass
from typing import Callable

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import Engine

from guest_remote_acl import GuestRequestBroker, GuestRequestDenied
try:
    # Production Cloud backend installs the account module under this name.
    from cloud_room_membership import get_membership_role
except ImportError:
    # Standalone repository regression tests use the source module name.
    from room_membership import get_membership_role


@dataclass
class GuestSocketState:
    socket: WebSocket
    device_id: str
    room_id: str
    account_id: str
    access_token: str


class CloudGuestRemote:
    def __init__(
        self, *,
        engine: Engine,
        account_from_access: Callable[[str], str],
        device_sockets: dict,
        socket_lock: asyncio.Lock,
    ):
        self.engine = engine
        self.account_from_access = account_from_access
        self.device_sockets = device_sockets
        self.socket_lock = socket_lock
        self.sessions: dict[str, GuestSocketState] = {}
        self.broker = GuestRequestBroker()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        session_id = ""
        try:
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=10)
                if len(raw) > 8192:
                    await ws.close(code=4400)
                    return
                message = json.loads(raw)
                if not isinstance(message, dict) or message.get("type") != "auth":
                    await ws.close(code=4401)
                    return
                token = message.get("access_token")
                device_id = message.get("device_id")
                room_id = message.get("room_id")
                if not all(isinstance(v, str) for v in (token, device_id, room_id)):
                    await ws.close(code=4401)
                    return
                if len(token) > 2048 or len(device_id) > 64 or len(room_id) > 120:
                    await ws.close(code=4400)
                    return
                account_id = self.account_from_access(token)
                role = get_membership_role(self.engine, device_id, room_id, account_id)
                if role is None:
                    await ws.close(code=4403)
                    return
            except (HTTPException, ValueError, KeyError, TypeError, asyncio.TimeoutError):
                await ws.close(code=4401)
                return
            # The guest session has its own registry and is NEVER inserted
            # into the owner's device-wide broadcast_to_clients() registry.
            session_id = secrets.token_urlsafe(24)
            state = GuestSocketState(ws, device_id, room_id, account_id, token)
            self.sessions[session_id] = state
            await ws.send_json({"type": "auth_ok", "device_id": device_id,
                                "room_id": room_id, "role": role,
                                "guest_scoped": True})
            while True:
                raw = await ws.receive_text()
                if len(raw) > 16384:
                    await ws.close(code=4400)
                    return
                # Revalidate active access token and room membership on EVERY
                # request. Role edits and revoked accounts take effect immediately.
                try:
                    verified_account = self.account_from_access(state.access_token)
                except Exception:
                    await ws.close(code=4401)
                    return
                if verified_account != state.account_id:
                    await ws.close(code=4401)
                    return
                role = get_membership_role(self.engine, device_id, room_id, account_id)
                if role is None:
                    await ws.close(code=4403)
                    return
                try:
                    data = json.loads(raw)
                    prepared = self.broker.prepare(
                        data, session_id=session_id, room_id=room_id, role=role
                    )
                except (ValueError, TypeError, GuestRequestDenied):
                    await ws.send_json({"type": "error", "error": "guest_action_denied"})
                    continue
                async with self.socket_lock:
                    device_socket = self.device_sockets.get(device_id)
                if device_socket is None:
                    self.broker.revoke_session(session_id)
                    await ws.send_json({"type": "error", "error": "device_offline"})
                    continue
                try:
                    await device_socket.send_text(json.dumps(prepared, separators=(",", ":")))
                except Exception:
                    self.broker.revoke_session(session_id)
                    await ws.send_json({"type": "error", "error": "device_transport_failed"})
        except WebSocketDisconnect:
            pass
        finally:
            if session_id:
                self.sessions.pop(session_id, None)
                self.broker.revoke_session(session_id)

    async def dispatch_device_result(self, device_id: str, raw: str) -> bool:
        """Consume a guest reply. Return True to prevent owner-wide broadcast."""
        try:
            message = json.loads(raw)
        except (ValueError, TypeError):
            return False
        if not isinstance(message, dict):
            return False
        internal_id = message.get("request_id")
        # Late or revoked guest replies must NEVER fall back to the owner's
        # device-wide broadcast, even after their pending request expires.
        if self.broker.is_guest_request_id(internal_id) and not self.broker.has_pending(internal_id):
            return True
        if not self.broker.has_pending(internal_id):
            return False
        # Reserved guest IDs are *always* suppressed from the general
        # owner response broadcast, including mismatched/revoked replies.
        delivery = self.broker.route_reply(message)
        if not delivery:
            return True
        session_id, reply = delivery
        state = self.sessions.get(session_id)
        if state is None or state.device_id != device_id:
            return True
        try:
            if self.account_from_access(state.access_token) != state.account_id:
                return True
            if get_membership_role(
                self.engine, state.device_id, state.room_id, state.account_id
            ) is None:
                return True
            await state.socket.send_json(reply)
        except Exception:
            # Never fall back to owner/client broadcasting.
            self.sessions.pop(session_id, None)
            self.broker.revoke_session(session_id)
        return True


def install_guest_remote(
    app: FastAPI,
    *,
    engine: Engine,
    account_from_access: Callable[[str], str],
    device_sockets: dict,
    socket_lock: asyncio.Lock,
) -> CloudGuestRemote:
    remote = CloudGuestRemote(
        engine=engine, account_from_access=account_from_access,
        device_sockets=device_sockets, socket_lock=socket_lock,
    )

    @app.websocket("/api/v2/collaboration/remote/connect")
    async def guest_room_connect(ws: WebSocket):
        await remote.connect(ws)

    return remote
