#!/usr/bin/env python3
"""Encrypted Grow-Central beta data archive and SAFE staging-only restore.

Never overwrite a running installation. Requires an operator-chosen passphrase;
private device identities, pairing secrets, photos and logs remain encrypted.
A restored staging directory is *not* a complete system restore until a
fresh-image migration and account/permission check have been approved.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import io
import json
import os
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"GC-BETA1\x00"
FILES = frozenset({
    "rooms.json", "history.sqlite3", "mars-history.sqlite3",
    "sensor-calibration.db", "device-trust.db",
    "ui-layout.json", "room-sharing.json", "room-notifications.json",
    "room-control-plans.json", "room-push.json", "local-api-token",
    "hardware-model", "hardware-profile", "hardware-wlan-interface",
    "credentials.json", "credentials.key", "config/app.env",
})
DIRS = frozenset({"grow-photos", "homekit", "cloud-identity"})
SQLITE = frozenset({"history.sqlite3", "mars-history.sqlite3",
                    "sensor-calibration.db", "device-trust.db"})
MAX_FILE = 80 * 1024 * 1024
MAX_BUNDLE = 512 * 1024 * 1024


def _allowed(name: str) -> bool:
    p = Path(name)
    if p.is_absolute() or not name or ".." in p.parts or "\\" in name:
        return False
    return name in FILES or (len(p.parts) >= 2 and p.parts[0] in DIRS)


def _key(passphrase: str, salt: bytes) -> bytes:
    if len(passphrase) < 16:
        raise ValueError("Backup passphrase must contain at least 16 characters")
    return Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode())


def _read_file(path: Path, relative: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Symlink or non-regular file rejected")
    if path.stat().st_size > MAX_FILE:
        raise ValueError(f"File too large: {relative}")
    if relative not in SQLITE:
        return path.read_bytes()
    # SQLite's online backup API produces a consistent snapshot with live WAL.
    with tempfile.TemporaryDirectory(prefix="gc-sqlite-snapshot-") as td:
        target = Path(td) / "snapshot.db"
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as source:
            with sqlite3.connect(target) as destination:
                source.backup(destination)
        with sqlite3.connect(target) as check:
            if check.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError(f"SQLite integrity check failed: {relative}")
        return target.read_bytes()


def collect(root: Path) -> dict[str, bytes]:
    root = root.resolve(strict=True)
    selected: dict[str, bytes] = {}
    for name in sorted(FILES):
        path = root / name
        if path.exists():
            selected[name] = _read_file(path, name)
    for name in sorted(DIRS):
        folder = root / name
        if folder.is_symlink():
            raise ValueError("Directory symlink rejected")
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*")):
            if path.is_symlink():
                raise ValueError("Directory entry symlink rejected")
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                if not _allowed(relative):
                    raise ValueError(f"Unexpected file: {relative}")
                selected[relative] = _read_file(path, relative)
    if not selected or "rooms.json" not in selected:
        raise ValueError("Backup source has no rooms.json; refusing incomplete export")
    if sum(map(len, selected.values())) > MAX_BUNDLE:
        raise ValueError("Backup source is too large")
    return selected


def create_bundle(root: Path, passphrase: str, *, config_file: Path | None = None) -> bytes:
    selected = collect(root)
    if config_file is not None:
        if not config_file.is_file() or config_file.is_symlink():
            raise ValueError('Configured app environment file not readable or is a symlink')
        selected['config/app.env'] = _read_file(config_file, 'config/app.env')
    index = {"schema": 1, "files": [
        {"path": name, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
        for name, data in sorted(selected.items())
    ]}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(index, sort_keys=True))
        for name, data in sorted(selected.items()):
            z.writestr("data/" + name, data)
    salt, nonce = os.urandom(16), os.urandom(12)
    return MAGIC + salt + nonce + AESGCM(_key(passphrase, salt)).encrypt(
        nonce, buffer.getvalue(), MAGIC
    )


def verify_bundle(blob: bytes, passphrase: str) -> dict[str, bytes]:
    if not blob.startswith(MAGIC) or len(blob) < len(MAGIC) + 16 + 12 + 16:
        raise ValueError("Invalid archive header")
    if len(blob) > MAX_BUNDLE:
        raise ValueError("Encrypted backup too large")
    marker = len(MAGIC)
    salt, nonce = blob[marker:marker + 16], blob[marker + 16:marker + 28]
    try:
        clear = AESGCM(_key(passphrase, salt)).decrypt(
            nonce, blob[marker + 28:], MAGIC
        )
    except InvalidTag as exc:
        raise ValueError("Wrong passphrase or corrupted archive") from exc
    files = {}
    with zipfile.ZipFile(io.BytesIO(clear)) as z:
        index = json.loads(z.read("manifest.json"))
        if index.get("schema") != 1:
            raise ValueError("Unknown backup schema")
        entries = index.get("files", [])
        if not isinstance(entries, list) or len(entries) > 10000:
            raise ValueError("Invalid archive file list")
        names = [item["path"] for item in entries]
        if len(names) != len(set(names)) or "rooms.json" not in names:
            raise ValueError("Missing/duplicate critical data")
        if set(z.namelist()) != {"manifest.json"} | {"data/" + n for n in names}:
            raise ValueError("Unexpected archive members")
        total = 0
        for item in entries:
            name = item["path"]
            if not _allowed(name):
                raise ValueError("Unsafe archive path")
            if item["size"] > MAX_FILE:
                raise ValueError("Oversized data")
            content = z.read("data/" + name)
            total += len(content)
            if total > MAX_BUNDLE or len(content) != item["size"]:
                raise ValueError("Archive size mismatch")
            if hashlib.sha256(content).hexdigest() != item["sha256"]:
                raise ValueError("Archive checksum mismatch")
            files[name] = content
    return files


def stage_restore(blob: bytes, passphrase: str, target: Path) -> int:
    """Restore into a NEW directory only, never to the running data root."""
    files = verify_bundle(blob, passphrase)
    if target.exists() or target.resolve() == Path("/var/lib/135er-grow-central"):
        raise ValueError("Restore destination must not exist")
    target.mkdir(mode=0o700, parents=False)
    for name, data in files.items():
        destination = target / name
        destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
    return len(files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    task = parser.add_mutually_exclusive_group(required=True)
    task.add_argument("--create", type=Path, help="create encrypted file (must not exist)")
    task.add_argument("--verify", type=Path, help="check archive encryption and hashes")
    task.add_argument("--stage-restore", type=Path, help="existing archive path")
    parser.add_argument("--data-root", type=Path, default=Path("/var/lib/135er-grow-central"))
    parser.add_argument("--staging-dir", type=Path, help="new, nonexisting destination for --stage-restore")
    parser.add_argument("--config-file", type=Path, help="encrypted export of the appliance app .env for full restore")
    args = parser.parse_args()
    password = getpass.getpass("Backup passphrase: ")
    if args.create:
        confirmation = getpass.getpass("Repeat backup passphrase: ")
        if password != confirmation:
            parser.error("Passphrases differ")
        output = create_bundle(args.data_root, password, config_file=args.config_file)
        fd = os.open(args.create, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(output)
        print("Encrypted backup created; remember your passphrase")
    else:
        source = args.verify or args.stage_restore
        blob = source.read_bytes()
        if args.verify:
            print(f"Verified encrypted archive with {len(verify_bundle(blob, password))} files")
        else:
            if args.staging_dir is None:
                parser.error("--staging-dir is required for staged restore")
            count = stage_restore(blob, password, args.staging_dir)
            print(f"Staged {count} files; live Grow-Central data unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
