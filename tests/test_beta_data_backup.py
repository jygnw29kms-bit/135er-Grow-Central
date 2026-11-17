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


def test_optional_app_configuration_is_encrypted_and_staged(tmp_path):
    root = fixture_root(tmp_path)
    config = tmp_path / "app.env"
    config.write_text("GC_TEST_SECRET=not-a-real-secret\n")
    blob = create_bundle(root, "synthetic beta backup passphrase", config_file=config)
    assert b"GC_TEST_SECRET" not in blob
    restored = verify_bundle(blob, "synthetic beta backup passphrase")
    assert restored["config/app.env"] == config.read_bytes()
    dest = tmp_path / "new-stage"
    stage_restore(blob, "synthetic beta backup passphrase", dest)
    assert (dest / "config/app.env").read_bytes() == config.read_bytes()
    assert (dest / "config/app.env").stat().st_mode & 0o077 == 0


def _repack_encrypted(blob: bytes, password: str, edit):
    """Create deliberately malformed, but correctly encrypted, test archives."""
    import io
    import json
    import os
    import zipfile
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from scripts.beta_data_backup import _key
    prefix = len(MAGIC)
    salt, nonce = blob[prefix:prefix + 16], blob[prefix + 16:prefix + 28]
    raw = AESGCM(_key(password, salt)).decrypt(nonce, blob[prefix + 28:], MAGIC)
    with zipfile.ZipFile(io.BytesIO(raw)) as src:
        members = [(item, src.read(item)) for item in src.infolist()]
    members = edit(members)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        for item, data in members:
            dst.writestr(item, data)
    fresh_salt, fresh_nonce = os.urandom(16), os.urandom(12)
    return MAGIC + fresh_salt + fresh_nonce + AESGCM(_key(password, fresh_salt)).encrypt(
        fresh_nonce, output.getvalue(), MAGIC)


def test_restore_rejects_manifest_negative_or_oversized_entries(tmp_path):
    import json
    root = fixture_root(tmp_path)
    password = "synthetic beta backup passphrase"
    original = create_bundle(root, password)

    for invalid in (-1, 100 * 1024 * 1024):
        def corrupt(members):
            changed = []
            for item, data in members:
                if item.filename == "manifest.json":
                    manifest = json.loads(data)
                    manifest["files"][0]["size"] = invalid
                    data = json.dumps(manifest).encode()
                changed.append((item, data))
            return changed

        archive = _repack_encrypted(original, password, corrupt)
        with pytest.raises(ValueError, match="Unsafe archive manifest entry"):
            verify_bundle(archive, password)


def test_restore_rejects_duplicate_zip_file_names(tmp_path):
    root = fixture_root(tmp_path)
    password = "synthetic beta backup passphrase"
    original = create_bundle(root, password)

    def duplicate(members):
        return members + [members[-1]]

    archive = _repack_encrypted(original, password, duplicate)
    with pytest.raises(ValueError, match="Unexpected or duplicate"):
        verify_bundle(archive, password)


def test_restore_rejects_zip_symlink_even_with_valid_hash(tmp_path):
    import zipfile
    root = fixture_root(tmp_path)
    password = "synthetic beta backup passphrase"
    original = create_bundle(root, password)

    def symlink(members):
        changed = []
        for item, data in members:
            if item.filename == "data/rooms.json":
                link = zipfile.ZipInfo(item.filename)
                link.create_system = 3
                link.external_attr = (0o120777 << 16)
                item = link
            changed.append((item, data))
        return changed

    archive = _repack_encrypted(original, password, symlink)
    with pytest.raises(ValueError, match="Unsafe ZIP member type"):
        verify_bundle(archive, password)
