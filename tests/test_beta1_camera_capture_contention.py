"""Camera snapshot must never evict an active ffmpeg viewer."""
from pathlib import Path

CAM = (Path(__file__).resolve().parents[1] / "app/camera.py").read_text(encoding="utf-8")


def test_snapshot_does_not_stop_active_capture():
    function = CAM.split("async def camera_snapshot(", 1)[1].split("\ndef _stream_is_stale(", 1)[0]
    assert '_stop_active_stream("snapshot")' not in function
    assert "cached = _LATEST_JPEG if active" in function
    assert '"X-GrowCentral-Frame-Source": "shared-live-stream"' in function
    assert 'raise HTTPException(503, "live camera stream has no fresh complete frame")' in function


def test_watchdog_reports_instead_of_silently_restarting_any_service():
    assert 'snapshot_waiting_for_live_frame' in CAM
    assert 'competing_stream_replacement' in CAM
    assert "camera.stream.watchdog" in CAM
