"""Beta 1.0 camera diagnostics and local/cloud UI regression contract."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAM = (ROOT / "app/camera.py").read_text(encoding="utf-8")
LOCAL = (ROOT / "web/gc-final.html").read_text(encoding="utf-8")
CLOUD = (ROOT / "cloud/portal/cloud-master.html").read_text(encoding="utf-8")
LOCAL_JS = (ROOT / "web/gc-final.js").read_text(encoding="utf-8")
CLOUD_JS = (ROOT / "cloud/portal/gc-final-cloud.js").read_text(encoding="utf-8")
LOCAL_CSS = (ROOT / "web/gc-final.css").read_text(encoding="utf-8")
CLOUD_CSS = (ROOT / "cloud/portal/gc-final-cloud.css").read_text(encoding="utf-8")


def test_camera_watchdog_has_bounded_owner_only_diagnostics():
    assert "@router.get(\"/diagnostics\", dependencies=[Depends(require_write_auth)])" in CAM
    assert "del _CAMERA_WATCHDOG_EVENTS[:-32]" in CAM
    for reason in (
        "missing_complete_frames",
        "missing_ffmpeg_output",
        "ffmpeg_output_ended",
        "competing_stream_replacement",
        "preview_unavailable_while_stream_active",
    ):
        assert reason in CAM
    assert '"capture_active"' in CAM
    assert '"last_complete_frame_age_seconds"' in CAM


def test_camera_start_stop_controls_match_both_gui_shells():
    for html in (LOCAL, CLOUD):
        assert 'id="cameraStop"' in html
        assert 'id="cameraRefresh"' in html
        assert 'data-page="growbook"' in html
    for js in (LOCAL_JS, CLOUD_JS):
        assert "state.cameraPaused=true" in js
        assert "state.cameraPaused=false" in js
        assert "if(state.cameraPaused){state.activeCam=null;return;}" in js
        assert "img.removeAttribute('src')" in js


def test_lamp_switch_color_follows_fresh_measured_status_not_click():
    for js in (LOCAL_JS, CLOUD_JS):
        assert "badge.dataset.state=active?(latest.power_on?'on':'off'):'unknown'" in js
        assert "sw.dataset.state=active?(latest.power_on?'on':'off'):'unknown'" in js
    for css in (LOCAL_CSS, CLOUD_CSS):
        for token in ('data-state="on"', 'data-state="off"', 'data-state="unknown"'):
            assert token in css
