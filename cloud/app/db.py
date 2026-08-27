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
            CREATE INDEX IF NOT EXISTS idx_telemetry_site_device_id
                ON telemetry(site_id, device_id, id DESC);

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

            CREATE TABLE IF NOT EXISTS diagnostic_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                site_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                summary_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_diagnostic_events_site_device_id
                ON diagnostic_events(site_id, device_id, id DESC);

            CREATE TABLE IF NOT EXISTS managed_devices (
                device_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL DEFAULT '',
                owner_name TEXT NOT NULL DEFAULT '',
                group_name TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                plan TEXT NOT NULL DEFAULT 'BASIC',
                valid_until TEXT,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_seen_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_managed_devices_status
                ON managed_devices(status);
            CREATE INDEX IF NOT EXISTS idx_managed_devices_group
                ON managed_devices(group_name);

            CREATE TABLE IF NOT EXISTS device_features (
                device_id TEXT NOT NULL,
                feature TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(device_id, feature),
                FOREIGN KEY(device_id) REFERENCES managed_devices(device_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cloud_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        await db.execute("PRAGMA foreign_keys=ON")
        await db.commit()
