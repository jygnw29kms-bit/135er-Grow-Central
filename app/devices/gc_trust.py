"""Persistent, explicit user decisions and replay protection for native sensors."""
from __future__ import annotations
from contextlib import contextmanager, closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from .gc_identity import SignedMessage

STATUSES = ('DISCOVERED', 'TRUSTED', 'REJECTED', 'REVOKED')

class TrustStore:
    def __init__(self, path: Path | None = None):
        self.path = path or Path(os.getenv('GC_DEVICE_TRUST_DB', '/var/lib/135er-grow-central/device-trust.db'))

    @contextmanager
    def db(self):
        self.path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        os.chmod(self.path, 0o600)
        with closing(sqlite3.connect(self.path, timeout=3)) as db, db:
            db.row_factory = sqlite3.Row
            db.execute('CREATE TABLE IF NOT EXISTS devices (id TEXT PRIMARY KEY, status TEXT NOT NULL, public_key TEXT, fingerprint TEXT, identity_verified INTEGER NOT NULL, metadata TEXT NOT NULL, name TEXT, room_id TEXT, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS receipts (device_id TEXT, kind TEXT, seq INTEGER, digest TEXT, received_at TEXT, PRIMARY KEY(device_id, kind))')
            db.execute('CREATE TABLE IF NOT EXISTS retired_keys (fingerprint TEXT PRIMARY KEY, device_id TEXT NOT NULL)')
            db.execute('BEGIN IMMEDIATE')
            yield db

    @staticmethod
    def public(row):
        if row is None:
            return None
        return {**dict(row), 'identity_verified': bool(row['identity_verified']), 'metadata': json.loads(row['metadata'])}

    def get(self, device_id):
        with self.db() as db:
            return self.public(db.execute('SELECT * FROM devices WHERE id=?', (device_id,)).fetchone())

    def list(self):
        with self.db() as db:
            return [self.public(row) for row in db.execute('SELECT * FROM devices ORDER BY first_seen,id')]

    @staticmethod
    def _receipt(db, message):
        row = db.execute('SELECT * FROM receipts WHERE device_id=? AND kind=?', (message.device_id, message.kind)).fetchone()
        if row and (message.sequence < row['seq'] or (message.sequence == row['seq'] and message.digest != row['digest'])):
            raise PermissionError('sensor replay rejected')
        if row and message.sequence == row['seq']:
            return row['received_at']
        now = datetime.now(timezone.utc).isoformat()
        db.execute('INSERT OR REPLACE INTO receipts VALUES(?,?,?,?,?)', (message.device_id, message.kind, message.sequence, message.digest, now))
        return now

    def discover(self, announce, message: SignedMessage | None):
        now = datetime.now(timezone.utc).isoformat()
        metadata = {'model': announce.model, 'firmware': announce.firmware, 'device_class': announce.device_class.value, 'capabilities': [c.value for c in announce.capabilities], 'reported_name': announce.name, 'hardware_uid': announce.hardware_uid, 'calibration': announce.calibration}
        with self.db() as db:
            if message and db.execute('SELECT 1 FROM retired_keys WHERE fingerprint=?', (message.fingerprint,)).fetchone():
                raise PermissionError('retired sensor identity rejected')
            row = db.execute('SELECT * FROM devices WHERE id=?', (announce.id,)).fetchone()
            if row and row['public_key'] and (message is None or message.public_key != row['public_key']):
                raise PermissionError('sensor key changed; manual identity review required')
            if message:
                if message.device_id != announce.id:
                    raise PermissionError('announcement identity mismatch')
                received = self._receipt(db, message)
            else:
                received = now
            if row:
                # Do not erase an operator's decision, name, key or room on rediscovery.
                db.execute('UPDATE devices SET last_seen=? WHERE id=?', (received, announce.id))
                if row['status'] == 'DISCOVERED':
                    db.execute('UPDATE devices SET public_key=?,fingerprint=?,identity_verified=?,metadata=? WHERE id=?',
                               (message.public_key if message else None, message.fingerprint if message else None, int(message is not None), json.dumps(metadata), announce.id))
            else:
                if db.execute('SELECT count(*) FROM devices').fetchone()[0] >= 1000:
                    raise PermissionError('sensor discovery capacity reached')
                db.execute('INSERT INTO devices VALUES(?,?,?,?,?,?,?,?,?,?)',
                           (announce.id, 'DISCOVERED', message.public_key if message else None, message.fingerprint if message else None,
                            int(message is not None), json.dumps(metadata), None, None, now, received))
            return self.public(db.execute('SELECT * FROM devices WHERE id=?', (announce.id,)).fetchone())

    def accept(self, device_id, *, name, room_id, fingerprint, proved_key, assign):
        with self.db() as db:
            row = db.execute('SELECT * FROM devices WHERE id=?', (device_id,)).fetchone()
            if row is None:
                raise KeyError('sensor not found')
            if row['status'] != 'DISCOVERED':
                raise ValueError('sensor must be explicitly released before acceptance')
            if not row['identity_verified'] or not row['fingerprint'] or row['public_key'] != proved_key:
                raise PermissionError('sensor needs firmware with verified cryptographic identity')
            if fingerprint.lower() != row['fingerprint'][-16:]:
                raise PermissionError('physical sensor fingerprint confirmation does not match')
            assign()  # Persist room assignment before granting productive data access.
            db.execute('UPDATE devices SET status=\'TRUSTED\',name=?,room_id=? WHERE id=?', (name, room_id, device_id))
            return self.public(db.execute('SELECT * FROM devices WHERE id=?', (device_id,)).fetchone())

    def transition(self, device_id, status):
        if status not in ('REJECTED', 'REVOKED', 'DISCOVERED'):
            raise ValueError('unsupported trust transition')
        with self.db() as db:
            row = db.execute('SELECT * FROM devices WHERE id=?', (device_id,)).fetchone()
            if row is None:
                raise KeyError('sensor not found')
            allowed = {'REJECTED': ('DISCOVERED',), 'REVOKED': ('TRUSTED',), 'DISCOVERED': ('REJECTED', 'REVOKED')}
            if row['status'] not in allowed[status]:
                raise ValueError('invalid trust transition')
            db.execute('UPDATE devices SET status=?,room_id=NULL WHERE id=?', (status, device_id))
            return self.public(db.execute('SELECT * FROM devices WHERE id=?', (device_id,)).fetchone())

    def reset_identity(self, device_id, fingerprint):
        with self.db() as db:
            row = db.execute('SELECT * FROM devices WHERE id=?', (device_id,)).fetchone()
            if row is None:
                raise KeyError('sensor not found')
            if row['status'] not in ('REJECTED', 'REVOKED') or not row['fingerprint']:
                raise ValueError('reject or revoke the sensor before identity reset')
            if fingerprint.lower() != row['fingerprint'][-16:]:
                raise PermissionError('old identity confirmation does not match')
            db.execute('INSERT OR IGNORE INTO retired_keys VALUES(?,?)', (row['fingerprint'], device_id))
            db.execute('DELETE FROM receipts WHERE device_id=?', (device_id,))
            db.execute("UPDATE devices SET status='DISCOVERED',public_key=NULL,fingerprint=NULL,identity_verified=0,room_id=NULL WHERE id=?", (device_id,))
            return self.public(db.execute('SELECT * FROM devices WHERE id=?', (device_id,)).fetchone())

    def require_trusted(self, device_id):
        row = self.get(device_id)
        if not row or row['status'] != 'TRUSTED' or not row['identity_verified']:
            raise PermissionError('sensor requires manual acceptance and room assignment')
        return row

    def receive(self, message: SignedMessage):
        with self.db() as db:
            row = db.execute('SELECT * FROM devices WHERE id=?', (message.device_id,)).fetchone()
            if not row or row['status'] != 'TRUSTED' or row['public_key'] != message.public_key:
                raise PermissionError('sensor is not trusted or identity changed')
            return self._receipt(db, message)
