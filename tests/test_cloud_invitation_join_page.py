"""Cloud room joining must be private, account bound and separated from owner UI."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
JOIN=(ROOT/'cloud/portal/join-room.html').read_text(encoding='utf-8')
JS=(ROOT/'cloud/portal/join-room.js').read_text(encoding='utf-8')
PORTAL=(ROOT/'cloud/portal/cloud-portal.js').read_text(encoding='utf-8')
DEPLOY=(ROOT/'cloud/portal/deploy_cloud_portal.sh').read_text(encoding='utf-8')
VERIFY=(ROOT/'scripts/verify_cloud_final_master_deployment.py').read_text(encoding='utf-8')


def test_one_time_invite_fragment_never_sent_as_query():
    assert "location.hash" in JS and "room-invite" in JS
    assert "'/join-room.html'+location.hash" in PORTAL
    assert "history.replaceState(null,'',location.pathname)" in JS
    assert 'invite_token:inviteToken' in JS
    assert "localStorage" not in JS and "sessionStorage" not in JS
    assert "console.log" not in JS


def test_guest_uses_scoped_transport_not_owner_socket():
    assert "'/api/v2/collaboration/remote/connect'" in JS
    assert "'/api/v2/remote/connect'" not in JS
    assert "guest_scoped!==true" in JS
    assert "api/v2/collaboration/accept" in JS
    assert "api/v2/collaboration/my-rooms" in JS
    assert "credentials:'omit'" in JS
    assert "textContent" in JS and ".innerHTML" not in JS
    assert "'/api/v1/rooms/'" in JS


def test_guest_page_does_not_expose_unscoped_controls():
    assert 'id="accountPanel"' in JOIN
    assert 'id="roomPanel"' in JOIN
    assert 'type="password"' in JOIN
    assert 'join-room.js?v=' in JOIN
    for forbidden in ('fast-fan-control','fast-lamp-control','/api/v1/rooms"'):
        assert forbidden not in JOIN
    assert "confirm_physical_change" not in JS


def test_guest_assets_are_deployed_and_verified():
    for name in ("join-room.html","join-room.js"):
        assert f'"$repo/cloud/portal/{name}" "$stage/{name}"' in DEPLOY
        assert f'"cloud/portal/{name}": "{name}"' in VERIFY
