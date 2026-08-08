-- 135er GrowControl Local SQLite schema baseline
-- DE: Lokale Daten für Offline-Betrieb und Synchronisation.
-- EN: Local data for offline operation and synchronization.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    device_type TEXT NOT NULL,
    name TEXT NOT NULL,
    hardware_id TEXT,
    config_json TEXT NOT NULL DEFAULT '{}',
    online INTEGER NOT NULL DEFAULT 0,
    last_seen_at TEXT
);

CREATE TABLE IF NOT EXISTS sensors (
    id TEXT PRIMARY KEY,
    device_id TEXT,
    name TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    unit TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS sensor_readings_local (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    value REAL NOT NULL,
    quality TEXT NOT NULL DEFAULT 'ok',
    synced INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(sensor_id) REFERENCES sensors(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_local_readings_sync_ts ON sensor_readings_local(synced, ts);

CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    schedule_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS automations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    priority INTEGER NOT NULL DEFAULT 100,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS automation_rules (
    id TEXT PRIMARY KEY,
    automation_id TEXT NOT NULL,
    condition_json TEXT NOT NULL,
    action_json TEXT NOT NULL,
    hysteresis_json TEXT NOT NULL DEFAULT '{}',
    safety_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(automation_id) REFERENCES automations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    level TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    data_json TEXT NOT NULL DEFAULT '{}',
    synced INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT NOT NULL
);
