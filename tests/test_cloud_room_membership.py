"""Cloud account-bound room membership with strictly one-time invitations."""
import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

SCRIPT = Path(__file__).resolve().parents[1] / "cloud/v7/room_membership.py"
spec = importlib.util.spec_from_file_location("gc_cloud_room_membership", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

DEV = "device-001"
ROOM = "room_alpha"


def env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", future=True)
    with engine.begin() as db:
        db.execute(text("CREATE TABLE accounts(id TEXT PRIMARY KEY,status TEXT NOT NULL)"))
        db.execute(text("CREATE TABLE devices(id TEXT PRIMARY KEY,account_id TEXT,revoked_at INTEGER)"))
        for who in ("owner", "alice", "bob", "other"):
            db.execute(text("INSERT INTO accounts(id,status) VALUES(:id,'active')"), {"id": who})
        db.execute(text("INSERT INTO devices(id,account_id,revoked_at) VALUES(:id,'owner',NULL)"),
                   {"id": DEV})
    mod.ensure_schema(engine)
    mod.ensure_schema(engine)

    def check_device(device_id, user):
        if device_id != DEV or user != "owner":
            raise HTTPException(403, "Device not owned")
        with engine.connect() as db:
            live = db.execute(text("SELECT 1 FROM devices WHERE id=:d AND revoked_at IS NULL"),
                              {"d": device_id}).scalar()
        if not live:
            raise HTTPException(403, "Revoked device")

    app = FastAPI()
    app.include_router(mod.build_router(
        engine, account_from_access=lambda token: token
        if token in {"owner", "alice", "bob", "other"}
        else (_ for _ in ()).throw(HTTPException(401, "Invalid credentials")),
        get_device_for_account=check_device,
        public_url="https://135ercloud.grow-central.de",
        clock=lambda: 200000,
    ))
    return engine, TestClient(app)


def headers(who):
    return {"Authorization": "Bearer " + who}


def invitation(client, role="grower"):
    resp = client.post(
        f"/api/v2/collaboration/devices/{DEV}/rooms/{ROOM}/invitations",
        json={"role": role}, headers=headers("owner"))
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_owner_invites_registered_account_and_one_time_redeems(tmp_path):
    engine, client = env(tmp_path)
    created = invitation(client, role="grower")
    assert created["role"] == "grower"
    assert created["remote_access"] if "remote_access" in created else True
    assert created["share_url_once"].startswith("https://135ercloud.grow-central.de/#room-invite=")
    assert "token_once" in created
    with engine.connect() as db:
        stored = db.execute(text("SELECT token_hash FROM cloud_room_invitations")).scalar()
    assert stored != created["token_once"]
    assert len(stored) == 64
    body = {"invite_token": created["token_once"]}
    resp = client.post("/api/v2/collaboration/accept", json=body, headers=headers("alice"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["remote_access"] == "guest_scoped"
    assert mod.get_membership_role(engine, DEV, ROOM, "alice") == "grower"
    reused = client.post("/api/v2/collaboration/accept", json=body, headers=headers("bob"))
    assert reused.status_code == 400
    mine = client.get("/api/v2/collaboration/my-rooms", headers=headers("alice")).json()
    assert mine["memberships"] == [{"device_id": DEV, "room_id": ROOM, "role": "grower"}]
    other = client.get("/api/v2/collaboration/my-rooms", headers=headers("bob")).json()
    assert other["memberships"] == []


def test_non_owner_cannot_invite_or_view_or_revoke(tmp_path):
    engine, client = env(tmp_path)
    post = f"/api/v2/collaboration/devices/{DEV}/rooms/{ROOM}/invitations"
    assert client.post(post, json={"role": "admin"}, headers=headers("alice")).status_code == 403
    assert client.post(post, json={"role": "admin"}).status_code == 401
    member_route = f"/api/v2/collaboration/devices/{DEV}/rooms/{ROOM}/members"
    assert client.get(member_route, headers=headers("bob")).status_code == 403
    assert client.delete(member_route + "/alice", headers=headers("alice")).status_code == 403


def test_immediate_revocation_and_role_change(tmp_path):
    engine, client = env(tmp_path)
    created = invitation(client, role="observer")
    client.post("/api/v2/collaboration/accept",
                json={"invite_token": created["token_once"]}, headers=headers("alice"))
    assert mod.get_membership_role(engine, DEV, ROOM, "alice") == "observer"
    member_path = f"/api/v2/collaboration/devices/{DEV}/rooms/{ROOM}/members/alice"
    resp = client.patch(member_path, json={"role": "grower"}, headers=headers("owner"))
    assert resp.status_code == 200
    assert mod.get_membership_role(engine, DEV, ROOM, "alice") == "grower"
    assert client.patch(member_path, json={"role": "owner"},
                        headers=headers("owner")).status_code == 422
    resp = client.delete(member_path, headers=headers("owner"))
    assert resp.status_code == 200
    assert mod.get_membership_role(engine, DEV, ROOM, "alice") is None
    assert client.delete(member_path, headers=headers("owner")).status_code == 404


def test_device_revocation_immediately_blocks_membership(tmp_path):
    engine, client = env(tmp_path)
    created = invitation(client)
    accepted = client.post("/api/v2/collaboration/accept",
                           json={"invite_token": created["token_once"]}, headers=headers("alice"))
    assert accepted.status_code == 200
    with engine.begin() as db:
        db.execute(text("UPDATE devices SET revoked_at=123 WHERE id=:d"), {"d": DEV})
    assert mod.get_membership_role(engine, DEV, ROOM, "alice") is None
    assert client.get("/api/v2/collaboration/my-rooms",
                      headers=headers("alice")).json()["memberships"] == []


def test_malicious_room_name_and_owner_self_redeem_denied(tmp_path):
    _, client = env(tmp_path)
    invalid = client.post(f"/api/v2/collaboration/devices/{DEV}/rooms/../invitations",
                          json={"role": "grower"}, headers=headers("owner"))
    assert invalid.status_code in (404, 422)
    invalid = client.post(f"/api/v2/collaboration/devices/{DEV}/rooms/{ROOM}/invitations",
                          json={"role": "owner"}, headers=headers("owner"))
    assert invalid.status_code == 422
    created = invitation(client)
    self_redeem = client.post("/api/v2/collaboration/accept",
                              json={"invite_token": created["token_once"]}, headers=headers("owner"))
    assert self_redeem.status_code == 403


def test_owner_transfer_invalidates_prior_guest_memberships(tmp_path):
    engine, client = env(tmp_path)
    created = invitation(client, role="grower")
    assert client.post("/api/v2/collaboration/accept",
                       json={"invite_token": created["token_once"]},
                       headers=headers("alice")).status_code == 200
    assert mod.get_membership_role(engine, DEV, ROOM, "alice") == "grower"
    with engine.begin() as db:
        db.execute(text("UPDATE devices SET account_id='other' WHERE id=:d"),
                   {"d": DEV})
    assert mod.get_membership_role(engine, DEV, ROOM, "alice") is None
    assert client.get("/api/v2/collaboration/my-rooms",
                      headers=headers("alice")).json()["memberships"] == []


def test_disabled_original_owner_blocks_all_guest_access(tmp_path):
    engine, client = env(tmp_path)
    created = invitation(client, role="observer")
    response = client.post("/api/v2/collaboration/accept",
                           json={"invite_token": created["token_once"]},
                           headers=headers("alice"))
    assert response.status_code == 200
    with engine.begin() as db:
        db.execute(text("UPDATE accounts SET status='disabled' WHERE id='owner'"))
    assert mod.get_membership_role(engine, DEV, ROOM, "alice") is None
    assert client.get("/api/v2/collaboration/my-rooms",
                      headers=headers("alice")).json()["memberships"] == []


def test_disabled_guest_is_not_listed_in_owner_or_guest_membership_results(tmp_path):
    engine, client = env(tmp_path)
    created = invitation(client, role="observer")
    response = client.post("/api/v2/collaboration/accept",
                           json={"invite_token": created["token_once"]},
                           headers=headers("alice"))
    assert response.status_code == 200
    own = client.get(f"/api/v2/collaboration/devices/{DEV}/rooms/{ROOM}/members",
                     headers=headers("owner"))
    assert any(row["account_id"] == "alice" for row in own.json()["members"])
    with engine.begin() as db:
        db.execute(text("UPDATE accounts SET status='disabled' WHERE id='alice'"))
    # A still-valid access token must not make a disabled account visible or
    # allow a guest membership to be represented as active.
    mine = client.get("/api/v2/collaboration/my-rooms", headers=headers("alice"))
    assert mine.status_code == 200
    assert mine.json()["memberships"] == []
    roster = client.get(f"/api/v2/collaboration/devices/{DEV}/rooms/{ROOM}/members",
                        headers=headers("owner"))
    assert roster.status_code == 200
    assert all(row["account_id"] != "alice" for row in roster.json()["members"])
    assert mod.get_membership_role(engine, DEV, ROOM, "alice") is None


def test_join_response_reports_live_guest_transport_not_stale_disabled_state(tmp_path):
    _, client = env(tmp_path)
    created = invitation(client)
    assert created["acceptance_ui"] == "cloud_join_page"
    accepted = client.post("/api/v2/collaboration/accept",
                           json={"invite_token": created["token_once"]},
                           headers=headers("alice"))
    assert accepted.status_code == 200
    assert accepted.json()["remote_access"] == "guest_scoped"
    rooms = client.get("/api/v2/collaboration/my-rooms", headers=headers("alice"))
    assert rooms.json()["remote_access"] == "guest_scoped"


def test_owner_can_list_and_cancel_pending_room_invitations(tmp_path):
    engine, client = env(tmp_path)
    created = invitation(client, role="observer")
    token = created["token_once"]
    url = f"/api/v2/collaboration/devices/{DEV}/rooms/{ROOM}/invitations"
    listing = client.get(url, headers=headers("owner"))
    assert listing.status_code == 200
    rows = listing.json()["pending"]
    assert len(rows) == 1
    public_id = rows[0]["id"]
    assert public_id.startswith("invite_")
    assert rows[0]["role"] == "observer"
    # No redeemable secret, token hash, or token prefix in owner listings.
    assert token not in listing.text
    assert "token_hash" not in listing.text
    assert "token_once" not in listing.text
    assert client.get(url, headers=headers("alice")).status_code == 403
    assert client.delete(f"{url}/{public_id}", headers=headers("alice")).status_code == 403
    assert client.delete(f"{url}/../{public_id}", headers=headers("owner")).status_code in (404, 422)
    cancelled = client.delete(f"{url}/{public_id}", headers=headers("owner"))
    assert cancelled.status_code == 200
    assert cancelled.json()["revoked"] is True
    assert client.get(url, headers=headers("owner")).json()["pending"] == []
    cannot_redeem = client.post("/api/v2/collaboration/accept",
                                json={"invite_token": token}, headers=headers("bob"))
    assert cannot_redeem.status_code == 400
    assert client.delete(f"{url}/{public_id}", headers=headers("owner")).status_code == 404
    with engine.connect() as db:
        assert db.execute(text("SELECT revoked_at FROM cloud_room_invitations")).scalar() is not None


def test_redeemed_invitation_is_not_revokeable_and_wrong_room_is_isolated(tmp_path):
    _, client = env(tmp_path)
    created = invitation(client)
    url = f"/api/v2/collaboration/devices/{DEV}/rooms/{ROOM}/invitations"
    pending_id = client.get(url, headers=headers("owner")).json()["pending"][0]["id"]
    response = client.post("/api/v2/collaboration/accept",
                           json={"invite_token": created["token_once"]},
                           headers=headers("alice"))
    assert response.status_code == 200
    assert client.get(url, headers=headers("owner")).json()["pending"] == []
    assert client.delete(f"{url}/{pending_id}", headers=headers("owner")).status_code == 404

    another = invitation(client)
    pending = client.get(url, headers=headers("owner")).json()["pending"]
    assert len(pending) == 1
    other_room_url = f"/api/v2/collaboration/devices/{DEV}/rooms/room_unrelated/invitations"
    assert client.get(other_room_url, headers=headers("owner")).json()["pending"] == []
    assert client.delete(f"{other_room_url}/{pending[0]['id']}",
                         headers=headers("owner")).status_code == 404
    assert client.post("/api/v2/collaboration/accept",
                       json={"invite_token": another["token_once"]},
                       headers=headers("bob")).status_code == 200
