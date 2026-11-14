"""C920 camera stream watchdog regressions.

No real camera is touched by these tests.
"""
import asyncio

from app import camera


def test_watchdog_uses_complete_frame_heartbeat_not_process_liveness():
    assert camera._stream_is_stale(100.0, now=114.9, timeout=15.0) is False
    assert camera._stream_is_stale(100.0, now=115.1, timeout=15.0) is True


def test_watchdog_stops_only_the_matching_stream(monkeypatch):
    calls = []
    class FakeProcess:
        returncode = None
        pid = 10203
    proc = FakeProcess()
    async def fake_stop(reason, *, expected_token=None):
        calls.append(reason)
        proc.returncode = 0
        return True
    monkeypatch.setattr(camera, "_stop_active_stream", fake_stop)
    monkeypatch.setattr(camera, "CAMERA_WATCHDOG_POLL", 0.001)
    monkeypatch.setattr(camera, "CAMERA_FRAME_TIMEOUT", 0.001)
    async def run():
        token = object()
        camera._ACTIVE_STREAM_TOKEN = token
        camera._ACTIVE_STREAM_PROCESS = proc
        try:
            await camera._camera_stream_watchdog(token, proc, {"last_frame": 0.0})
        finally:
            camera._ACTIVE_STREAM_TOKEN = None
            camera._ACTIVE_STREAM_PROCESS = None
    asyncio.run(run())
    assert calls == ["watchdog_missing_frames"]


def test_replaced_stream_cannot_be_stopped_by_old_watchdog(monkeypatch):
    calls = []
    class FakeProcess:
        returncode = None
        pid = 10204
    proc = FakeProcess()
    monkeypatch.setattr(camera, "CAMERA_WATCHDOG_POLL", 0.001)
    monkeypatch.setattr(camera, "CAMERA_FRAME_TIMEOUT", 0.001)
    async def fake_stop(reason):
        calls.append(reason)
    monkeypatch.setattr(camera, "_stop_active_stream", fake_stop)
    async def run():
        camera._ACTIVE_STREAM_TOKEN = object()
        camera._ACTIVE_STREAM_PROCESS = object()
        try:
            await camera._camera_stream_watchdog(object(), proc, {"last_frame": 0.0})
        finally:
            camera._ACTIVE_STREAM_TOKEN = None
            camera._ACTIVE_STREAM_PROCESS = None
    asyncio.run(run())
    assert calls == []
