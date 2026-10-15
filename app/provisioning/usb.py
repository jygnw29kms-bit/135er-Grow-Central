"""USB candidates, trusted bundled firmware and guided local provisioning."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field, SecretStr, field_validator
import serial
from serial.tools import list_ports

from app.security import require_write_auth
from app.audit import append_audit
from app.devices.gc_identity import verify_message
from app.devices.gc_esp32_protocol import parse_announcement
from app.devices.gc_trust import TrustStore
from .broker import request_broker

class USBRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()
        async def sanitized(request):
            try:
                return await handler(request)
            except RequestValidationError as exc:
                # Pydantic errors otherwise echo submitted password values.
                raise HTTPException(422, 'Eingaben prüfen: Board, WLAN, Kennwort, Name und Raum.') from exc
        return sanitized


router = APIRouter(prefix='/api/devices/usb', route_class=USBRoute, tags=['USB sensor setup'], dependencies=[Depends(require_write_auth)])
VERSION = '0.5.1'
MODEL = 'GC-SOIL-XIAO-C3-HW390'
SUPPORTED = {(0x303a, 0x1001), (0x1a86, 0x7523), (0x1a86, 0x55d4), (0x10c4, 0xea60), (0x2886, 0x0044), (0x2886, 0x0056)}
OFFSETS = {'bootloader.bin': 0, 'partitions.bin': 0x8000, 'boot_app0.bin': 0xe000, 'firmware.bin': 0x10000}
LIMITS = {'bootloader.bin': 0x8000, 'partitions.bin': 0x1000, 'boot_app0.bin': 0x2000, 'firmware.bin': 0x1B0000}


def version_tuple(value: str) -> tuple[int, ...]:
    if not re.fullmatch(r'\d+(?:\.\d+){1,3}', value or ''):
        raise ValueError('Ungültige Sensor-Firmwareversion.')
    return tuple(int(part) for part in value.split('.'))


def installed_firmware(path: str) -> str | None:
    try:
        with USBSerial(path) as connection:
            line = connection.command('INFO', lambda value: bool(re.search(r'\bfirmware=\d+(?:\.\d+){1,3}\b', value)), timeout=3)
        match = re.search(r'\bfirmware=(\d+(?:\.\d+){1,3})\b', line)
        return match.group(1) if match else None
    except (OSError, TimeoutError, ValueError, serial.SerialException):
        return None


def ensure_not_downgrade(path: str) -> str | None:
    installed = installed_firmware(path)
    if installed and version_tuple(installed) > version_tuple(VERSION):
        raise DeviceBlocked(f'Sensor-Firmware {installed} ist neuer als das gebündelte Paket {VERSION}; Downgrade blockiert.')
    return installed


class DeviceBlocked(PermissionError):
    """Persistent trust/key denial, distinct from OS USB access permissions."""


def ports():
    result = []
    for port in list_ports.comports():
        if (port.vid, port.pid) not in SUPPORTED or not re.fullmatch(r'/dev/tty(?:ACM|USB)\d+', port.device):
            continue
        identity = f'{port.vid:x}:{port.pid:x}:{port.serial_number or ""}:{port.location or port.device}'
        result.append({'id': hashlib.sha256(identity.encode()).hexdigest()[:24], 'port': port.device,
            'label': port.description or 'ESP32 USB-Kandidat', 'serial': port.serial_number or '',
            'vid': port.vid, 'pid': port.pid})
    return result


def resolve(port_id):
    for port in ports():
        if port['id'] == port_id:
            if not stat.S_ISCHR(os.stat(port['port']).st_mode):
                raise ValueError('Kein serielles USB-Gerät.')
            return port['port']
    raise ValueError('USB-Gerät getrennt. Wieder anschließen und erneut prüfen.')


def firmware_files():
    root = Path(os.getenv('GC_USB_FIRMWARE_DIR', str(Path(__file__).resolve().parents[2] / 'firmware/gc-soil-node/dist'))).resolve()
    manifest = json.loads((root / 'manifest.json').read_text())
    if not isinstance(manifest, dict) or manifest.get('version') != VERSION or manifest.get('chip') != 'esp32c3' or manifest.get('model') != MODEL:
        raise ValueError('Firmware-Paket passt nicht zum unterstützten Sensor.')
    files = manifest.get('files', {})
    if not isinstance(files, dict) or set(files) != set(OFFSETS):
        raise ValueError('Firmware-Paket unvollständig.')
    for name, offset in OFFSETS.items():
        path = root / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > LIMITS[name] or path.stat().st_size < 1:
            raise ValueError('Ungültige Firmware-Datei.')
        if not isinstance(files[name], dict) or files[name].get('offset') != offset or hashlib.sha256(path.read_bytes()).hexdigest() != files[name].get('sha256'):
            raise ValueError('Firmware-Prüfsumme oder Speicherbereich ungültig.')
    return root


class USBSerial:
    def __init__(self, path):
        self.connection = serial.Serial(port=None, baudrate=115200, timeout=0.15, write_timeout=2)
        self.connection.dtr = False
        self.connection.rts = False
        self.connection.port = path

    def __enter__(self):
        self.connection.open()
        return self

    def __exit__(self, *args):
        self.connection.close()

    def command(self, value, match, timeout=5):
        self.connection.reset_input_buffer()
        payload = (value + '\n').encode()
        # ESP32-C3 USB/JTAG defaults to a 256-byte RX queue.
        # Pace long commands so the sensor can drain that queue.
        for offset in range(0, len(payload), 32):
            self.connection.write(payload[offset:offset + 32])
            self.connection.flush()
            if offset + 32 < len(payload):
                time.sleep(0.03)
        deadline = time.monotonic() + timeout
        total = 0
        while time.monotonic() < deadline:
            line = self.connection.readline(8193)
            total += len(line)
            if total > 32768 or len(line) > 8192:
                raise ValueError('USB-Antwort zu groß.')
            text = line.decode('utf-8', errors='replace').strip()
            if text.startswith('ERR '):
                raise ValueError('Sensor hat den Einrichtungsschritt abgelehnt.')
            if match(text):
                if value.startswith('NET CA '):
                    encoded = value[7:].strip()
                    expected = len('-----BEGIN CERTIFICATE-----\n') + len(encoded) + (len(encoded) + 63) // 64 + len('-----END CERTIFICATE-----\n')
                    status = self.command('NET INFO', lambda line: bool(re.search(r'\bca_bytes=\d+', line)))
                    actual = int(re.search(r'\bca_bytes=(\d+)', status).group(1))
                    if actual != expected:
                        raise ValueError('Sensor-CA unvollständig übertragen; USB-Einrichtung erneut versuchen.')
                return text
        raise TimeoutError('Sensor antwortet nicht. USB-Kabel und Boot-Taste prüfen.')

    def proof(self):
        nonce = secrets.token_hex(32)
        raw = self.command('USB ID ' + nonce, lambda value: value.startswith('GC_USB_ID '), timeout=8)
        proof = verify_message(raw[10:], kind='proof')
        if proof.body.get('nonce') != nonce:
            raise ValueError('USB-Identität bestätigt die Anfrage nicht.')
        announce = parse_announcement(json.dumps(proof.body.get('announcement')))
        if announce.id != proof.device_id or announce.model != MODEL or announce.firmware != VERSION:
            raise ValueError('Sensor benötigt die aktuelle Grow-Central-Firmware.')
        return proof, announce


@dataclass
class Session:
    id: str
    state: str = 'DETECTED'
    message: str = 'USB-Gerät erkannt. Boardtyp prüfen und Einrichtung starten.'
    device_id: str | None = None
    fingerprint: str | None = None
    name: str | None = None
    firmware: str | None = None
    public_key: str | None = None
    hardware_uid: str | None = None
    calibration_ready: bool = False
    air_calibrated: bool = False
    wet_calibrated: bool = False
    air_raw: int | None = None
    wet_raw: int | None = None
    busy: bool = False
    resume: str = 'FIRMWARE'
    task: asyncio.Task | None = field(default=None, repr=False)

    def public(self):
        return {key: getattr(self, key) for key in ['id', 'state', 'message', 'device_id', 'fingerprint', 'name', 'firmware', 'hardware_uid', 'calibration_ready', 'air_calibrated', 'wet_calibrated', 'air_raw', 'wet_raw', 'busy', 'resume']}


class USBManager:
    def __init__(self):
        self.sessions = {}

    def session(self, port_id):
        if not any(port['id'] == port_id for port in ports()):
            raise HTTPException(404, 'USB-Gerät nicht mehr angeschlossen.')
        return self.sessions.setdefault(port_id, Session(port_id))

    def start(self, session, operation):
        if session.busy:
            raise HTTPException(409, 'Für dieses USB-Gerät läuft bereits ein Schritt.')
        session.busy = True

        async def run():
            try:
                await operation()
            except DeviceBlocked:
                session.state = 'BLOCKED'
                session.message = 'Sperrstatus oder geänderte Identität: Entscheidung in der Sensorliste ausdrücklich prüfen und gegebenenfalls erneut freigeben.'
                append_audit('usb.setup.blocked', port_id=session.id, device_id=session.device_id)
            except (ValueError, OSError, TimeoutError, RuntimeError, subprocess.SubprocessError, serial.SerialException):
                # Never expose subprocess output or commands carrying credentials.
                session.resume = 'NETWORK' if session.state in {'PROVISIONING', 'CONNECTING', 'NETWORK'} else ('CALIBRATION' if session.state in {'CALIBRATION','CALIBRATING'} else 'FIRMWARE')
                session.state = 'ERROR'
                session.message = ('WLAN-/MQTT-Verbindung nicht bestätigt. Als Broker die LAN-IP des Pi wählen und WLAN erneut einrichten. Die geprüfte Firmware bleibt erhalten.' if session.resume == 'NETWORK' else 'USB-/Firmwareprüfung fehlgeschlagen. Verbindung und Board prüfen; nicht automatisch erneut flashen.')
                append_audit('usb.setup.failed', port_id=session.id, resume=session.resume)
            except Exception:
                session.resume = 'NETWORK' if session.state in {'PROVISIONING', 'CONNECTING', 'NETWORK', 'ASSIGN'} else ('CALIBRATION' if session.state in {'CALIBRATION','CALIBRATING'} else 'FIRMWARE')
                session.state = 'ERROR'
                session.message = 'Einrichtung fehlgeschlagen. Am aktuellen Schritt erneut versuchen; keine automatische Firmwareinstallation.'
            finally:
                session.busy = False
        session.task = asyncio.create_task(run())

    async def read_identity(self, session):
        def probe():
            with USBSerial(resolve(session.id)) as connection:
                return connection.proof()
        proof, announce = await asyncio.to_thread(probe)
        if session.public_key and session.public_key != proof.public_key:
            raise DeviceBlocked('USB-Geräteidentität wurde ausgetauscht.')
        try:
            row = await asyncio.to_thread(TrustStore().discover, announce, proof)
        except PermissionError as exc:
            raise DeviceBlocked('Gespeicherte Identität oder Sperrstatus verhindert Aufnahme.') from exc
        if row['status'] in {'REJECTED', 'REVOKED'}:
            raise DeviceBlocked('Sensor ist gesperrt; zuerst explizit erneut freigeben.')
        if not announce.hardware_uid or not re.fullmatch(r'[0-9a-f]{16}', announce.hardware_uid):
            raise DeviceBlocked('Hardware-ID fehlt oder ist ungültig.')
        if session.hardware_uid and session.hardware_uid != announce.hardware_uid:
            raise DeviceBlocked('Hardware-ID hat sich während der USB-Einrichtung geändert; möglicher Klon oder vertauschtes Gerät.')
        stored_uid = (row.get('metadata') or {}).get('hardware_uid') if isinstance(row, dict) else None
        if stored_uid and stored_uid != announce.hardware_uid:
            raise DeviceBlocked('Hardware-ID passt nicht zur gespeicherten Sensoridentität.')
        calibration = announce.calibration or {}
        session.device_id, session.public_key, session.fingerprint = proof.device_id, proof.public_key, proof.fingerprint
        session.hardware_uid = announce.hardware_uid
        session.calibration_ready = bool(calibration.get('ready'))
        session.air_calibrated = bool(calibration.get('air_done'))
        session.wet_calibrated = bool(calibration.get('wet_done'))
        session.air_raw = calibration.get('air_raw') if isinstance(calibration.get('air_raw'), int) else None
        session.wet_raw = calibration.get('wet_raw') if isinstance(calibration.get('wet_raw'), int) else None
        session.name, session.firmware = row['name'] or announce.name, announce.firmware
        return proof

    async def inspect(self, session):
        session.state, session.message = 'CHECKING', 'Firmware und USB-Identität werden geprüft…'
        try:
            await self.read_identity(session)
        except (TimeoutError, ValueError):
            session.state, session.message = 'NEEDS_FIRMWARE', 'Aktuelle Sensor-Firmware nicht bestätigt. XIAO ESP32-C3 auswählen und Firmware installieren.'
            return
        session.state, session.message = ('NETWORK', 'Kalibrierung geprüft. Jetzt Sensor mit dem WLAN verbinden.') if session.calibration_ready else ('CALIBRATION', 'Identität und Hardware-ID geprüft. Jetzt Sensor vollständig kalibrieren.')

    async def flash(self, session):
        session.state, session.message = 'FLASHING', 'Firmware wird geprüft und installiert. USB nicht trennen.'
        root = await asyncio.to_thread(firmware_files)
        path = await asyncio.to_thread(resolve, session.id)
        installed = await asyncio.to_thread(ensure_not_downgrade, path)
        append_audit('usb.flash.started', port_id=session.id, firmware=VERSION, installed_firmware=installed)
        args = [sys.executable, '-m', 'esptool', '--chip', 'esp32c3', '--port', path, '--baud', '460800',
                '--before', 'default-reset', '--after', 'hard-reset', 'write-flash', '-z']
        for name, offset in OFFSETS.items():
            args.extend([hex(offset), str(root / name)])
        # esptool validates ESP32-C3 before any write; offsets never include NVS.
        result = await asyncio.to_thread(subprocess.run, args, capture_output=True, timeout=150, check=False)
        if result.returncode:
            raise ValueError('Firmwareinstallation fehlgeschlagen.')
        session.state, session.message = 'CHECKING', 'Firmware installiert. Sensor startet; Identität wird geprüft…'
        for attempt in range(8):
            try:
                await self.read_identity(session)
                break
            except (OSError, ValueError, TimeoutError, serial.SerialException):
                if attempt == 7:
                    raise
                await asyncio.sleep(1)
        session.state, session.message = ('NETWORK', 'Firmware, Identität und Kalibrierung geprüft. WLAN einrichten.') if session.calibration_ready else ('CALIBRATION', 'Firmware und Hardware-Identität geprüft. Vor WLAN zuerst kalibrieren.')
        append_audit('usb.flash.completed', port_id=session.id, device_id=session.device_id, firmware=VERSION)


    async def calibrate(self, session, kind: str):
        session.state, session.message = 'CALIBRATING', ('Trockenreferenz wird gemessen…' if kind == 'air' else 'Nassreferenz wird gemessen…')
        before_key = session.public_key
        command = 'CAL AIR' if kind == 'air' else 'CAL WATER'
        expected = 'CAL AIR SAVED:' if kind == 'air' else 'CAL WATER SAVED:'
        def run():
            with USBSerial(resolve(session.id)) as connection:
                fresh, _ = connection.proof()
                if before_key and fresh.public_key != before_key:
                    raise DeviceBlocked('Sensoridentität hat sich während der Kalibrierung geändert.')
                connection.command(command, lambda line: line.startswith(expected), timeout=15)
        await asyncio.to_thread(run)
        await self.read_identity(session)
        if session.air_calibrated and session.wet_calibrated:
            if session.air_raw is None or session.wet_raw is None or session.air_raw <= session.wet_raw + 100:
                raise ValueError('Kalibrierwerte sind nicht plausibel; Kalibrierung wiederholen.')
            session.state, session.message = 'NETWORK', 'Kalibrierung vollständig und plausibel. Jetzt WLAN/TLS einrichten.'
            append_audit('usb.calibration.completed', device_id=session.device_id, air_raw=session.air_raw, wet_raw=session.wet_raw)
        else:
            session.state, session.message = 'CALIBRATION', 'Erster Kalibrierpunkt gespeichert. Zweiten Referenzpunkt durchführen.'

    async def provision(self, session, body):
        session.state, session.message = 'PROVISIONING', 'Individueller Zugang und Zertifikat werden lokal eingerichtet…'
        proof = await self.read_identity(session)
        append_audit('usb.network.started', device_id=proof.device_id)
        credentials = await asyncio.to_thread(request_broker, 'provision', device_id=proof.device_id, host=body.broker_host)
        def transfer():
            with USBSerial(resolve(session.id)) as connection:
                fresh, _ = connection.proof()
                if fresh.public_key != proof.public_key:
                    raise ValueError('Sensor ausgetauscht.')
                commands = [
                    ('NET CA ' + credentials['ca'], 'OK broker CA stored'),
                    ('NET MQTT ' + '|'.join([credentials['host'], str(credentials['port']), credentials['username'], credentials['password']]), 'OK MQTT configuration saved'),
                    ('NET WIFI ' + body.ssid + '|' + body.password.get_secret_value(), 'OK WiFi configuration saved'),
                ]
                for command, response in commands:
                    connection.command(command, lambda line, expected=response: line == expected, timeout=8)
        await asyncio.to_thread(transfer)
        session.state, session.message = 'CONNECTING', 'WLAN und TLS-MQTT werden verbunden. Aktuelle Netzwerk-Identität prüfen…'
        await self.wait_online(session)

    async def wait_online(self, session):
        from app.devices.runtime import runtime
        provider = runtime.get('growcentral_esp32')
        for attempt in range(12):
            session.message = f'WLAN-/MQTT-Verbindung prüfen: Versuch {attempt + 1}/12. Sensor angeschlossen lassen.'
            try:
                proof = await provider.prove_identity(session.device_id)
                if proof.public_key != session.public_key:
                    raise DeviceBlocked('Netzwerk-Identität passt nicht zum USB-Sensor.')
                if proof.body.get('hardware_uid') != session.hardware_uid:
                    raise DeviceBlocked('Netzwerk-Hardware-ID passt nicht zum USB-Sensor.')
                cal = proof.body.get('calibration') or {}
                if not cal.get('ready'):
                    raise DeviceBlocked('Sensor meldet keine abgeschlossene Kalibrierung.')
                if (TrustStore().get(session.device_id) or {}).get('status') == 'TRUSTED':
                    session.state, session.message = 'READY', 'Bekannter Sensor ist verbunden und bereits einem Raum zugewiesen.'
                    return proof
                session.state, session.message = 'ASSIGN', 'Sensor ist verbunden. Jetzt Name und Raum zuweisen.'
                return proof
            except TimeoutError:
                await asyncio.sleep(1)
        raise TimeoutError('Sensorverbindung nicht bestätigt.')


manager = USBManager()


class FlashRequest(BaseModel):
    board: str = Field(pattern=r'^seeed_xiao_esp32c3$')
    confirmed: bool = Field(strict=True)


class NetworkRequest(BaseModel):
    ssid: str = Field(min_length=1, max_length=32)
    password: SecretStr
    broker_host: str = Field(min_length=1, max_length=253)

    @field_validator('ssid', 'broker_host')
    @classmethod
    def safe_serial(cls, value):
        if any(ord(char) < 32 for char in value) or '|' in value:
            raise ValueError('Ungültige Zeichen.')
        return value

    @field_validator('broker_host')
    @classmethod
    def supported_broker_host(cls, value):
        if value.lower().endswith('.local'):
            raise ValueError('Für diesen Sensor die LAN-IP des Pi als Broker wählen; .local wird nicht unterstützt.')
        return value

    @field_validator('ssid')
    @classmethod
    def ssid_bytes(cls, value):
        if len(value.encode()) > 32:
            raise ValueError('SSID ist zu lang.')
        return value

    @field_validator('password')
    @classmethod
    def safe_password(cls, value):
        text = value.get_secret_value()
        if len(text.encode()) > 63 or (text and len(text.encode()) < 8) or any(ord(char) < 32 for char in text) or text != text.rstrip():
            raise ValueError('WLAN-Kennwort benötigt 8–63 Bytes; leer nur für offene WLANs.')
        return value


class Assignment(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    room_id: str = Field(min_length=1, max_length=80)
    confirmed: bool = Field(strict=True)

    @field_validator('name')
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError('Name fehlt.')
        return value.strip()


@router.get('')
async def usb_devices():
    found = await asyncio.to_thread(ports)
    try:
        await asyncio.to_thread(firmware_files)
        firmware_ready = True
    except (OSError, ValueError, KeyError):
        firmware_ready = False
    return {'devices': [{**port, **manager.sessions.setdefault(port['id'], Session(port['id'])).public()} for port in found],
            'sessions': [session.public() for session in manager.sessions.values()],
            'firmware_ready': firmware_ready, 'firmware_version': VERSION, 'supported_board': 'seeed_xiao_esp32c3'}


@router.get('/broker')
async def broker_options():
    try:
        result = await asyncio.to_thread(request_broker, 'info')
        return {'ready': True, 'hosts': result['hosts']}
    except (OSError, RuntimeError):
        return {'ready': False, 'hosts': [], 'message': 'Lokaler Broker-Einrichtungsdienst nicht verfügbar.'}


@router.post('/{port_id}/inspect')
async def inspect_device(port_id: str):
    session = manager.session(port_id)
    manager.start(session, lambda: manager.inspect(session))
    return session.public()


@router.post('/{port_id}/flash')
async def flash_device(port_id: str, body: FlashRequest):
    if not body.confirmed:
        raise HTTPException(422, 'Board und Firmwareinstallation zuerst bestätigen.')
    try:
        await asyncio.to_thread(firmware_files)
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(503, 'Geprüftes Firmware-Paket fehlt; aktuelles Test-Image installieren.') from exc
    session = manager.session(port_id)
    try:
        path = await asyncio.to_thread(resolve, port_id)
        await asyncio.to_thread(ensure_not_downgrade, path)
    except DeviceBlocked as exc:
        append_audit('usb.flash.downgrade_blocked', port_id=port_id, bundled_firmware=VERSION)
        raise HTTPException(409, str(exc)) from exc
    manager.start(session, lambda: manager.flash(session))
    return session.public()




@router.post('/{port_id}/calibrate/{kind}')
async def calibrate_device(port_id: str, kind: str):
    if kind not in {'air', 'wet'}:
        raise HTTPException(404, 'Unbekannter Kalibrierpunkt.')
    session = manager.session(port_id)
    if not session.public_key or session.state not in {'CALIBRATION', 'CALIBRATING'}:
        raise HTTPException(409, 'Zuerst Firmware und Hardware-Identität prüfen.')
    manager.start(session, lambda: manager.calibrate(session, kind))
    return session.public()

@router.post('/{port_id}/network')
async def network_device(port_id: str, body: NetworkRequest):
    session = manager.session(port_id)
    if not session.public_key or not session.calibration_ready or session.state not in {'NETWORK', 'ERROR', 'ASSIGN'}:
        raise HTTPException(409, 'Zuerst Firmware, Hardware-Identität und Kalibrierung vollständig prüfen.')
    manager.start(session, lambda: manager.provision(session, body))
    return session.public()


@router.post('/{port_id}/connection')
async def check_connection(port_id: str):
    session = manager.session(port_id)
    if not session.public_key:
        raise HTTPException(409, 'USB-Identität zuerst prüfen.')
    async def operation():
        session.state, session.message = 'CONNECTING', 'Vorhandene Sensorverbindung wird geprüft…'
        await manager.read_identity(session)
        await manager.wait_online(session)
    manager.start(session, operation)
    return session.public()


@router.post('/{port_id}/assign')
async def assign_device(port_id: str, body: Assignment):
    from app import rooms
    session = manager.session(port_id)
    if session.busy or session.state != 'ASSIGN':
        raise HTTPException(409, 'Sensor muss zuerst verbunden und geprüft sein.')
    if not body.confirmed:
        raise HTTPException(422, 'Name, Raum und physische Sensorzuordnung ausdrücklich bestätigen.')
    session.busy = True
    try:
        rooms.room_or_404(rooms.load_state(), body.room_id)
        proof = await manager.read_identity(session)
        network_proof = await manager.wait_online(session)
        if network_proof.public_key != proof.public_key or network_proof.body.get('hardware_uid') != session.hardware_uid:
            raise ValueError('Identität oder Hardware-ID passt nicht.')
        if not session.calibration_ready:
            raise ValueError('Kalibrierung nicht vollständig.')
        state = network_proof.body.get('state') or {}
        meta = state.get('meta') if isinstance(state, dict) else {}
        if not isinstance(meta, dict) or meta.get('sensor_ok') is not True or meta.get('quality') not in {'FAIR','GOOD','EXCELLENT'}:
            raise ValueError('Sensor-Selbsttest oder Signalqualität nicht ausreichend.')
        def assign():
            with rooms.edit_state() as current:
                rooms.room_or_404(current, body.room_id)
                current['assignments']['growcentral_esp32:' + proof.device_id] = body.room_id
        existing = TrustStore().get(proof.device_id)
        if existing and existing['status'] == 'TRUSTED':
            raise ValueError('Sensor bereits aufgenommen; bestehende Raumzuweisung in der Raumverwaltung ändern.')
        row = await asyncio.to_thread(TrustStore().accept, proof.device_id, name=body.name, room_id=body.room_id,
            fingerprint=proof.fingerprint[-16:], proved_key=proof.public_key, assign=assign)
        session.name = row['name']
        session.state, session.message = 'READY', 'Alle Prüfungen bestanden: Identität, Hardware-ID, Kalibrierung, TLS-Verbindung und Raumzuweisung. Sensor kann jetzt abgezogen und eingesetzt werden.'
        append_audit('usb.sensor.accepted', device_id=proof.device_id, room_id=body.room_id)
        return {'ok': True, 'device': row, 'session': session.public()}
    except (ValueError, DeviceBlocked) as exc:
        if isinstance(exc, DeviceBlocked):
            session.state, session.message = 'BLOCKED', 'Sperrstatus und Geräteidentität in der Sensorliste prüfen.'
        raise HTTPException(409, 'Aufnahme nicht möglich; Identität, Sperrstatus und Raum prüfen.') from exc
    except (TimeoutError, OSError) as exc:
        session.state, session.resume = 'ERROR', 'NETWORK'
        session.message = 'Sensor ist aktuell nicht erreichbar; WLAN-Verbindung erneut prüfen.'
        raise HTTPException(504, session.message) from exc
    finally:
        session.busy = False
