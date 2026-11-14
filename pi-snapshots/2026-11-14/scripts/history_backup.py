#!/usr/bin/env python3
"""Consistent offline backup of Grow Central long-term history SQLite database.

Uses SQLite's online-backup API (WAL safe), gzip and atomic replacement.
Keep last 30 daily backups plus first daily of each month for 5 years.
Does not send files over the network or touch raw auth tokens.
"""
from __future__ import annotations
from datetime import datetime,timezone
import gzip
import os
from pathlib import Path
import sqlite3
import tempfile

SOURCE=Path(os.getenv("GC_HISTORY_DB","/var/lib/135er-grow-central/history.sqlite3"))
TARGET=Path(os.getenv("GC_HISTORY_BACKUP_DIR","/var/lib/135er-grow-central/history-backups"))

def run()->str:
    if not SOURCE.is_file():
        raise FileNotFoundError("History database not initialized")
    TARGET.mkdir(parents=True,exist_ok=True,mode=0o750)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d")
    final=TARGET/f"history-{stamp}.sqlite3.gz"
    with tempfile.TemporaryDirectory(dir=TARGET) as directory:
        backup=Path(directory)/"history.sqlite3"
        with sqlite3.connect(SOURCE,timeout=15) as src:
            with sqlite3.connect(backup) as dest:
                src.backup(dest)
                result=dest.execute("PRAGMA integrity_check").fetchone()[0]
                if result!="ok":raise RuntimeError("Backup integrity check failed")
        stage=Path(directory)/"history.sqlite3.gz"
        with backup.open("rb") as f, gzip.open(stage,"wb",compresslevel=6) as g:
            while (chunk:=f.read(1024*1024)):
                g.write(chunk)
        os.chmod(stage,0o640)
        os.replace(stage,final)
    # Retain daily copies for a month and first daily per month for five years.
    files=sorted(TARGET.glob("history-????????.sqlite3.gz"))
    recent=set(files[-30:])
    monthly={}
    for f in files:
        key=f.name[8:14]
        monthly.setdefault(key,f)
    kept=recent|set(list(monthly.values())[-60:])
    for f in files:
        if f not in kept:f.unlink()
    return str(final)

if __name__=="__main__":
    path=run()
    print("HISTORY_BACKUP_OK",Path(path).name,Path(path).stat().st_size)
