"""SQLite-Persistenz / SQLite persistence."""
from pathlib import Path

import aiosqlite

from .config import settings


async def init_db():
    """DE: Tabellen idempotent anlegen. EN: Create tables idempotently."""
    Path(settings.cloud_db).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(settings.cloud_db) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                site_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                temperature_c REAL,
                humidity_pct REAL,
                vpd_kpa REAL,
                fan_speed_pct INTEGER,
                device_online INTEGER NOT NULL,
                extra_json TEXT
            );
            CREATE TABLE IF NOT EXISTS commands (
                id TEXT PRIMARY KEY,
                site_id TEXT NOT NULL,
                target TEXT NOT NULL,
                action TEXT NOT NULL,
                value_json TEXT,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                result_json TEXT
            );
            """
        )
        await db.commit()
