"""Fresh physical USB identity proof used only as MQTT onboarding fallback.

This does not weaken sensor trust: USBSerial.proof() already issues a fresh
256-bit nonce and verifies the signed P-256 response, firmware, model and
announcement identity. The fallback is available only while the exact sensor is
physically connected to the Pi over an allowlisted serial interface.
"""
from __future__ import annotations

from dataclasses import dataclass

import serial

from .usb import USBSerial, ports, resolve


@dataclass(frozen=True)
class UsbIdentityProof:
    device_id: str
    public_key: str
    fingerprint: str
    hardware_uid: str
    firmware: str
    calibration: dict


def prove_connected_device(device_id: str) -> UsbIdentityProof:
    """Return a fresh verified proof for one physically attached sensor."""
    saw_candidate = False
    for candidate in ports():
        saw_candidate = True
        try:
            with USBSerial(resolve(candidate["id"])) as connection:
                proof, announce = connection.proof()
        except (OSError, TimeoutError, ValueError, serial.SerialException):
            continue
        if proof.device_id != device_id or announce.id != device_id:
            continue
        return UsbIdentityProof(
            device_id=device_id,
            public_key=proof.public_key,
            fingerprint=proof.fingerprint,
            hardware_uid=announce.hardware_uid or "",
            firmware=announce.firmware,
            calibration=dict(announce.calibration or {}),
        )
    if not saw_candidate:
        raise TimeoutError("no supported Grow Central sensor is attached over USB")
    raise TimeoutError("attached USB sensor did not prove the requested identity")
