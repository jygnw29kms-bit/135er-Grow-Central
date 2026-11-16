"""Beta 1.0 owner GUI and secure Cloud account-bridge contract."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LOCAL=(ROOT/"web/gc-final.html").read_text(encoding="utf-8")
CLOUD=(ROOT/"cloud/portal/cloud-master.html").read_text(encoding="utf-8")
LOCAL_JS=(ROOT/"web/owner-members.js").read_text(encoding="utf-8")
CLOUD_JS=(ROOT/"cloud/portal/owner-members.js").read_text(encoding="utf-8")
PARENT=(ROOT/"cloud/portal/cloud-portal.js").read_text(encoding="utf-8")
BRIDGE=(ROOT/"cloud/portal/cloud-master-bridge.js").read_text(encoding="utf-8")

def test_owner_gui_shell_and_branding_match():
    for html in (LOCAL,CLOUD):
        assert 'data-page="members"' in html
        assert '<section id="members" class="page">' in html
        for item in ("gcMemberList","gcInvitationList","gcInviteRole","gcInviteTtl",
                     "gcOwnerRefresh","gcCreateInvitation","gcInvitationOnce"):
            assert 'id="'+item+'"' in html
        assert 'gc-sidebar-brand-title' in html
        assert 'ENVIRONMENT CONTROL SYSTEM' in html
        assert '/static/owner-members.js' in html

def test_controller_is_identical_for_both_access_paths():
    assert LOCAL_JS==CLOUD_JS
    for pattern in ("gcCloudOwnerRequest","room-members/owner/","room-sharing/",
                    "Einladung widerrufen","Zugriff entziehen","ttl_hours"):
        assert pattern in LOCAL_JS
    assert "localStorage" not in LOCAL_JS
    assert "sessionStorage" not in LOCAL_JS
    assert "innerHTML" not in LOCAL_JS

def test_cloud_account_token_never_enters_child_frame():
    assert "window.gcCloudOwnerRequest" in BRIDGE
    assert "ask('owner-members'" in BRIDGE
    assert "msg.kind==='owner-members'" in PARENT
    assert "encodeURIComponent(currentDeviceId)" in PARENT
    assert "'/api/v2/collaboration/devices/'" in PARENT
    assert "Authorization:'Bearer '+accessToken" in PARENT
    assert "masterReply(msg.id,response.status,data)" in PARENT
    assert "get_membership_role" not in LOCAL_JS
    assert "accessToken" not in LOCAL_JS
    assert "accessToken" not in CLOUD_JS

def test_cloud_writes_are_explicit_allowlisted():
    assert "if(!allowed)" in PARENT
    assert "if(!accessToken||!currentDeviceId)" in PARENT
    assert "event.origin!==location.origin" in PARENT
    assert "event.source!==$('masterFrame')?.contentWindow" in PARENT
    assert "['GET','POST','PATCH','DELETE']" in PARENT
