"""Safe, local-first Mars Hydro BLE investigation for FC3000 and DF150-M.

No GATT writes are available here. Device identity and protocol have not yet
been verified on the user's real hardware. Scans, reads and notifications are
diagnostics only, not proof of a functioning remote-control protocol.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import subprocess
import time
from typing import Any, Literal

from bleak import BleakClient, BleakScanner
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.security import require_write_auth
from app.mars_legacy_telemetry import mzf002_telemetry, fc3000_telemetry
from app.mars_fc3000_trial import context_from_live_status, encode_command
from app.mars_wifi_probe import wifi_status

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


class LampControlTrialRequest(InspectRequest):
    action: Literal["power", "brightness"]
    value: int = Field(ge=0, le=100)
    confirm_physical_change: bool = False


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


# Model-family suggestions are advertising-name hints, not verified identities.
# The observed MZF002 GATT service is an exact hardware match; the physical
# model and sensor payload format remain unverified.
MZF002_SERVICE = "83677baa-3eb8-4866-b6b6-96e5ed5cc48d"
MZF002_NOTIFY = "6f588463-f8f1-44f8-bdae-a1272a1b0f6e"
MZF002_WRITE = "f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d"


def device_family(name: str, manufacturer_ids: list[int]) -> dict[str, Any]:
    lowered = name.lower()
    if "mz_mars_" in lowered or "c260" in lowered:
        return {
            "family": "mars_hydro_lighting_candidate",
            "label": "Mars Hydro Licht (C260-Kandidat)",
            "target_role": "light",
            "identity_verified": False,
            "control_validated": False,
        }
    if "mzf002" in lowered or "df150" in lowered:
        return {
            "family": "mars_hydro_ventilation_candidate",
            "label": "Mars Hydro Lüfter (MZF002-Kandidat)",
            "target_role": "fan",
            "identity_verified": False,
            "control_validated": False,
        }
    return {
        "family": "unclassified_ble",
        "label": "Unbekanntes Bluetooth-Gerät",
        "target_role": "unknown",
        "identity_verified": False,
        "control_validated": False,
    }


def summarize_gatt_services(services: list[dict[str, Any]]) -> dict[str, Any]:
    """Report proven GATT capabilities, never guessed fan or lamp measurements."""
    service_uuids = {service["uuid"] for service in services}
    chars = {char["uuid"]: set(char["properties"])
             for service in services for char in service["characteristics"]}
    confirmed = MZF002_SERVICE in service_uuids and (
        "notify" in chars.get(MZF002_NOTIFY, set())
        and "write" in chars.get(MZF002_WRITE, set())
    )
    return {
        "mzf002_transport_confirmed": confirmed,
        "notify_uuid": MZF002_NOTIFY if confirmed else None,
        "write_uuid": MZF002_WRITE if confirmed else None,
        "readable_count": sum("read" in props for props in chars.values()),
        "notifiable_count": sum("notify" in props for props in chars.values()),
        "control_validated": False,
        "sensor_values_decoded": False,
    }


def _transport_error(exc: Exception, stage: str) -> str:
    """Present a bounded, non-secret diagnostic instead of a generic HTTP 502."""
    error_type = type(exc).__name__
    # BlueZ frequently reports disconnects as BleakDBusError or EOFError.
    if error_type in {"BleakDBusError", "EOFError", "BleakDeviceNotFoundError"}:
        reason = "BlueZ-Verbindung während " + stage + " getrennt oder nicht mehr vorhanden."
    elif isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        reason = "Zeitüberschreitung bei " + stage + "."
    else:
        reason = "GATT-Kommunikation bei " + stage + " fehlgeschlagen."
    return (
        f"{reason} ({error_type}). Gerät eingeschaltet lassen, andere "
        "Bluetooth-Verbindungen zum Gerät beenden und erneut suchen."
    )


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


def _command(*args: str) -> tuple[int, str]:
    """Bounded read-only BlueZ diagnostics, with no shell or state changes."""
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=4, check=False)
        return result.returncode, (result.stdout + "\n" + result.stderr)[:3000]
    except (OSError, subprocess.TimeoutExpired):
        return -1, ""


def adapter_diagnostics() -> dict[str, Any]:
    rc, show = _command("bluetoothctl", "show")
    rc_rf, rfkill = _command("rfkill", "list", "bluetooth")
    controller = bool(re.search(r"^\s*Controller\s+", show, re.M))
    powered = bool(re.search(r"^\s*Powered:\s+yes\s*$", show, re.M | re.I))
    blocked = bool(re.search(r"^\s*(Soft|Hard) blocked:\s+yes\s*$", rfkill, re.M | re.I))
    if rc != 0 or not controller:
        state = "adapter_unavailable"
        hint = "Kein Bluetooth-Controller über BlueZ verfügbar. Pi-Adapter und bluetooth.service prüfen."
    elif blocked:
        state = "radio_blocked"
        hint = "Bluetooth ist durch rfkill gesperrt. Funkfreigabe am Pi prüfen."
    elif not powered:
        state = "adapter_off"
        hint = "Bluetooth-Adapter ist ausgeschaltet. BlueZ und Bluetooth-Initialisierung prüfen."
    else:
        state = "ready"
        hint = "Adapter bereit. BLE-Geräte müssen eingeschaltet und in Funkreichweite sein."
    return {
        "state": state,
        "controller_present": controller,
        "powered": powered,
        "rfkill_blocked": blocked,
        "bluez_accessible": rc == 0,
        "rfkill_available": rc_rf == 0,
        "hint": hint,
    }


@router.get("/status")
def status():
    return {
        "transport": "bluetooth",
        "models": ["FC3000", "DF150-M"],
        "discovery": "available_if_adapter_ready",
        "adapter": adapter_diagnostics(),
        "gatt_read": "available_when_characteristic_supports_read",
        "notifications": "available_when_characteristic_supports_notify",
        "control": "blocked_pending_model_specific_validation",
        "protocol_validated": False,
        "cloud_required": False,
        "wifi_required_for_ble": False,
        "note": "GATT-Rohdaten sind keine bestätigten Licht-/Lüfterwerte.",
    }


@router.get("/wifi-access-points")
def mars_wifi_access_points():
    """Read cached WiFi AP records without connecting, probing or modifying radio state."""
    return wifi_status()


@router.post("/scan")
async def scan(seconds: float = 8.0):
    timeout = min(max(seconds, 3.0), 15.0)
    if _capture_lock.locked():
        raise HTTPException(409, "Eine BLE-Diagnose läuft bereits. Bitte danach erneut suchen.")
    adapter = adapter_diagnostics()
    if adapter["state"] != "ready":
        return {"devices": [], "found": 0, "read_only": True,
                "adapter": adapter, "scan_seconds": 0, "attempts": 0,
                "message": adapter["hint"]}
    results: dict[str, Any] = {}
    attempts = 0
    try:
        # A generic iPhone or sensor almost always advertises immediately.
        # Stopping after *any* device made the C260 lamp disappear from
        # scans even while MZF002 was reliably visible. Use both passes unless
        # we have evidence of both Mars families, and merge across passes.
        for attempt in range(2):
            attempts += 1
            seen = await BleakScanner.discover(timeout=timeout, return_adv=True)
            results.update(seen)
            names = [
                str(adv.local_name or dev.name or "").lower()
                for dev, adv in results.values()
            ]
            lamp = any("c260" in name or "mz_mars_" in name for name in names)
            fan = any("mzf002" in name or "df150" in name for name in names)
            if lamp and fan:
                break
    except Exception as exc:
        logger.warning("Mars BLE scan failed: %s", type(exc).__name__)
        raise HTTPException(503, f"BLE-Scan fehlgeschlagen ({type(exc).__name__}). BlueZ und Adapterstatus prüfen.") from exc
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
            "profile": device_family(name, manufacturer_ids),
            "identity_verified": False,
        })
    for key, row in list(_candidates.items()):
        if now - row[2] > _CANDIDATE_TTL:
            _candidates.pop(key, None)
    rows.sort(key=lambda x: (not x["mars_hydro_hint"], -(x["rssi"] or -999)))
    mars_count = sum(bool(row["mars_hydro_hint"]) for row in rows)
    message = (
        f"{len(rows)} BLE-Geräte erkannt, davon {mars_count} Mars-Hydro-Kandidaten."
        if rows else
        "Bluetooth-Adapter bereit, aber keine BLE-Werbesignale empfangen. "
        "C260/FC3000 und Lüfter einschalten, Hersteller-App trennen und erneut suchen."
    )
    return {"devices": rows, "read_only": True, "found": len(rows),
            "adapter": adapter, "attempts": attempts,
            "scan_seconds": timeout * attempts, "mars_candidate_count": mars_count,
            "message": message}


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
                    "capabilities": summarize_gatt_services(services),
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
                stage = "Notify-Start"
                subscribed = False
                try:
                    await asyncio.wait_for(client.start_notify(uuid, capture), timeout=6.0)
                    subscribed = True
                    stage = "Notify-Beobachtung"
                    await asyncio.sleep(body.seconds)
                except Exception as exc:
                    logger.warning("Mars BLE observe stage=%s failure=%s", stage, type(exc).__name__)
                    raise HTTPException(502, _transport_error(exc, stage)) from exc
                finally:
                    if subscribed and getattr(client, "is_connected", True):
                        try:
                            await asyncio.wait_for(client.stop_notify(uuid), timeout=3.0)
                        except Exception as exc:
                            logger.warning("Mars BLE notify cleanup failure=%s", type(exc).__name__)
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
            raise HTTPException(502, _transport_error(exc, "Verbindungsaufbau oder Service-Erkennung")) from exc


@router.post("/observe-fan-telemetry")
async def observe_fan_telemetry(body: InspectRequest):
    """Opt-in read-only MZF002 observation; no raw identifiers are returned.

    The iPhone's exclusive BLE connection must be disconnected before running
    this endpoint from the Pi. A successful connection proves neither device
    identity nor permission to issue commands.
    """
    address = _candidate(body.candidate_id)
    row = _candidates.get(body.candidate_id)
    if not row or device_family(row[1], [])["target_role"] != "fan":
        raise HTTPException(422, "Nur ein erneut gesuchter MZF002-Luefterkandidat ist erlaubt.")
    if _capture_lock.locked():
        raise HTTPException(409, "Eine andere BLE-Diagnose laeuft bereits.")
    async with _capture_lock:
        samples: list[dict[str, Any]] = []
        try:
            async with BleakClient(address, timeout=12.0) as client:
                services = _services(client)
                _characteristic(services, MZF002_NOTIFY, "notify")
                def capture(_sender: Any, data: bytearray):
                    if len(samples) >= 12:
                        return
                    value = mzf002_telemetry(bytes(data))
                    if value is not None:
                        samples.append(value)
                subscribed = False
                try:
                    await asyncio.wait_for(client.start_notify(MZF002_NOTIFY, capture), timeout=6.0)
                    subscribed = True
                    await asyncio.sleep(5.0)
                finally:
                    if subscribed and getattr(client, "is_connected", True):
                        try:
                            await asyncio.wait_for(client.stop_notify(MZF002_NOTIFY), timeout=3.0)
                        except Exception as exc:
                            logger.warning("MZF002 unsubscribe: %s", type(exc).__name__)
            return {
                "candidate_id": body.candidate_id,
                "device_family": "MZF002",
                "status": "decoded" if samples else "no_matching_telemetry",
                "latest": samples[-1] if samples else None,
                "sample_count": len(samples),
                "identity_verified": False,
                "control_enabled": False,
                "raw_payload_returned": False,
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("MZF002 telemetry observe failed: %s", type(exc).__name__)
            raise HTTPException(502, _transport_error(exc, "MZF002-Statusbeobachtung")) from exc


@router.post("/observe-lamp-telemetry")
async def observe_lamp_telemetry(body: InspectRequest):
    """Read actual FC3000 On/Off and brightness from captured-family BLE notifications.

    Does not authenticate or issue any device control commands. Device identity
    must still be verified separately before write access can ever be enabled.
    """
    address = _candidate(body.candidate_id)
    row = _candidates.get(body.candidate_id)
    if not row or device_family(row[1], [])["target_role"] != "light":
        raise HTTPException(422, "Nur ein erneut erkannter FC3000/C260-Lichtkandidat ist erlaubt.")
    if _capture_lock.locked():
        raise HTTPException(409, "Eine andere Bluetooth-Diagnose läuft bereits.")
    async with _capture_lock:
        samples: list[dict[str, Any]] = []
        try:
            async with BleakClient(address, timeout=12.0) as client:
                services = _services(client)
                _characteristic(services, MZF002_NOTIFY, "notify")
                def capture(_sender: Any, data: bytearray):
                    if len(samples) >= 12:
                        return
                    value = fc3000_telemetry(bytes(data))
                    if value is not None:
                        samples.append(value)
                subscribed = False
                try:
                    await asyncio.wait_for(client.start_notify(MZF002_NOTIFY, capture), timeout=6.0)
                    subscribed = True
                    await asyncio.sleep(5.0)
                finally:
                    if subscribed and getattr(client, "is_connected", True):
                        try:
                            await asyncio.wait_for(client.stop_notify(MZF002_NOTIFY), timeout=3.0)
                        except Exception as exc:
                            logger.warning("FC3000 notify cleanup failure: %s", type(exc).__name__)
            return {
                "candidate_id": body.candidate_id,
                "device_family": "MARS",
                "status": "decoded" if samples else "no_matching_telemetry",
                "latest": samples[-1] if samples else None,
                "sample_count": len(samples),
                "identity_verified": False,
                "control_enabled": False,
                "raw_payload_returned": False,
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("FC3000 telemetry observe failed: %s", type(exc).__name__)
            raise HTTPException(502, _transport_error(exc, "FC3000-Statusbeobachtung")) from exc


@router.post("/control-lamp-trial")
async def control_lamp_trial(body: LampControlTrialRequest):
    """Opt-in, single-action owner test for exactly one FC3000 V3.4.

    Never sends a command without a fresh MARS status notification; rejects
    old tokens, unmatched devices, wrong firmware, parallel BLE operations,
    unauthenticated requests and unconfirmed physical actions.
    """
    allowed_id = os.environ.get("GC_FC3000_ALLOWED_ID", "").strip().upper()
    if os.environ.get("GC_FC3000_CONTROL_TRIAL") != "1":
        raise HTTPException(403, "FC3000 Hardware-Test nicht freigeschaltet.")
    if not re.fullmatch(r"FC[A-F0-9]{10}", allowed_id):
        raise HTTPException(403, "FC3000-Gerätekennung fehlt.")
    if not body.confirm_physical_change:
        raise HTTPException(428, "Explizite Bestätigung der physischen Lichtänderung erforderlich.")
    if body.action == "power" and body.value not in (0, 1):
        raise HTTPException(422, "Ein/Aus nur 0 oder 1.")
    if body.action == "brightness" and not 10 <= body.value <= 100:
        raise HTTPException(422, "Dimmung nur 10 bis 100 Prozent.")
    if _capture_lock.locked():
        raise HTTPException(409, "Bluetooth-Gerät ist bereits belegt.")

    address = _candidate(body.candidate_id)
    candidate = _candidates.get(body.candidate_id)
    if not candidate or candidate[1].upper() != "MZ_MARS_0_" + allowed_id:
        raise HTTPException(403, "Lampenidentität stimmt nicht mit dem Privatgerät überein.")

    async with _capture_lock:
        entries: list[tuple[str, dict[str, Any]]] = []
        try:
            async with BleakClient(address, timeout=12.0) as client:
                services = _services(client)
                _characteristic(services, MZF002_NOTIFY, "notify")
                _characteristic(services, MZF002_WRITE, "write")

                def on_notify(_sender: Any, data: bytearray) -> None:
                    context = context_from_live_status(bytes(data))
                    if context is not None and len(entries) < 40:
                        entries.append(context)

                started = False
                try:
                    await asyncio.wait_for(client.start_notify(MZF002_NOTIFY, on_notify), timeout=6)
                    started = True
                    # A fresh genuine 19-field MARS notification is mandatory.
                    for _ in range(30):
                        if entries:
                            break
                        await asyncio.sleep(0.5)
                    if not entries:
                        raise HTTPException(409, "Keine frische FC3000-Statusmeldung. Kein Steuerbefehl gesendet.")
                    code, previous = entries[-1]
                    packet = encode_command(
                        code=code, device_id=allowed_id,
                        action=body.action, value=body.value)
                    count_before = len(entries)
                    await asyncio.wait_for(
                        client.write_gatt_char(MZF002_WRITE, packet, response=True),
                        timeout=5,
                    )
                    # The write is NOT proof of physical effect: wait for a new
                    # status reflecting the requested value, without retries.
                    confirmed = False
                    latest = None
                    for _ in range(16):
                        await asyncio.sleep(0.5)
                        for _, reported in entries[count_before:]:
                            latest = reported
                            if (body.action == "power"
                                and reported["power_on"] == (body.value == 1)):
                                confirmed = True
                            if (body.action == "brightness"
                                and reported["brightness_percent"] == body.value):
                                confirmed = True
                        if confirmed:
                            break
                    return {
                        "command_sent": True,
                        "device_report_confirmed": confirmed,
                        "action": body.action,
                        "requested_value": body.value,
                        "latest": latest,
                        "retry_attempted": False,
                        "physical_effect_independently_verified": False,
                        "message": ("FC3000 meldet den angeforderten Wert."
                                    if confirmed else
                                    "Befehl übertragen, Bestätigung fehlt. Nicht blind wiederholen."),
                    }
                finally:
                    if started and getattr(client, "is_connected", True):
                        try:
                            await asyncio.wait_for(client.stop_notify(MZF002_NOTIFY), timeout=3)
                        except Exception:
                            logger.warning("FC3000 trial notify cleanup error")
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("FC3000 trial stage=%s", type(exc).__name__)
            raise HTTPException(502, "FC3000-Transaktion fehlgeschlagen; keine automatische Wiederholung.") from exc


@router.post("/control-test")
async def control_test():
    # The previous DF100M hypotheses and Mars Pro cloud commands MUST NOT
    # be replayed on an unverified FC3000 or DF150-M.
    raise HTTPException(403, "Steuerung gesperrt: FC3000-/DF150-M-BLE-Protokoll noch nicht validiert.")
