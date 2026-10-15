"""Persistent Ed25519 identity for one Grow Central Raspberry Pi installation.

The universal image clears /etc/machine-id before distribution, so the machine
ID is regenerated per installation. The private key is generated locally with
0600 permissions and never leaves the Pi; only its raw public key is sent to
the Grow Central cloud authorization endpoint.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import NamedTuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

IDENTITY_DIR = Path(os.getenv("GC_CLOUD_IDENTITY_DIR", "/var/lib/135er-grow-central/cloud-identity"))
PRIVATE_KEY_FILE = Path(os.getenv("GC_CLOUD_DEVICE_KEY_FILE", str(IDENTITY_DIR / "device-ed25519.key")))
PUBLIC_KEY_FILE = Path(os.getenv("GC_CLOUD_DEVICE_PUBLIC_KEY_FILE", str(IDENTITY_DIR / "device-ed25519.pub")))
DEVICE_ID_FILE = Path(os.getenv("GC_CLOUD_DEVICE_ID_FILE", str(IDENTITY_DIR / "device-id")))
MACHINE_ID_FILE = Path(os.getenv("GC_MACHINE_ID_FILE", "/etc/machine-id"))


class DeviceIdentity(NamedTuple):
    hardware_guid: str
    public_key: str
    private_key: Ed25519PrivateKey
    device_id: str | None


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.strip() + "=" * (-len(value.strip()) % 4))


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def hardware_guid() -> str:
    configured = os.getenv("GC_HARDWARE_GUID", "").strip()
    if configured:
        return configured
    machine_id = _read(MACHINE_ID_FILE)
    if len(machine_id) < 16:
        raise RuntimeError("stable machine-id unavailable")
    return f"gc-pi-{machine_id}"


def load_private_key() -> Ed25519PrivateKey | None:
    key_text = os.getenv("GC_PLATFORM_PRIVATE_KEY", "").strip() or _read(PRIVATE_KEY_FILE)
    if not key_text:
        return None
    try:
        raw = _b64decode(key_text)
        if len(raw) != 32:
            return None
        return Ed25519PrivateKey.from_private_bytes(raw)
    except (ValueError, TypeError):
        return None


def ensure_identity() -> DeviceIdentity:
    """Return a stable local identity, generating the private key if needed."""
    IDENTITY_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(IDENTITY_DIR, 0o700)
    except OSError:
        pass

    private_key = load_private_key()
    if private_key is None:
        private_key = Ed25519PrivateKey.generate()
        raw_private = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        PRIVATE_KEY_FILE.write_text(_b64encode(raw_private) + "\n", encoding="utf-8")
        os.chmod(PRIVATE_KEY_FILE, 0o600)

    raw_public = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    public_key = _b64encode(raw_public)
    PUBLIC_KEY_FILE.write_text(public_key + "\n", encoding="utf-8")
    os.chmod(PUBLIC_KEY_FILE, 0o644)

    configured_device_id = os.getenv("GC_PLATFORM_DEVICE_ID", "").strip()
    device_id = configured_device_id or _read(DEVICE_ID_FILE) or None
    if device_id is not None and len(device_id) != 36:
        device_id = None

    return DeviceIdentity(hardware_guid(), public_key, private_key, device_id)


def save_device_id(device_id: str) -> None:
    if len(device_id.strip()) != 36:
        raise ValueError("invalid cloud device id")
    IDENTITY_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    DEVICE_ID_FILE.write_text(device_id.strip() + "\n", encoding="utf-8")
    os.chmod(DEVICE_ID_FILE, 0o600)
