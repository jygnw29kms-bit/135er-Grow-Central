"""Authenticated native sensor messages; a device ID alone is never a credential."""
from __future__ import annotations
import base64
import hashlib
from dataclasses import dataclass
import json
import re
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

ALGORITHM = 'ecdsa-p256-sha256'
MAX_MESSAGE_BYTES = 8192

@dataclass(frozen=True)
class SignedMessage:
    device_id: str
    kind: str
    sequence: int
    body: dict
    public_key: str
    fingerprint: str
    digest: str


def verify_message(payload: bytes | str, *, kind: str, device_id: str | None = None) -> SignedMessage:
    try:
        if len(payload) > MAX_MESSAGE_BYTES:
            raise ValueError('sensor message too large')
        envelope = json.loads(payload)
        if not isinstance(envelope, dict) or envelope.get('schema') != 'gc-signed-v1' or envelope.get('algorithm') != ALGORITHM:
            raise ValueError('signed sensor identity required')
        raw_key = base64.b64decode(envelope['public_key'], validate=True)
        key = serialization.load_der_public_key(raw_key)
        if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(key.curve, ec.SECP256R1):
            raise ValueError('sensor identity must use P-256')
        message = envelope['message']
        if not isinstance(message, str):
            raise ValueError('invalid signed message')
        raw = message.encode('utf-8')
        if len(raw) > MAX_MESSAGE_BYTES:
            raise ValueError('sensor message too large')
        key.verify(base64.b64decode(envelope['signature'], validate=True), raw, ec.ECDSA(hashes.SHA256()))
        data = json.loads(message)
        if not isinstance(data, dict) or data.get('kind') != kind:
            raise ValueError('sensor message kind mismatch')
        if device_id is not None and data.get('device_id') != device_id:
            raise ValueError('sensor identity does not match topic')
        from .gc_esp32_protocol import device_topic
        identity = data['device_id']
        if kind == 'ble_proof':
            if not isinstance(identity, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{1,63}', identity):
                raise ValueError('invalid Grow Central BLE identity')
        else:
            device_topic('growcentral/v1', identity, kind)
        sequence = data['seq']
        if type(sequence) is not int or not 0 < sequence <= 2**53 - 1:
            raise ValueError('invalid sensor sequence')
        if not isinstance(data.get('body'), dict):
            raise ValueError('sensor body must be an object')
        canonical = key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        return SignedMessage(identity, kind, sequence, data['body'], base64.b64encode(canonical).decode(),
                             hashlib.sha256(canonical).hexdigest(), hashlib.sha256(raw).hexdigest())
    except (KeyError, TypeError, ValueError, InvalidSignature, UnsupportedAlgorithm, UnicodeError) as exc:
        raise ValueError('invalid or unsigned sensor identity') from exc
