from pathlib import Path

from app import maintenance


def test_preflight_reports_runtime(monkeypatch, tmp_path):
    root=tmp_path/"app"; root.mkdir(); (root/"VERSION").write_text("alpha-test\n"); (root/"BUILD").write_text("999\n"); (root/".live-git-sha").write_text("abc123\n"); (root/"data").mkdir(); venv=root/".venv/bin"; venv.mkdir(parents=True); py=venv/"python"; py.write_text(""); py.chmod(0o755)
    monkeypatch.setattr(maintenance,"ROOT",root); monkeypatch.setattr(maintenance,"STATE_DIR",tmp_path/"state")
    monkeypatch.setattr(maintenance,"_service_state",lambda:{"active":True,"state":"active","substate":"running","main_pid":"1"})
    monkeypatch.setattr(maintenance,"_maintenance_bridge",lambda:{"available":False,"noninteractive":False,"status":"unavailable"})
    import asyncio
    result=asyncio.run(maintenance.preflight(False))
    assert result["version"]=="alpha-test"
    assert result["build"]=="999"
    assert result["live_git_sha"]=="abc123"
    assert result["service"]["active"] is True

def test_backup_listing_is_bounded(monkeypatch,tmp_path):
    root=tmp_path/"grow"; root.mkdir(); monkeypatch.setattr(maintenance,"ROOT",root)
    for i in range(25): (tmp_path/f"grow.backup-{i:02d}").mkdir()
    rows=maintenance._code_backups()
    assert len(rows)==20
    assert all(row["path_type"]=="code_rollback" for row in rows)
