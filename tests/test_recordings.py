from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app import recordings


def _clip(root: Path, name: str, *, active=False, payload=b"video") -> Path:
    path=root/name
    path.mkdir(parents=True)
    (path/"meta.json").write_text(json.dumps({"clip_id":name,"active":active,"started_at":"2026-10-15T18:00:00+00:00"}),encoding="utf-8")
    if payload is not None:
        (path/"clip.mkv").write_bytes(payload)
    return path


@pytest.fixture(autouse=True)
def reset_job(monkeypatch,tmp_path):
    monkeypatch.setattr(recordings,"ROOT",tmp_path/"recordings")
    recordings.job.task=None
    recordings.job.process=None
    recordings.job.clip_id=None
    recordings.job.camera_id=None
    recordings.job.duration_seconds=0
    recordings.job.started_at=None
    recordings.job.stop_requested=False
    recordings.job.error=None
    yield
    recordings.job.task=None
    recordings.job.process=None


def test_recording_request_bounds_and_camera_id():
    assert recordings.StartBody(duration_seconds=5,camera_id="cam0").duration_seconds==5
    with pytest.raises(ValidationError): recordings.StartBody(duration_seconds=4)
    with pytest.raises(ValidationError): recordings.StartBody(duration_seconds=60,camera_id="/dev/video0")


def test_bounded_env_int_survives_invalid_environment(monkeypatch):
    monkeypatch.setenv("GC_TEST_INT","garbage")
    assert recordings._bounded_env_int("GC_TEST_INT",20,3,100)==20
    monkeypatch.setenv("GC_TEST_INT","999")
    assert recordings._bounded_env_int("GC_TEST_INT",20,3,100)==100


def test_clip_listing_recovers_stale_active_metadata(tmp_path):
    root=recordings.ROOT
    path=_clip(root,"clip_aaaaaaaaaaaa",active=True,payload=b"1234")
    rows=recordings._clip_rows()
    assert len(rows)==1 and rows[0][0]==path
    meta=rows[0][1]
    assert meta["active"] is False
    assert meta["interrupted"] is True
    assert meta["download_ready"] is True and meta["bytes"]==4
    assert "Dienstneustart" in meta["error"]


def test_retention_keeps_only_newest_completed_clips(monkeypatch):
    root=recordings.ROOT
    monkeypatch.setattr(recordings,"MAX_CLIPS",3)
    paths=[]
    for index in range(5):
        path=_clip(root,f"clip_{index:012x}")
        os.utime(path,(1000+index,1000+index))
        paths.append(path)
    recordings._prune()
    remaining={p.name for p in root.iterdir() if p.is_dir()}
    assert remaining=={paths[2].name,paths[3].name,paths[4].name}


def test_safe_clip_rejects_invalid_ids_and_missing_paths():
    with pytest.raises(HTTPException) as invalid:
        recordings._safe_clip("../../etc")
    assert invalid.value.status_code==404
    with pytest.raises(HTTPException): recordings._safe_clip("clip_aaaaaaaaaaaa")


@pytest.mark.skipif(os.name=="nt",reason="Windows symlink creation requires Developer Mode/admin rights")
def test_recordings_never_follow_clip_or_video_symlinks(tmp_path):
    root=recordings.ROOT
    outside=tmp_path/"outside";outside.mkdir();(outside/"clip.mkv").write_bytes(b"secret")
    root.mkdir(parents=True)
    (root/"clip_aaaaaaaaaaaa").symlink_to(outside,target_is_directory=True)
    with pytest.raises(HTTPException): recordings._safe_clip("clip_aaaaaaaaaaaa")
    safe=_clip(root,"clip_bbbbbbbbbbbb",payload=None)
    (safe/"clip.mkv").symlink_to(outside/"clip.mkv")
    assert recordings._safe_target(safe) is None


def test_start_rejects_critically_low_disk(monkeypatch):
    monkeypatch.setattr(recordings.shutil,"disk_usage",lambda _path:SimpleNamespace(total=1,used=1,free=0))
    with pytest.raises(HTTPException) as error:
        asyncio.run(recordings.start(recordings.StartBody(duration_seconds=30)))
    assert error.value.status_code==507
    assert recordings.job.task is None


def test_stop_tolerates_process_exit_race():
    class Task:
        def done(self): return False
    class Process:
        returncode=None
        def terminate(self): raise ProcessLookupError
    recordings.job.task=Task()
    recordings.job.process=Process()
    result=asyncio.run(recordings.stop())
    assert result["ok"] is True
    assert recordings.job.stop_requested is True


def test_recordings_router_and_ui_contract():
    root=Path(__file__).resolve().parents[1]
    paths={(route.path,tuple(sorted(route.methods or []))) for route in recordings.router.routes}
    assert ("/api/v1/recordings/start",("POST",)) in paths
    assert ("/api/v1/recordings/stop",("POST",)) in paths
    source=(root/"web/menu-live.js").read_text(encoding="utf-8")
    entry=(root/"app/entrypoint.py").read_text(encoding="utf-8")
    for token in ("/api/v1/recordings/start","/api/v1/recordings/stop","/api/v1/recordings/${encodeURIComponent(clip)}`","gc-recording-delete"):
        assert token in source
    assert "recordings_router" in entry
    assert "-fs\", str(MAX_CLIP_BYTES)" in (root/"app/recordings.py").read_text(encoding="utf-8")
