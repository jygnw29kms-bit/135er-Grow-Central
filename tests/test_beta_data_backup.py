"""Encrypted Beta data export/restore tests using synthetic throwaway files only."""
import sqlite3
from pathlib import Path

import pytest

from scripts.beta_data_backup import (
    MAGIC, collect, create_bundle, verify_bundle, stage_restore,
)


def fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    root.mkdir()
    (root / "rooms.json").write_text('{"rooms":[{"id":"test"}]}', encoding="utf-8")
    (root / "grow-photos").mkdir()
    (root / "grow-photos" / "sample.jpg").write_bytes(b"FAKEJPEG")
    (root / "cloud-identity").mkdir()
    (root / "cloud-identity" / "device-ed25519.key").write_bytes(b"PRIVATE_TEST_KEY")
    with sqlite3.connect(root / "history.sqlite3") as db:
        db.execute("CREATE TABLE samples (x INTEGER)")
        db.execute("INSERT INTO samples VALUES (42)")
        db.commit()
    (root / "gui-sessions.json").write_text('{"session":"do-not-restore"}')
    return root


def test_encrypted_backup_is_private_and_roundtrips_to_staging(tmp_path):
    root = fixture_root(tmp_path)
    password = "synthetic beta backup passphrase"
    blob = create_bundle(root, password)
    assert blob.startswith(MAGIC)
    for secret in (b"PRIVATE_TEST_KEY", b"FAKEJPEG", b"do-not-restore"):
        assert secret not in blob
    verified = verify_bundle(blob, password)
    assert verified["rooms.json"] == (root / "rooms.json").read_bytes()
    assert "gui-sessions.json" not in verified
    stage = tmp_path / "staged"
    assert stage_restore(blob, password, stage) == len(verified)
    assert (stage / "grow-photos/sample.jpg").read_bytes() == b"FAKEJPEG"
    assert (stage / "cloud-identity/device-ed25519.key").read_bytes() == b"PRIVATE_TEST_KEY"
    assert not (stage / "gui-sessions.json").exists()
    assert (stage / "rooms.json").stat().st_mode & 0o077 == 0
    assert (root / "rooms.json").exists()


def test_restore_rejects_wrong_passphrase_or_tamper(tmp_path):
    root = fixture_root(tmp_path)
    blob = create_bundle(root, "synthetic beta backup passphrase")
    with pytest.raises(ValueError, match="passphrase"):
        verify_bundle(blob, "completely wrong passphrase")
    corrupt = blob[:-2] + bytes([blob[-2] ^ 1]) + blob[-1:]
    with pytest.raises(ValueError, match="corrupted"):
        verify_bundle(corrupt, "synthetic beta backup passphrase")


def test_restore_never_overwrites_existing_directory(tmp_path):
    root = fixture_root(tmp_path)
    blob = create_bundle(root, "synthetic beta backup passphrase")
    with pytest.raises(ValueError, match="must not exist"):
        stage_restore(blob, "synthetic beta backup passphrase", root)
    assert (root / "rooms.json").exists()


def test_source_symlink_cannot_escape_backup_root(tmp_path):
    root = fixture_root(tmp_path)
    (root / "grow-photos" / "escape").symlink_to(root / "rooms.json")
    with pytest.raises(ValueError, match="symlink"):
        collect(root)
