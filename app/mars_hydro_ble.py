"""Safe, local-first Mars Hydro BLE investigation for FC3000 and DF150-M.

No GATT writes are available here. Device identity and protocol have not yet
been verified on the user's real hardware. Scans, reads and notifications are
diagnostics only, not proof of a functioning remote-control protocol.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from typing import Any

from bleak import BleakClient, BleakScanner
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.security import require_write_auth

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/mars-hydro/ble",
    tags=["Mars Hydro BLE diagnostics"],
    dependencies=[Depends(require_write_auth)],
)

# Discover does not grant the device trust or write access. IDs are ephemeral
# handles to addresses observed by the local Pi, not persistent identifiers.
_candidates: dict[str, tuple[str, str, float]] = {}
_capture_lock = asyncio.Lock()
_CANDIDATE_TTL = 180.0
_MAX_PAYLOAD = 128
_UUID = re.compile(r"^(?:[0-9a-fA-F]{4}|[0-9a-fA-F]{8}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$")
MARS_HINTS = ("mars", "mh-", "mzf", "ifresh", "iconnect", "fc3000", "df150", "c260")


class InspectRequest(BaseModel):
    candidate_id: str = Field(pattern=r"^[a-f0-9]{20}$")


class ObserveRequest(InspectRequest):
    characteristic_uuid: str = Field(min_length=4, max_length=36)
    seconds: float = Field(default=4.0, ge=0.5, le=8.0)


def _id(address: str) -> str:
    return hashlib.sha256(address.encode()).hexdigest()[:20]


def _candidate(candidate_id: str) -> str:
    row = _candidates.get(candidate_id)
    if row is None or time.monotonic() - row[2] > _CANDIDATE_TTL:
        _candidates.pop(candidate_id, None)
        raise HTTPException(409, "Gerät erneut suchen: Bluetooth-Fund ist abgelaufen.")
    return row[0]


def _payload(data: bytes) -> dict[str, Any]:
    sample = bytes(data[:_MAX_PAYLOAD])
    result: dict[str, Any] = {
        "hex": sample.hex(" "),
        "length": len(data),
        "truncated": len(data) > _MAX_PAYLOAD,
    }
    try:
        text = sample.decode("utf-8")
        if text.isprintable():
            result["text"] = text
    except UnicodeDecodeError:
        pass
    return result


def _services(client: BleakClient) -> list[dict[str, Any]]:
    result = []
    for service in client.services:
        characteristics = []
        for characteristic in service.characteristics:
            characteristics.append({
                "uuid": str(characteristic.uuid).lower(),
                "properties": sorted(str(p).lower() for p in characteristic.properties),
                "handle": characteristic.handle,
            })
        result.append({"uuid": str(service.uuid).lower(), "characteristics": characteristics})
    return result


def _characteristic(services: list[dict[str, Any]], uuid: str, property_name: str) -> str:
    for service in services:
        for char in service["characteristics"]:
            if char["uuid"] == uuid and property_name in char["properties"]:
                return char["uuid"]
    raise HTTPException(422, f"Characteristic unbekannt oder nicht '{property_name}'-fähig.")


@router.get("/status")
def status():
    return {
        "transport": "bluetooth",
        "models": ["FC3000", "DF150-M"],
        "discovery": "available",
        "gatt_read": "available_when_characteristic_supports_read",
        "notifications": "available_when_characteristic_supports_notify",
        "control": "blocked_pending_model_specific_validation",
        "protocol_validated": False,
        "cloud_required": False,
        "wifi_required_for_ble": False,
        "note": "GATT-Rohdaten sind keine bestätigten Licht-/Lüfterwerte.",
    }


@router.post("/scan")
async def scan(seconds: float = 5.0):
    timeout = min(max(seconds, 1.0), 12.0)
    try:
        results = await BleakScanner.discover(timeout=timeout, return_adv=True)
    except Exception as exc:
        logger.warning("Mars BLE scan failed: %s", type(exc).__name__)
        raise HTTPException(503, "Bluetooth-Scan fehlgeschlagen; Pi-Funk und BlueZ prüfen.") from exc
    now = time.monotonic()
    rows = []
    for address, (device, adv) in results.items():
        name = str(adv.local_name or device.name or "").strip()[:100]
        service_uuids = [str(x).lower() for x in (adv.service_uuids or [])][:24]
        manufacturer_ids = sorted(int(x) for x in (adv.manufacturer_data or {}))[:16]
        candidate_id = _id(str(address))
        _candidates[candidate_id] = (str(address), name, now)
        rows.append({
            "candidate_id": candidate_id,
            "name": name or "Unbekanntes BLE-Gerät",
            "rssi": getattr(adv, "rssi", None),
            "service_uuids": service_uuids,
            "manufacturer_ids": manufacturer_ids,
            "mars_hydro_hint": any(hint in name.lower() for hint in MARS_HINTS),
            "identity_verified": False,
        })
    for key, row in list(_candidates.items()):
        if now - row[2] > _CANDIDATE_TTL:
            _candidates.pop(key, None)
    rows.sort(key=lambda x: (not x["mars_hydro_hint"], -(x["rssi"] or -999)))
    return {"devices": rows, "read_only": True, "found": len(rows)}


@router.post("/inspect")
async def inspect(body: InspectRequest):
    address = _candidate(body.candidate_id)
    if _capture_lock.locked():
        raise HTTPException(409, "Eine andere Bluetooth-Diagnose läuft bereits.")
    async with _capture_lock:
        try:
            async with BleakClient(address, timeout=12.0) as client:
                services = _services(client)
                values = []
                for service in services:
                    for char in service["characteristics"]:
                        if "read" not in char["properties"]:
                            continue
                        try:
                            raw = await asyncio.wait_for(client.read_gatt_char(char["uuid"]), timeout=3.0)
                            values.append({"uuid": char["uuid"], "value": _payload(raw), "ok": True})
                        except Exception as exc:
                            values.append({"uuid": char["uuid"], "ok": False, "error": type(exc).__name__})
                        if len(values) >= 48:
                            break
                    if len(values) >= 48:
                        break
                return {
                    "candidate_id": body.candidate_id,
                    "name": _candidates[body.candidate_id][1],
                    "connected": True,
                    "identity_verified": False,
                    "protocol_validated": False,
                    "services": services[:40],
                    "reads": values,
                    "write_attempted": False,
                }
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Mars BLE inspect failed: %s", type(exc).__name__)
            raise HTTPException(502, "GATT-Auslesen fehlgeschlagen. Hersteller-App trennen und Gerät erneut suchen.") from exc


@router.post("/observe")
async def observe(body: ObserveRequest):
    address = _candidate(body.candidate_id)
    uuid = body.characteristic_uuid.lower()
    if not _UUID.fullmatch(uuid):
        raise HTTPException(422, "Ungültige Characteristic-UUID.")
    if _capture_lock.locked():
        raise HTTPException(409, "Eine andere Bluetooth-Diagnose läuft bereits.")
    async with _capture_lock:
        events: list[dict[str, Any]] = []
        try:
            async with BleakClient(address, timeout=12.0) as client:
                services = _services(client)
                _characteristic(services, uuid, "notify")
                def capture(_sender: Any, data: bytearray):
                    if len(events) < 80:
                        events.append({"index": len(events) + 1, "elapsed_s": round(time.monotonic() - started, 3), "value": _payload(data)})
                started = time.monotonic()
                await client.start_notify(uuid, capture)
                try:
                    await asyncio.sleep(body.seconds)
                finally:
                    await client.stop_notify(uuid)
                return {
                    "candidate_id": body.candidate_id,
                    "uuid": uuid,
                    "duration_s": round(body.seconds, 2),
                    "events": events,
                    "event_count": len(events),
                    "write_attempted": False,
                    "meaning": "undecoded_raw_notifications",
                }
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Mars BLE observe failed: %s", type(exc).__name__)
            raise HTTPException(502, "Bluetooth-Benachrichtigungen konnten nicht gelesen werden.") from exc


@router.post("/control-test")
async def control_test():
    # The previous DF100M hypotheses and Mars Pro cloud commands MUST NOT
    # be replayed on an unverified FC3000 or DF150-M.
    raise HTTPException(403, "Steuerung gesperrt: FC3000-/DF150-M-BLE-Protokoll noch nicht validiert.")
