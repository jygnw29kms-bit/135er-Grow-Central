"""Room-member onboarding and strictly scoped guest API.

Member cookies never authenticate the appliance owner endpoints. Guests can
access only /api/v1/room-members/... under the separate middleware exception.
Invitation tokens are single-use, SHA256-at-rest and expired automatically.
"""
from __future__ import annotations

import hashlib
import secrets
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, SecretStr

from app.gui_auth import authenticated, hash_password, verify_password, _cookie_secure
from app.room_permissions import allowed, ASSIGNABLE, permission_matrix
from app.room_sharing import _load, _save, _require_owner, _room_exists

router = APIRouter(prefix="/api/v1/room-members", tags=["room-members"])
MEMBER_COOKIE = "gc_room_member"
MEMBER_SESSION_SECONDS = 12 * 3600
MAX_MEMBERS = 50


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _member_from_request(request: Request, store: dict) -> dict | None:
    token = request.cookies.get(MEMBER_COOKIE, "")
    if not token or len(token) < 32:
        return None
    session = store.get("sessions", {}).get(_hash(token))
    if not isinstance(session, dict) or session.get("expires_at", 0) <= time.time():
        return None
    return next((member for member in store["members"]
                 if member["id"] == session.get("member_id") and member.get("status") == "active"), None)


def member_authenticated(request: Request) -> bool:
    return _member_from_request(request, _load()) is not None


def _require_room_access(request: Request, room_id: str, permission: str) -> dict:
    if authenticated(request):
        return {"role": "owner", "room_id": room_id}
    member = _member_from_request(request, _load())
    if member is None or member.get("room_id") != room_id or not allowed(member.get("role", ""), permission):
        raise HTTPException(403, "No permission for this room action")
    return member


class AcceptBody(BaseModel):
    invite_token: str = Field(min_length=30, max_length=200)
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: SecretStr


class MemberLogin(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: SecretStr


def redeem(data: dict, body: AcceptBody, *, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    token_digest = _hash(body.invite_token)
    invite = next((r for r in data["invitations"]
                   if secrets.compare_digest(r.get("token_hash", ""), token_digest)
                   and r.get("status") == "pending"), None)
    if invite is None or invite.get("expires_at", 0) <= now:
        raise HTTPException(400, "Invalid or expired invitation")
    if not _room_exists(invite["room_id"]):
        raise HTTPException(404, "Room not found")
    if len(data["members"]) >= MAX_MEMBERS:
        raise HTTPException(409, "Maximum room members reached")
    if any(m.get("username", "").casefold() == body.username.casefold() for m in data["members"]):
        raise HTTPException(409, "Username already assigned")
    try:
        verifier = hash_password(body.password.get_secret_value())
    except ValueError as exc:
        raise HTTPException(422, "Password needs at least 12 characters") from exc
    account = {
        "id": "member_" + secrets.token_hex(12),
        "username": body.username,
        "password_hash": verifier,
        "room_id": invite["room_id"],
        "role": invite["role"],
        "status": "active",
        "joined_at": now,
    }
    invite["status"], invite["used_at"] = "used", now
    data["members"].append(account)
    return account


def _start_session(data: dict, member: dict, response: Response, request: Request) -> None:
    token = secrets.token_urlsafe(32)
    data.setdefault("sessions", {})[_hash(token)] = {
        "member_id": member["id"], "expires_at": time.time() + MEMBER_SESSION_SECONDS,
    }
    response.set_cookie(MEMBER_COOKIE, token, max_age=MEMBER_SESSION_SECONDS,
                        httponly=True, secure=_cookie_secure(request),
                        samesite="strict", path="/")


@router.post("/accept")
async def accept(body: AcceptBody, request: Request, response: Response):
    data = _load()
    member = redeem(data, body)
    _start_session(data, member, response, request)
    _save(data)
    return {"ok": True, "room_id": member["room_id"], "role": member["role"],
            "username": member["username"], "redirect": "/join"}


@router.post("/login")
async def login(body: MemberLogin, request: Request, response: Response):
    data = _load()
    member = next((m for m in data["members"]
                   if m.get("username", "").casefold() == body.username.casefold()
                   and m.get("status") == "active"), None)
    if member is None or not verify_password(body.password.get_secret_value(), member["password_hash"]):
        # Do not reveal whether a username exists.
        raise HTTPException(401, "Invalid login")
    _start_session(data, member, response, request)
    _save(data)
    return {"ok": True, "room_id": member["room_id"], "role": member["role"]}


@router.get("/status")
async def status(request: Request):
    member = _member_from_request(request, _load())
    return {"authenticated": member is not None,
            "room_id": member["room_id"] if member else None,
            "role": member["role"] if member else None,
            "permissions": sorted(permission_matrix().get(member["role"], [])) if member else []}


@router.post("/logout")
async def logout(request: Request, response: Response):
    data = _load()
    token = request.cookies.get(MEMBER_COOKIE, "")
    if token:
        data.setdefault("sessions", {}).pop(_hash(token), None)
        _save(data)
    response.delete_cookie(MEMBER_COOKIE, path="/")
    return {"ok": True}


@router.get("/room/{room_id}")
async def member_room(room_id: str, request: Request):
    _require_room_access(request, room_id, "room.view")
    from app.rooms import load_state
    data = load_state()
    room = next((r for r in data["rooms"] if r["id"] == room_id), None)
    if room is None:
        raise HTTPException(404, "Room not found")
    plants = [{"id": p.get("id"), "name": p.get("name"), "phase": p.get("phase")}
              for p in data["plants"] if p.get("room_id") == room_id]
    return {"room": room, "plants": plants}


@router.get("/room/{room_id}/journal")
async def member_journal(room_id: str, request: Request):
    _require_room_access(request, room_id, "journal.view")
    from app.rooms import load_state
    return {"entries": [r for r in load_state()["room_journal"] if r.get("room_id") == room_id]}


@router.post("/room/{room_id}/journal")
async def member_add_journal(room_id: str, body: dict, request: Request):
    _require_room_access(request, room_id, "journal.write")
    from app.rooms import JournalEntry, add_room_journal
    try:
        validated = JournalEntry.model_validate(body)
    except Exception as exc:
        raise HTTPException(422, "Invalid room journal entry") from exc
    return await add_room_journal(room_id, validated)



@router.get("/room/{room_id}/alerts")
async def member_alerts(room_id: str, request: Request):
    _require_room_access(request, room_id, "alerts.view")
    from app.room_notifications import _load as load_alerts
    data = load_alerts()
    return {"room_id": room_id, "events": [
        e for e in data["events"] if e.get("room_id") == room_id
    ][-100:]}


@router.get("/room/{room_id}/automation")
async def member_automation(room_id: str, request: Request):
    _require_room_access(request, room_id, "automation.view")
    from app.room_control_plans import _load as load_plans, RoomControlPlan
    return {"room_id": room_id,
            "plan": load_plans().get(room_id, RoomControlPlan().model_dump()),
            "execution": "simulation_only_not_armed"}


@router.post("/room/{room_id}/invitations")
async def member_invite(room_id: str, request: Request, body: dict):
    """Allow a room admin to invite only Growers or Observers in that room.

    Owner invitation management remains on its original owner-only endpoint.
    Delegated invites cannot grant permissions beyond the inviter's role.
    """
    actor = _require_room_access(request, room_id, "members.invite")
    from app.room_sharing import InviteCreate, issue_invitation
    from pydantic import ValidationError
    try:
        invitation = InviteCreate.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(422, "Invalid invitation details") from exc
    if not allowed(actor["role"], "members.invite"):
        raise HTTPException(403, "Invitations are not permitted")
    return issue_invitation(room_id, invitation, inviter_role=actor["role"])


@router.get("/room/{room_id}/role")
async def member_role(room_id: str, request: Request):
    account = _require_room_access(request, room_id, "room.view")
    return {"role": account["role"], "permissions": sorted(permission_matrix()[account["role"]])}


@router.get("/owner/{room_id}/members")
async def owner_members(room_id: str, request: Request, _=Depends(_require_owner)):
    if not _room_exists(room_id):
        raise HTTPException(404, "Room not found")
    return {"members": [
        {k: v for k, v in m.items() if k not in {"password_hash"}}
        for m in _load()["members"] if m.get("room_id") == room_id]}


@router.delete("/owner/{room_id}/members/{member_id}")
async def owner_revoke_member(room_id: str, member_id: str, request: Request, _=Depends(_require_owner)):
    data = _load()
    member = next((m for m in data["members"] if m["room_id"] == room_id and m["id"] == member_id), None)
    if member is None:
        raise HTTPException(404, "Member not found")
    member["status"] = "revoked"
    data["sessions"] = {key: val for key, val in data.get("sessions", {}).items()
                        if val.get("member_id") != member_id}
    _save(data)
    return {"ok": True}


# Public onboarding is intentionally separate from the owner-only Final Master.
# The member cookie never grants access to /ui or any unscoped appliance API.
join_router = APIRouter()


@join_router.get("/join", response_class=HTMLResponse)
async def join_page():
    return HTMLResponse("""<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#071411">
<title>Grow Central · Raumfreigabe</title>
<style>
*{box-sizing:border-box}body{margin:0;padding:20px;background:#071411;color:#d9e9e4;font:16px system-ui,Arial,sans-serif}
main{max-width:580px;margin:30px auto}header{padding:22px 0;border-bottom:1px solid #2a4941}
h1{font-size:1.7rem;font-weight:650}section{padding:20px;border:1px solid #385750;border-radius:16px;background:#12201f;margin-top:18px}
label{display:block;margin:14px 0 4px}input,textarea{display:block;width:100%;background:#0b1717;color:#fff;border:1px solid #587169;padding:12px;border-radius:8px;font:inherit}
button{background:#5cdfa7;border:0;border-radius:8px;padding:12px 18px;margin-top:14px;color:#071411;font-weight:700;cursor:pointer}
button.secondary{background:#263c38;color:#d9e9e4}
small{color:#9bb2a9}#error{color:#ff9d9d;min-height:24px}#content{white-space:pre-wrap}
</style></head><body><main>
<header><h1>Grow Central · Raumfreigabe</h1><p>Dein Zugang gilt nur für den freigegebenen Raum.</p></header>
<section id="invite"><h2>Einladung annehmen</h2><p>Vergib einen eigenen Benutzernamen und ein sicheres Passwort.</p>
<form id="accept"><label>Benutzername<input id="username" autocomplete="username" required minlength="3" maxlength="64"></label>
<label>Passwort<input id="password" type="password" autocomplete="new-password" required minlength="12"></label>
<button>Einladung annehmen</button></form></section>
<section id="login"><h2>Bereits Mitglied?</h2>
<form id="loginForm"><label>Benutzername<input id="loginName" autocomplete="username"></label>
<label>Passwort<input id="loginPass" type="password" autocomplete="current-password"></label>
<button class="secondary">Anmelden</button></form></section>
<section id="room" hidden><h2 id="roomName">Raum</h2><small id="myRole"></small>
<p id="content"></p><button class="secondary" id="logout">Abmelden</button></section>
<p id="error" role="alert"></p><small>Nur sichere Freigaben. Keine zusätzlichen Adminrechte durch den Einladungslink.</small>
</main><script>
const $=id=>document.getElementById(id);
const token=new URLSearchParams(location.hash.slice(1)).get('invite');
if(!token)$('invite').hidden=true;
history.replaceState(null,'',location.pathname);
async function call(path,data){const r=await fetch('/api/v1/room-members/'+path,{method:data?'POST':'GET',headers:{'Content-Type':'application/json'},body:data?JSON.stringify(data):undefined,credentials:'same-origin'});const v=await r.json().catch(()=>({}));if(!r.ok)throw Error(v.detail||'Fehler '+r.status);return v}
async function refresh(){const me=await call('status');if(!me.authenticated)return;
$('invite').hidden=true;$('login').hidden=true;$('room').hidden=false;
$('myRole').textContent='Rolle: '+me.role;
const d=await call('room/'+encodeURIComponent(me.room_id));
$('roomName').textContent=d.room.name;
$('content').textContent='Pflanzen: '+(d.plants.map(p=>p.name+' ('+p.phase+')').join(', ')||'Keine');
}
function failed(e){$('error').textContent=e.message}
$('accept').onsubmit=async e=>{e.preventDefault();try{await call('accept',{invite_token:token,username:$('username').value,password:$('password').value});await refresh()}catch(err){failed(err)}};
$('loginForm').onsubmit=async e=>{e.preventDefault();try{await call('login',{username:$('loginName').value,password:$('loginPass').value});await refresh()}catch(err){failed(err)}};
$('logout').onclick=async()=>{try{await call('logout',{});location.reload()}catch(err){failed(err)}};
refresh().catch(failed);
</script></body></html>""")


class MemberRoleChange(BaseModel):
    role: str = Field(pattern=r"^(admin|grower|observer)$")


@router.patch("/owner/{room_id}/members/{member_id}")
async def owner_change_role(room_id: str, member_id: str, body: MemberRoleChange,
                            request: Request, _=Depends(_require_owner)):
    data = _load()
    member = next((m for m in data["members"]
                   if m["room_id"] == room_id and m["id"] == member_id
                   and m.get("status") == "active"), None)
    if member is None:
        raise HTTPException(404, "Member not found")
    if body.role not in ASSIGNABLE:
        raise HTTPException(422, "Cannot assign this role")
    member["role"] = body.role
    _save(data)
    return {"ok": True, "member_id": member_id, "role": body.role}
