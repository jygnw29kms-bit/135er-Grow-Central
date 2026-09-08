#!/usr/bin/env python3
"""135er Dyson Service Center.

The normal monitor keeps all battery communication passive.  A technician can
explicitly start a narrowly-scoped UART probe which sends only read requests
for battery type and status.  The application never sends control/write TLVs,
flashes firmware or changes battery protection data.
"""

import binascii
import copy
import glob
import json
import os
import re
import select
import shutil
import subprocess
import termios
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, make_response, render_template_string, request


APP_VERSION = "0.3.0"
SUPPORTED_CAN_BITRATES = (10000, 20000, 50000, 100000, 125000, 250000, 500000, 800000, 1000000)
SUPPORTED_SERIAL_BAUDS = (9600, 19200, 38400, 57600, 115200, 230400)
CAN_IFACE = os.getenv("CAN_IFACE", "can0")
CAN_BITRATE = int(os.getenv("CAN_BITRATE", "500000"))
SERIAL_DEVICE = os.getenv("SERIAL_DEVICE", "auto")
SERIAL_BAUD = int(os.getenv("SERIAL_BAUD", "115200"))
DETECTION_TIMEOUT = max(2.0, float(os.getenv("DETECTION_TIMEOUT", "5")))
AUTO_SCAN_DWELL = max(1.0, float(os.getenv("AUTO_SCAN_DWELL", "2.5")))
WEB_PORT = int(os.getenv("WEB_PORT", "8080"))
START_MONITORS = os.getenv("DYSON_DISABLE_MONITORS", "0") != "1"

app = Flask(__name__)
state_lock = threading.RLock()
stop_event = threading.Event()
probe_lock = threading.Lock()
probe_active = threading.Event()
config_epoch = 0
auto_preferred_device = None
workers_started = False
started_monotonic = time.monotonic()

can_frames = deque(maxlen=500)
uart_frames = deque(maxlen=300)
events = deque(maxlen=500)

monitor_state = {
    "can": {
        "status": "starting",
        "iface": CAN_IFACE,
        "pid": None,
        "last_error": None,
        "last_frame_at": None,
        "last_frame_monotonic": None,
        "frames_total": 0,
        "restart_count": 0,
    },
    "uart": {
        "status": "starting",
        "configured_device": SERIAL_DEVICE,
        "active_device": None,
        "baud": SERIAL_BAUD,
        "last_error": None,
        "last_byte_at": None,
        "last_byte_monotonic": None,
        "last_valid_frame_at": None,
        "last_valid_frame_monotonic": None,
        "bytes_total": 0,
        "frames_total": 0,
        "valid_frames": 0,
        "response_frames": 0,
        "invalid_frames": 0,
        "last_response_frame_at": None,
        "last_response_frame_monotonic": None,
        "restart_count": 0,
    },
}

probe_state = {
    "status": "never_run",
    "started_at": None,
    "finished_at": None,
    "device": None,
    "attempts": 0,
    "last_error": None,
    "detail": "Noch keine aktive Leseabfrage ausgeführt.",
}


PCB_ADAPTERS = [
    {"model": "V6", "pcb": "61462", "interface": "PIC-ICSP", "status": "TESTED", "status_class": "ok",
     "signals": ["MCLR/VPP", "GND", "ICSPDAT", "ICSPCLK"], "adapter": "V6_PCB_61462_PIC-ICSP_ALIGNMENT_FIXTURE",
     "mechanical": "Elektrisch verifiziert; Pogo-Abstände am realen Board messen.",
     "notes": "PIC16LF1847. Programmer-VDD nicht blind in das Dyson-BMS einspeisen."},
    {"model": "V6", "pcb": "188002", "interface": "PIC-ICSP", "status": "TESTED", "status_class": "ok",
     "signals": ["MCLR/VPP", "GND", "ICSPDAT", "ICSPCLK"], "adapter": "V6_PCB_188002_PIC-ICSP_ALIGNMENT_FIXTURE",
     "mechanical": "Elektrisch verifiziert; Boardfoto vorhanden. Pogo-Abstände am realen Board messen.",
     "notes": "PIC16LF1847. Reprogrammierung in Community dokumentiert."},
    {"model": "V7", "pcb": "279857", "interface": "PIC-ICSP", "status": "TESTED", "status_class": "ok",
     "signals": ["MCLR/VPP", "GND", "ICSPDAT", "ICSPCLK"], "adapter": "V7_PCB_279857_PIC-ICSP_ALIGNMENT_FIXTURE",
     "mechanical": "Elektrisch verifiziert; Millimeter-Pitch vor Druck messen.",
     "notes": "PIC16LF1847. PCB-spezifischer Adapter vorgesehen."},
    {"model": "V7", "pcb": "228499", "interface": "PIC-ICSP", "status": "REPORTED WORKING", "status_class": "warn",
     "signals": ["MCLR/VPP", "GND", "ICSPDAT", "ICSPCLK"], "adapter": "V7_PCB_228499_PIC-ICSP_ALIGNMENT_FIXTURE",
     "mechanical": "Elektrischer Pfad berichtet; keine autoritativen mm-Padkoordinaten gefunden.",
     "notes": "Vor Freigabe Boardrevision und Padabstände am Original prüfen."},
    {"model": "V8", "pcb": "180207", "interface": "PIC-ICSP", "status": "WORKING REPORTS", "status_class": "warn",
     "signals": ["MCLR/VPP", "GND", "ICSPDAT", "ICSPCLK"], "adapter": "V8_PCB_180207_PIC-ICSP_ALIGNMENT_FIXTURE",
     "mechanical": "Erfolgreiche Berichte; exakte mm-Padkoordinaten nicht öffentlich normiert.",
     "notes": "V8 D/E und weitere Revisionen nicht pauschal gleichsetzen."},
    {"model": "V10", "pcb": "board-specific", "interface": "SWD / UART", "status": "INTERFACE VERIFIED", "status_class": "warn",
     "signals": ["GND", "SWDIO", "SWCLK", "UART RX/TX"], "adapter": "V10_SWD_ALIGNMENT_FIXTURE_UNVERIFIED",
     "mechanical": "SWD/OpenOCD und Debug-UART bekannt; Testpad-Geometrie pro Originalboard verifizieren.",
     "notes": "UART nur verwenden, wenn es zum konkreten Board/Firmwarestand passt."},
    {"model": "V11", "pcb": "board-specific", "interface": "SWD / UART 115200", "status": "INTERFACE VERIFIED", "status_class": "warn",
     "signals": ["GND", "SWDIO", "SWCLK", "UART RX/TX"], "adapter": "V11_SWD_ALIGNMENT_FIXTURE_UNVERIFIED",
     "mechanical": "SAMD20E15/SWD bekannt; Screw- und Click-In-Boards mechanisch getrennt prüfen.",
     "notes": "Die Dyson-Datenkommunikation ist UART/TLV, nicht CAN. Keine universelle Pogo-Geometrie verwenden."},
    {"model": "V12", "pcb": "unverified", "interface": "SWD / UART, revisionsabhängig", "status": "EXPERIMENTAL", "status_class": "exp",
     "signals": ["nur nach Board-Verifikation"], "adapter": "kein freigegebener Adapter",
     "mechanical": "Keine universell bestätigte Testpad-Geometrie.", "notes": "Nicht automatisch freischalten."},
    {"model": "V15", "pcb": "unverified", "interface": "SWD / UART, revisionsabhängig", "status": "EXPERIMENTAL", "status_class": "exp",
     "signals": ["nur nach Board-Verifikation"], "adapter": "kein freigegebener Adapter",
     "mechanical": "Keine universell bestätigte Testpad-Geometrie.", "notes": "Nicht automatisch freischalten."},
]


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def seconds_since(value):
    if value is None:
        return None
    return round(max(0.0, time.monotonic() - value), 2)


def trim(value, limit=1200):
    text = str(value or "").strip()
    return text[-limit:]


def add_event(source, level, code, message, detail=None):
    item = {"ts": utc_now(), "source": source, "level": level, "code": code, "message": message}
    if detail:
        item["detail"] = trim(detail)
    with state_lock:
        events.append(item)


def update_monitor(channel, **values):
    with state_lock:
        previous_status = monitor_state[channel].get("status")
        previous_error = monitor_state[channel].get("last_error")
        monitor_state[channel].update(values)
        new_status = monitor_state[channel].get("status")
        new_error = monitor_state[channel].get("last_error")
    if new_status != previous_status or (new_error and new_error != previous_error):
        level = "error" if new_status in ("error", "missing", "bus_off") else "info"
        add_event(channel, level, "monitor_state", f"Monitorstatus: {new_status}", new_error)


def run_command(args, timeout=5):
    try:
        result = subprocess.run(args, text=True, capture_output=True, timeout=timeout, check=False)
        return {"ok": result.returncode == 0, "returncode": result.returncode,
                "stdout": trim(result.stdout, 4000), "stderr": trim(result.stderr, 4000)}
    except FileNotFoundError:
        return {"ok": False, "returncode": 127, "stdout": "", "stderr": f"{args[0]} nicht installiert"}
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "returncode": 124, "stdout": trim(exc.stdout), "stderr": "Zeitüberschreitung"}
    except Exception as exc:
        return {"ok": False, "returncode": 1, "stdout": "", "stderr": trim(exc)}


def config_path():
    explicit = os.getenv("DYSON_CONFIG_PATH")
    candidates = [explicit] if explicit else []
    candidates.extend(["/etc/default/dyson-v11-bms", "/etc/default/dyson-bms"])
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return candidates[0] if candidates else "/etc/default/dyson-v11-bms"


def persist_config(updates):
    path = Path(config_path())
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    values.update({key: str(value) for key, value in updates.items()})
    allowed = ("CAN_IFACE", "CAN_BITRATE", "SERIAL_DEVICE", "SERIAL_BAUD",
               "DETECTION_TIMEOUT", "AUTO_SCAN_DWELL", "WEB_PORT")
    body = "".join(f"{key}={values[key]}\n" for key in allowed if key in values)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(body, encoding="utf-8")
    os.chmod(temporary, 0o644)
    os.replace(temporary, path)
    return str(path)


def serial_path_allowed(path):
    if path == "auto":
        return True
    return bool(re.fullmatch(r"/dev/(tty(USB|ACM|AMA|S)\d+|serial\d+|serial/by-id/[A-Za-z0-9_.:+@-]+)", path))


def serial_candidates():
    patterns = ["/dev/serial/by-id/*", "/dev/ttyACM*", "/dev/ttyUSB*", "/dev/serial0", "/dev/ttyAMA0"]
    result = []
    seen_paths = set()
    seen_real_paths = set()
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            if path in seen_paths:
                continue
            seen_paths.add(path)
            real_path = os.path.realpath(path)
            if real_path in seen_real_paths:
                continue
            seen_real_paths.add(real_path)
            result.append({
                "path": path,
                "real_path": real_path,
                "name": os.path.basename(path),
                "exists": os.path.exists(path),
                "readable": os.access(path, os.R_OK),
                "writable": os.access(path, os.W_OK),
                "by_id": "/by-id/" in path,
            })
    return result


def resolve_serial_device(configured):
    if configured != "auto":
        return configured if os.path.exists(configured) else None
    candidates = serial_candidates()
    if auto_preferred_device:
        preferred_real = os.path.realpath(auto_preferred_device)
        for candidate in candidates:
            if candidate["real_path"] == preferred_real:
                return candidate["path"]
    return candidates[0]["path"] if candidates else None


def configure_serial(fd, baud, flush_input=True):
    speed = getattr(termios, f"B{baud}", None)
    if speed is None:
        raise ValueError(f"Baudrate {baud} wird von diesem System nicht unterstützt")
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0
    attrs[1] = 0
    attrs[2] = termios.CLOCAL | termios.CREAD | termios.CS8
    attrs[3] = 0
    attrs[4] = speed
    attrs[5] = speed
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 1
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    if flush_input:
        termios.tcflush(fd, termios.TCIFLUSH)


def dyson_crc8(data):
    crc = 0xFF
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = ((crc >> 1) ^ 0xE0) if crc & 1 else (crc >> 1)
    return crc ^ 0xFF


def dyson_crc32(data):
    padded = bytes(data) + b"\x00" * ((-len(data)) % 4)
    return binascii.crc32(padded) & 0xFFFFFFFF


def stuff_dyson(data):
    result = bytearray([0x12])
    for value in data:
        if value == 0x12:
            result.extend((0xDB, 0xDE))
        elif value == 0xDB:
            result.extend((0xDB, 0xDD))
        else:
            result.append(value)
    result.append(0x12)
    return bytes(result)


def build_dyson_read_probe(counter=1):
    """Build a read-only request for battery type (0x8102) and status (0x8106)."""
    payload = bytes((counter & 0xFF, 0x02, 0x10, 0x02, 0x81, 0x02, 0x10, 0x06, 0x81))
    size = 4 + len(payload) + 4
    frame = bytearray(size + 3)
    frame[0:2] = size.to_bytes(2, "little")
    frame[2] = dyson_crc8(frame[:2])
    frame[3:7] = bytes((0x01, 0xC0, 0x01, 0x02))
    frame[7:7 + len(payload)] = payload
    crc_offset = size - 1
    frame[crc_offset:crc_offset + 4] = dyson_crc32(frame[3:crc_offset]).to_bytes(4, "little")
    return stuff_dyson(frame)


def unstuff_dyson(data):
    result = bytearray()
    index = 0
    while index < len(data):
        value = data[index]
        if value != 0xDB:
            result.append(value)
            index += 1
            continue
        if index + 1 >= len(data):
            raise ValueError("unvollständige Escape-Sequenz")
        escaped = data[index + 1]
        if escaped == 0xDE:
            result.append(0x12)
        elif escaped == 0xDD:
            result.append(0xDB)
        else:
            raise ValueError(f"unbekannte Escape-Sequenz DB {escaped:02X}")
        index += 2
    return bytes(result)


def decode_dyson_frame(stuffed):
    errors = []
    try:
        frame = unstuff_dyson(stuffed)
    except ValueError as exc:
        return {"ts": utc_now(), "valid": False, "errors": ["bad_escape"], "detail": str(exc),
                "raw": bytes(stuffed).hex(" ").upper(), "length": len(stuffed)}
    if len(frame) < 11:
        errors.append("too_short")
    size = frame[0] | (frame[1] << 8) if len(frame) >= 2 else None
    length_ok = size is not None and len(frame) == size + 3
    if not length_ok:
        errors.append("bad_size")
    crc8_ok = len(frame) >= 3 and dyson_crc8(frame[:2]) == frame[2]
    if not crc8_ok:
        errors.append("bad_crc8")
    marker_ok = len(frame) >= 5 and frame[4] == 0xC0
    if not marker_ok:
        errors.append("bad_marker")
    crc32_ok = False
    if size is not None and size >= 8 and len(frame) >= size + 3:
        stored = int.from_bytes(frame[size - 1:size + 3], "little")
        computed = dyson_crc32(frame[3:3 + size - 4])
        crc32_ok = stored == computed
    if not crc32_ok:
        errors.append("bad_crc32")
    valid = not errors
    source = frame[5] if len(frame) > 5 else None
    frame_class = frame[6] if len(frame) > 6 else None
    if source == 0xFF:
        kind = "Discovery"
        role = "discovery"
    elif frame_class == 0x01 and source in (0x02, 0x03):
        kind = "Antwort"
        role = "battery_response"
    elif frame_class == 0x02:
        kind = "Datenanfrage"
        role = "request"
    elif frame_class == 0x03:
        kind = "Steueranfrage"
        role = "request"
    else:
        kind = "Dyson-Frame" if valid else "Unbekannt"
        role = "other"
    return {
        "ts": utc_now(), "valid": valid, "errors": errors, "length": len(frame), "size": size,
        "crc8_ok": crc8_ok, "crc32_ok": crc32_ok, "marker_ok": marker_ok,
        "direction": frame[3] if len(frame) > 3 else None, "source": source, "class": frame_class,
        "kind": kind, "role": role, "raw": frame[:192].hex(" ").upper(),
    }


class DysonFrameParser:
    def __init__(self):
        self.collecting = False
        self.buffer = bytearray()
        self.noise_bytes = 0

    def feed(self, data):
        decoded = []
        for value in data:
            if value == 0x12:
                if self.collecting and self.buffer:
                    decoded.append(decode_dyson_frame(bytes(self.buffer)))
                    self.buffer.clear()
                self.collecting = True
            elif self.collecting:
                self.buffer.append(value)
                if len(self.buffer) > 512:
                    decoded.append({"ts": utc_now(), "valid": False, "errors": ["frame_overflow"],
                                    "detail": "Mehr als 512 Bytes ohne Abschluss-Trennzeichen", "length": len(self.buffer),
                                    "raw": self.buffer[:192].hex(" ").upper()})
                    self.buffer.clear()
                    self.collecting = False
            else:
                self.noise_bytes += 1
        return decoded


def record_uart_chunk(parser, chunk, device):
    global auto_preferred_device
    now_mono = time.monotonic()
    now_text = utc_now()
    decoded = parser.feed(chunk)
    with state_lock:
        uart_state = monitor_state["uart"]
        uart_state["bytes_total"] += len(chunk)
        uart_state["last_byte_at"] = now_text
        uart_state["last_byte_monotonic"] = now_mono
        for item in decoded:
            uart_frames.append(item)
            uart_state["frames_total"] += 1
            if item.get("valid"):
                uart_state["valid_frames"] += 1
                uart_state["last_valid_frame_at"] = item["ts"]
                uart_state["last_valid_frame_monotonic"] = now_mono
                if item.get("role") == "battery_response":
                    uart_state["response_frames"] += 1
                    uart_state["last_response_frame_at"] = item["ts"]
                    uart_state["last_response_frame_monotonic"] = now_mono
                    uart_state["status"] = "battery_response"
                    auto_preferred_device = device
                elif uart_state["status"] != "battery_response":
                    uart_state["status"] = "protocol_activity"
            else:
                uart_state["invalid_frames"] += 1
                if uart_state["status"] not in ("battery_response", "protocol_activity"):
                    uart_state["status"] = "traffic_invalid"
    if decoded:
        good = sum(1 for item in decoded if item.get("valid"))
        responses = sum(1 for item in decoded if item.get("valid") and item.get("role") == "battery_response")
        bad = len(decoded) - good
        if responses:
            add_event("uart", "ok", "battery_response", f"{responses} gültige Akku-Antworten empfangen")
        elif good:
            add_event("uart", "info", "dyson_activity", f"{good} gültige Dyson-Request/Discovery-Frames empfangen")
        if bad:
            add_event("uart", "warn", "invalid_frame", f"{bad} beschädigte/unpassende Frames empfangen")
    return decoded


def serial_monitor():
    parser = DysonFrameParser()
    auto_index = 0
    while not stop_event.is_set():
        if probe_active.is_set():
            update_monitor("uart", status="probing", active_device=None, last_error=None)
            stop_event.wait(0.1)
            continue
        with state_lock:
            epoch = config_epoch
            configured = SERIAL_DEVICE
            baud = SERIAL_BAUD
        candidates = serial_candidates() if configured == "auto" else []
        if configured == "auto" and candidates:
            if auto_preferred_device:
                preferred_real = os.path.realpath(auto_preferred_device)
                candidates.sort(key=lambda item: item["real_path"] != preferred_real)
            device = candidates[auto_index % len(candidates)]["path"]
        else:
            device = resolve_serial_device(configured)
        if not device:
            update_monitor("uart", status="missing", configured_device=configured, active_device=None,
                           baud=baud, last_error="Kein serielles UART-Gerät gefunden")
            stop_event.wait(1.0)
            continue
        fd = None
        try:
            # Open read-only: the monitor must never transmit a byte to the BMS.
            fd = os.open(device, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
            configure_serial(fd, baud)
            parser = DysonFrameParser()
            opened_at = time.monotonic()
            with state_lock:
                opened_valid = monitor_state["uart"]["valid_frames"]
            update_monitor("uart", status="listening", configured_device=configured, active_device=device,
                           baud=baud, last_error=None)
            add_event("uart", "info", "serial_open", f"UART geöffnet: {device} mit {baud} Baud")
            while not stop_event.is_set():
                with state_lock:
                    valid_frames = monitor_state["uart"]["valid_frames"]
                    if epoch != config_epoch or probe_active.is_set():
                        break
                ready, _, _ = select.select([fd], [], [], 0.75)
                if not ready:
                    if (configured == "auto" and len(candidates) > 1 and
                            valid_frames == opened_valid and time.monotonic() - opened_at >= AUTO_SCAN_DWELL):
                        auto_index = (auto_index + 1) % len(candidates)
                        add_event("uart", "info", "auto_scan_next",
                                  f"Keine Daten auf {device}; nächstes UART-Gerät wird geprüft")
                        break
                    continue
                chunk = os.read(fd, 4096)
                if not chunk:
                    raise OSError("UART-Gerät liefert keine Daten mehr")
                record_uart_chunk(parser, chunk, device)
        except (OSError, ValueError, termios.error) as exc:
            with state_lock:
                monitor_state["uart"]["restart_count"] += 1
            update_monitor("uart", status="error", active_device=device, last_error=trim(exc))
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        stop_event.wait(0.05 if probe_active.is_set() else 0.5)


def run_active_uart_probe(timeout=2.5, attempts=2):
    """Pause passive monitoring, scan UART candidates and accept only a BMS response."""
    global config_epoch, auto_preferred_device
    if not probe_lock.acquire(blocking=False):
        with state_lock:
            return {**probe_state, "ok": False, "error": "Eine Leseabfrage läuft bereits."}
    paused_monitor = False
    try:
        candidates = serial_candidates() if SERIAL_DEVICE == "auto" else []
        if SERIAL_DEVICE != "auto" and os.path.exists(SERIAL_DEVICE):
            candidates = [{"path": SERIAL_DEVICE, "real_path": os.path.realpath(SERIAL_DEVICE)}]
        if auto_preferred_device and SERIAL_DEVICE == "auto":
            preferred_real = os.path.realpath(auto_preferred_device)
            candidates.sort(key=lambda item: item["real_path"] != preferred_real)
        with state_lock:
            probe_state.update(status="running", started_at=utc_now(), finished_at=None,
                               device=SERIAL_DEVICE, attempts=0, last_error=None,
                               detail="Read-only Dyson-UART-Abfrage läuft.", devices=[])
        if not candidates:
            raise OSError("Kein serielles UART-Gerät gefunden")

        probe_active.set()
        paused_monitor = True
        with state_lock:
            config_epoch += 1
        # The passive reader uses a 750 ms select timeout. Give it time to close
        # so it cannot consume the response intended for this bounded probe.
        time.sleep(0.85)

        device_results = []
        total_attempts = 0
        for candidate in candidates:
            device = candidate["path"]
            fd = None
            parser = DysonFrameParser()
            device_result = {"device": device, "status": "no_response", "bytes": 0, "attempts": 0}
            try:
                if not os.access(device, os.R_OK | os.W_OK):
                    raise PermissionError(f"Lese-/Schreibzugriff auf {device} fehlt")
                fd = os.open(device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
                configure_serial(fd, SERIAL_BAUD)
                update_monitor("uart", status="probing", configured_device=SERIAL_DEVICE,
                               active_device=device, baud=SERIAL_BAUD, last_error=None)
                for attempt in range(1, attempts + 1):
                    total_attempts += 1
                    device_result["attempts"] = attempt
                    request_frame = build_dyson_read_probe(attempt)
                    written = 0
                    while written < len(request_frame):
                        _, writable, _ = select.select([], [fd], [], 0.5)
                        if not writable:
                            raise TimeoutError("UART-Senden hat das Zeitlimit überschritten")
                        count = os.write(fd, request_frame[written:])
                        if count <= 0:
                            raise OSError("UART-Senden lieferte 0 Bytes")
                        written += count
                    termios.tcdrain(fd)
                    with state_lock:
                        probe_state["attempts"] = total_attempts
                    add_event("uart", "info", "read_probe_sent",
                              f"Sichere Leseabfrage {attempt}/{attempts} über {device} gesendet")
                    deadline = time.monotonic() + timeout / attempts
                    while time.monotonic() < deadline:
                        remaining = max(0.0, deadline - time.monotonic())
                        readable, _, _ = select.select([fd], [], [], min(0.2, remaining))
                        if not readable:
                            continue
                        chunk = os.read(fd, 4096)
                        if not chunk:
                            raise OSError("UART-Gerät wurde während der Leseabfrage getrennt")
                        device_result["bytes"] += len(chunk)
                        decoded = record_uart_chunk(parser, chunk, device)
                        if any(item.get("valid") and item.get("role") == "battery_response"
                               for item in decoded):
                            device_result["status"] = "success"
                            device_results.append(device_result)
                            auto_preferred_device = device
                            with state_lock:
                                probe_state.update(status="success", finished_at=utc_now(), device=device,
                                                   last_error=None, devices=device_results,
                                                   detail=f"Gültige Akku-Antwort auf {device} mit Rollen-, Größen-, Marker-, CRC8- und CRC32-Prüfung empfangen.")
                                result = copy.deepcopy(probe_state)
                            add_event("uart", "ok", "read_probe_response",
                                      f"Dyson-Akku hat auf {device} gültig geantwortet")
                            return {**result, "ok": True}
            except (OSError, ValueError, TimeoutError, termios.error) as exc:
                device_result.update(status="error", error=trim(exc))
                add_event("uart", "warn", "read_probe_device_error",
                          f"Leseabfrage auf {device} fehlgeschlagen", exc)
            finally:
                if fd is not None:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
            device_results.append(device_result)

        with state_lock:
            probe_state.update(status="no_response", finished_at=utc_now(),
                               device=None, devices=device_results,
                               detail=f"{len(device_results)} UART-Gerät(e) geprüft, aber keine gültige Akku-Antwort empfangen.",
                               last_error="Keine gültige Antwort innerhalb des Zeitlimits")
            result = copy.deepcopy(probe_state)
        add_event("uart", "warn", "read_probe_timeout", "Keine gültige Antwort auf sichere Leseabfrage")
        return {**result, "ok": False, "error": result["last_error"]}
    except (OSError, ValueError, TimeoutError, termios.error) as exc:
        with state_lock:
            probe_state.update(status="error", finished_at=utc_now(), last_error=trim(exc),
                               detail="Aktive Leseabfrage konnte nicht vollständig ausgeführt werden.")
            result = copy.deepcopy(probe_state)
        add_event("uart", "error", "read_probe_failed", "Sichere Leseabfrage fehlgeschlagen", exc)
        return {**result, "ok": False, "error": str(exc)}
    finally:
        if paused_monitor:
            probe_active.clear()
            with state_lock:
                config_epoch += 1
        probe_lock.release()


def parse_candump_line(line):
    match = re.match(r"^\(([^)]+)\)\s+(\S+)\s+([0-9A-Fa-f]{3,8})(##?)([0-9A-Fa-f]*)", line.strip())
    if not match:
        return None
    separator = match.group(4)
    data = match.group(5)
    flags = None
    if separator == "##" and data:
        flags, data = data[0], data[1:]
    return {"ts": match.group(1), "iface": match.group(2), "id": match.group(3).upper(),
            "data": data.upper(), "fd_flags": flags, "received_at": utc_now()}


def can_interfaces():
    result = []
    command = run_command(["ip", "-details", "-statistics", "-json", "link", "show", "type", "can"])
    if command["ok"]:
        try:
            for item in json.loads(command["stdout"] or "[]"):
                info = item.get("linkinfo", {}).get("info_data", {})
                stats = item.get("stats64") or item.get("stats") or {}
                result.append({
                    "name": item.get("ifname"), "operstate": item.get("operstate", "UNKNOWN"),
                    "flags": item.get("flags", []), "bitrate": info.get("bittiming", {}).get("bitrate"),
                    "state": info.get("state"), "berr_counter": info.get("berr_counter"),
                    "statistics": stats,
                })
        except (ValueError, TypeError):
            pass
    if not result:
        for path in sorted(Path("/sys/class/net").glob("*")):
            try:
                if (path / "type").read_text().strip() == "280":
                    result.append({"name": path.name, "operstate": (path / "operstate").read_text().strip().upper(),
                                   "flags": [], "bitrate": None, "state": None, "berr_counter": None, "statistics": {}})
            except OSError:
                continue
    return result


def can_monitor():
    while not stop_event.is_set():
        with state_lock:
            epoch = config_epoch
            iface = CAN_IFACE
        available = {item["name"] for item in can_interfaces()}
        if iface not in available:
            update_monitor("can", status="missing", iface=iface, pid=None,
                           last_error=f"CAN-Interface {iface} ist nicht vorhanden")
            stop_event.wait(1.5)
            continue
        if not shutil.which("candump"):
            update_monitor("can", status="error", iface=iface, pid=None, last_error="candump ist nicht installiert")
            stop_event.wait(3.0)
            continue
        process = None
        try:
            process = subprocess.Popen(["candump", "-L", iface], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, bufsize=1)
            update_monitor("can", status="listening", iface=iface, pid=process.pid, last_error=None)
            add_event("can", "info", "candump_start", f"CAN-Monitor auf {iface} gestartet")
            while not stop_event.is_set() and process.poll() is None:
                with state_lock:
                    if epoch != config_epoch:
                        break
                streams = [stream for stream in (process.stdout, process.stderr) if stream is not None]
                ready, _, _ = select.select(streams, [], [], 0.75)
                for stream in ready:
                    line = stream.readline()
                    if not line:
                        continue
                    if stream is process.stderr:
                        update_monitor("can", status="error", last_error=trim(line))
                        continue
                    item = parse_candump_line(line)
                    if item:
                        now_mono = time.monotonic()
                        with state_lock:
                            can_frames.append(item)
                            can_state = monitor_state["can"]
                            can_state["frames_total"] += 1
                            can_state["last_frame_at"] = item["received_at"]
                            can_state["last_frame_monotonic"] = now_mono
                            can_state["status"] = "traffic"
            if process.poll() not in (None, 0):
                error = process.stderr.read() if process.stderr else ""
                update_monitor("can", status="error", last_error=trim(error) or f"candump endete mit {process.returncode}")
        except OSError as exc:
            update_monitor("can", status="error", pid=None, last_error=trim(exc))
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
            with state_lock:
                monitor_state["can"]["pid"] = None
                monitor_state["can"]["restart_count"] += 1
        stop_event.wait(1.0)


def configure_can(iface, bitrate):
    available = {item["name"] for item in can_interfaces()}
    if iface not in available:
        return False, {"stage": "interface", "error": f"CAN-Interface {iface} nicht gefunden"}
    steps = []
    for stage, args in (
        ("down", ["ip", "link", "set", "dev", iface, "down"]),
        ("bitrate", ["ip", "link", "set", "dev", iface, "type", "can", "bitrate", str(bitrate), "restart-ms", "100"]),
        ("up", ["ip", "link", "set", "dev", iface, "up"]),
    ):
        result = run_command(args)
        steps.append({"stage": stage, **result})
        if not result["ok"]:
            return False, {"stage": stage, "error": result["stderr"] or result["stdout"], "steps": steps}
    return True, {"stage": "ready", "steps": steps}


def usb_debug_probes():
    probes = []
    known = {("1366", None): "SEGGER J-Link", ("03eb", "2141"): "Atmel-ICE",
             ("0d28", "0204"): "CMSIS-DAP", ("c251", "f001"): "CMSIS-DAP"}
    for device in sorted(Path("/sys/bus/usb/devices").glob("*")):
        try:
            vendor = (device / "idVendor").read_text().strip().lower()
            product_id = (device / "idProduct").read_text().strip().lower()
        except OSError:
            continue
        product = ""
        manufacturer = ""
        try:
            product = (device / "product").read_text(errors="replace").strip()
        except OSError:
            pass
        try:
            manufacturer = (device / "manufacturer").read_text(errors="replace").strip()
        except OSError:
            pass
        label = None
        for (known_vendor, known_product), known_label in known.items():
            if vendor == known_vendor and (known_product is None or product_id == known_product):
                label = known_label
                break
        combined = f"{manufacturer} {product}".lower()
        if label or any(word in combined for word in ("j-link", "cmsis-dap", "atmel-ice", "debug probe")):
            probes.append({"name": label or product or manufacturer or "Debug-Probe",
                           "vendor_id": vendor, "product_id": product_id,
                           "manufacturer": manufacturer, "product": product})
    return probes


def serial_getty_status(device):
    if not device or not shutil.which("systemctl"):
        return None
    unit = f"serial-getty@{os.path.basename(os.path.realpath(device))}.service"
    result = run_command(["systemctl", "is-active", unit], timeout=3)
    return {"unit": unit, "active": result["stdout"].strip() == "active", "detail": result["stderr"]}


def battery_snapshot():
    with state_lock:
        uart = copy.deepcopy(monitor_state["uart"])
        can = copy.deepcopy(monitor_state["can"])
    uart_valid_age = seconds_since(uart.pop("last_valid_frame_monotonic", None))
    uart_response_age = seconds_since(uart.pop("last_response_frame_monotonic", None))
    uart_byte_age = seconds_since(uart.pop("last_byte_monotonic", None))
    can_age = seconds_since(can.pop("last_frame_monotonic", None))
    uart["last_valid_frame_age_s"] = uart_valid_age
    uart["last_response_frame_age_s"] = uart_response_age
    uart["last_byte_age_s"] = uart_byte_age
    can["last_frame_age_s"] = can_age
    if uart_response_age is not None and uart_response_age <= DETECTION_TIMEOUT:
        battery = {"state": "detected", "label": "Dyson-Protokoll erkannt", "source": "UART",
                   "detail": f"Letzte gültige Akku-Antwort vor {uart_response_age:.1f} s"}
    elif uart_response_age is not None:
        battery = {"state": "lost", "label": "Verbindung abgebrochen", "source": "UART",
                   "detail": f"Letzte gültige Akku-Antwort vor {uart_response_age:.1f} s"}
    elif uart_valid_age is not None and uart_valid_age <= DETECTION_TIMEOUT:
        battery = {"state": "activity", "label": "Dyson-Anfrage, keine Akku-Antwort", "source": "UART",
                   "detail": "Ein gültiger Request/Discovery-Frame ist sichtbar, bestätigt allein aber keinen angeschlossenen Akku."}
    elif uart_byte_age is not None and uart_byte_age <= DETECTION_TIMEOUT:
        battery = {"state": "invalid", "label": "Signal da, Protokoll ungültig", "source": "UART",
                   "detail": "Bytes kommen an, aber kein vollständiger Dyson-Frame besteht Größen-/CRC-Prüfung."}
    elif can_age is not None and can_age <= DETECTION_TIMEOUT:
        battery = {"state": "activity", "label": "CAN-Verkehr vorhanden", "source": "CAN",
                   "detail": "CAN-Verkehr allein bestätigt keinen V11-Akku; das dokumentierte V11-Datenprotokoll ist UART."}
    else:
        battery = {"state": "waiting", "label": "Kein Akku-Protokoll", "source": None,
                   "detail": "Warte auf einen gültigen Dyson-UART-Frame."}
    return battery, uart, can


def diagnostic_check(check_id, layer, label, status, summary, remedy="", detail=None):
    item = {"id": check_id, "layer": layer, "label": label, "status": status,
            "summary": summary, "remedy": remedy}
    if detail is not None:
        item["detail"] = detail
    return item


def build_diagnostics():
    battery, uart, can = battery_snapshot()
    serials = serial_candidates()
    active_serial = uart.get("active_device") or resolve_serial_device(SERIAL_DEVICE)
    getty = serial_getty_status(active_serial)
    interfaces = can_interfaces()
    selected_can = next((item for item in interfaces if item.get("name") == CAN_IFACE), None)
    probes = usb_debug_probes()
    checks = []

    checks.append(diagnostic_check("protocol", "Protokoll", "V11-Protokollweg", "ok",
        "UART 115200 / 8N1 mit Dyson-TLV-Frameprüfung aktiv.",
        "Für V11 UART RX/TX/GND oder für Programmierdiagnose SWD verwenden; CAN ist nur Zusatz-/Legacy-Monitor."))
    if serials:
        checks.append(diagnostic_check("serial_device", "Adapter", "UART-Gerät", "ok",
            f"{len(serials)} serielles Gerät gefunden; aktiv: {active_serial or 'noch keines'}.", detail=serials))
    else:
        checks.append(diagnostic_check("serial_device", "Adapter", "UART-Gerät", "error",
            "Kein UART-Gerät unter /dev gefunden.",
            "USB-UART-Adapter/Interfacebox verbinden oder Raspberry-Pi-UART aktivieren; danach Diagnose erneut starten."))
    if active_serial and not os.access(active_serial, os.R_OK):
        checks.append(diagnostic_check("serial_permission", "Betriebssystem", "UART-Berechtigung", "error",
            f"Keine Leseberechtigung für {active_serial}.",
            "Dienstberechtigung bzw. dialout-Gruppe und Geräte-Regel prüfen."))
    elif active_serial:
        checks.append(diagnostic_check("serial_permission", "Betriebssystem", "UART-Berechtigung", "ok",
            f"Zugriff auf {active_serial} ist möglich."))
        if os.access(active_serial, os.W_OK):
            checks.append(diagnostic_check("serial_probe_permission", "Betriebssystem",
                "UART-Leseabfrage", "ok", f"TX-Zugriff für sichere Leseabfrage auf {active_serial} ist möglich."))
        else:
            checks.append(diagnostic_check("serial_probe_permission", "Betriebssystem",
                "UART-Leseabfrage", "warn", f"Kein TX-Zugriff auf {active_serial}; passives Monitoring funktioniert weiterhin.",
                "Geräteberechtigung/udev-Regel bzw. dialout-Gruppe für die manuelle Leseabfrage prüfen."))
    if SERIAL_DEVICE == "auto" and len(serials) > 1:
        checks.append(diagnostic_check("serial_auto_scan", "Adapter", "Mehrere UART-Geräte", "info",
            f"Auto-Scan prüft {len(serials)} physische UART-Geräte nacheinander.",
            "Nach erfolgreicher Akku-Antwort wird der richtige Port bis zum Trennen bevorzugt."))
    if getty and getty["active"]:
        checks.append(diagnostic_check("serial_getty", "Betriebssystem", "Serielle Konsole", "error",
            f"{getty['unit']} belegt dieselbe Schnittstelle.",
            "Serielle Linux-Konsole für diesen Port deaktivieren; zwei Leser verursachen sporadisch fehlende Frames."))
    elif getty:
        checks.append(diagnostic_check("serial_getty", "Betriebssystem", "Serielle Konsole", "ok",
            "Keine aktive serial-getty-Kollision erkannt."))
    if uart["status"] in ("listening", "battery_response", "protocol_activity", "traffic_invalid"):
        checks.append(diagnostic_check("serial_open", "Treiber", "UART-Monitor", "ok",
            f"Monitor läuft auf {uart.get('active_device')} mit {uart.get('baud')} Baud."))
    else:
        checks.append(diagnostic_check("serial_open", "Treiber", "UART-Monitor", "error",
            uart.get("last_error") or f"UART-Monitorstatus: {uart['status']}",
            "Adapterpfad, Berechtigungen und serielle Konsole prüfen."))
    if uart["last_byte_age_s"] is None:
        checks.append(diagnostic_check("uart_signal", "Elektrik", "UART-Rohsignal", "warn",
            "Seit Dienststart keine UART-Bytes empfangen.",
            "GND, RX/TX-Zuordnung, 3,3-V-Pegel, Pogo-Kontakt und aktiven/wachen Akku prüfen."))
    elif uart["last_byte_age_s"] <= DETECTION_TIMEOUT:
        checks.append(diagnostic_check("uart_signal", "Elektrik", "UART-Rohsignal", "ok",
            f"UART-Aktivität vor {uart['last_byte_age_s']:.1f} s; insgesamt {uart['bytes_total']} Bytes."))
    else:
        checks.append(diagnostic_check("uart_signal", "Elektrik", "UART-Rohsignal", "warn",
            f"UART-Signal ist seit {uart['last_byte_age_s']:.1f} s weg.",
            "Federkontakte, gemeinsame Masse, Akku-Wakeup/Trigger und Kabelzug prüfen."))
    if uart["last_response_frame_age_s"] is not None and uart["last_response_frame_age_s"] <= DETECTION_TIMEOUT:
        checks.append(diagnostic_check("dyson_frame", "Protokoll", "Dyson-Frame", "ok",
            f"Gültige Akku-Antwort mit Größen-, Marker-, CRC8- und CRC32-Prüfung; "
            f"{uart['response_frames']} Antworten gesamt."))
    elif uart["last_valid_frame_age_s"] is not None and uart["last_valid_frame_age_s"] <= DETECTION_TIMEOUT:
        checks.append(diagnostic_check("dyson_frame", "Protokoll", "Dyson-Frame", "warn",
            "Gültige Dyson-Anfrage sichtbar, aber keine gültige Akku-Antwort.",
            "Akku-TX → Adapter-RX, gemeinsame Masse und Pogo-Kontakt prüfen oder sichere Leseabfrage starten."))
    elif uart["invalid_frames"]:
        checks.append(diagnostic_check("dyson_frame", "Protokoll", "Dyson-Frame", "error",
            f"{uart['invalid_frames']} ungültige und {uart['valid_frames']} gültige Frames.",
            "Bei CRC-/Größenfehlern zuerst Pegel, GND, RX/TX, Baudrate und Kontaktqualität prüfen."))
    else:
        checks.append(diagnostic_check("dyson_frame", "Protokoll", "Dyson-Frame", "warn",
            "Noch kein vollständiger Dyson-Frame empfangen.",
            "V11 spricht laut Firmwarebasis UART mit 115200 Baud; CAN-Verkehr ist kein Ersatz für diesen Nachweis."))

    with state_lock:
        probe = copy.deepcopy(probe_state)
    probe_status = {"success": "ok", "no_response": "error", "error": "error",
                    "running": "info", "never_run": "info"}.get(probe["status"], "info")
    checks.append(diagnostic_check("active_probe", "Protokoll", "Aktive Leseabfrage", probe_status,
        probe["detail"],
        "Bei Timeout TX/RX-Zuordnung, 3,3-V-Pegel, gemeinsame Masse und Akku-Wakeup prüfen."
        if probe_status == "error" else "", detail=probe))

    if probes:
        checks.append(diagnostic_check("swd_probe", "SWD", "Programmer", "ok",
            ", ".join(probe["name"] for probe in probes) + " erkannt.", detail=probes))
    else:
        checks.append(diagnostic_check("swd_probe", "SWD", "Programmer", "info",
            "Kein J-Link/Atmel-ICE/CMSIS-DAP gefunden.",
            "Nur für SWD-Service nötig; für passive UART-Protokolldiagnose nicht erforderlich."))
    openocd = run_command(["openocd", "--version"], timeout=3)
    checks.append(diagnostic_check("openocd", "SWD", "OpenOCD", "ok" if openocd["ok"] else "warn",
        (openocd["stdout"].splitlines()[0] if openocd["stdout"] else openocd["stderr"]),
        "OpenOCD installieren, wenn die SWD-Zielverbindung geprüft werden soll." if not openocd["ok"] else ""))

    if selected_can:
        can_state = str(selected_can.get("state") or "").upper()
        can_status = "error" if "BUS-OFF" in can_state else "ok"
        checks.append(diagnostic_check("can_link", "CAN (optional)", "CAN-Link", can_status,
            f"{CAN_IFACE}: {selected_can.get('operstate')}; Buszustand {selected_can.get('state') or 'unbekannt'}; "
            f"Bitrate {selected_can.get('bitrate') or CAN_BITRATE}.",
            "Terminierung, CAN-H/CAN-L, Masse und Bitrate prüfen; nach BUS-OFF Interface neu starten." if can_status == "error" else "",
            detail=selected_can))
        statistics = selected_can.get("statistics") or {}
        rx_stats = statistics.get("rx") or {}
        tx_stats = statistics.get("tx") or {}
        error_total = sum(int(value or 0) for value in (
            rx_stats.get("errors"), rx_stats.get("dropped"), rx_stats.get("over_errors"),
            tx_stats.get("errors"), tx_stats.get("dropped"), tx_stats.get("carrier_errors")))
        checks.append(diagnostic_check("can_errors", "CAN (optional)", "CAN-Fehlerzähler",
            "warn" if error_total else "ok",
            f"Fehler-/Drop-Zähler: {error_total}.",
            "Bei steigenden Zählern Verkabelung, 120-Ohm-Terminierung, Masse, Bitrate und Störeinflüsse prüfen."
            if error_total else "", detail={"rx": rx_stats, "tx": tx_stats}))
        if can.get("status") == "error":
            checks.append(diagnostic_check("candump", "CAN (optional)", "CAN-Monitor", "error",
                can.get("last_error") or "candump ist beendet.",
                "candump/can-utils, Interfacezustand und Dienstberechtigungen prüfen."))
        else:
            checks.append(diagnostic_check("candump", "CAN (optional)", "CAN-Monitor", "ok",
                f"Monitorstatus: {can.get('status')}; Frames gesamt: {can.get('frames_total')}."))
    else:
        checks.append(diagnostic_check("can_link", "CAN (optional)", "CAN-Link", "info",
            f"Optionales Interface {CAN_IFACE} ist nicht vorhanden.",
            "Für echte V11-UART-Erkennung nicht erforderlich."))

    error_count = sum(1 for item in checks if item["status"] == "error")
    warn_count = sum(1 for item in checks if item["status"] == "warn")
    if battery["state"] == "detected":
        overall = "ok"
    elif error_count:
        overall = "error"
    else:
        overall = "warn"
    with state_lock:
        recent_events = list(events)[-120:]
    return {
        "generated_at": utc_now(), "app_version": APP_VERSION, "overall": overall,
        "battery": battery, "summary": {"errors": error_count, "warnings": warn_count, "checks": len(checks)},
        "config": {"serial_device": SERIAL_DEVICE, "serial_baud": SERIAL_BAUD,
                   "can_iface": CAN_IFACE, "can_bitrate": CAN_BITRATE,
                   "detection_timeout_s": DETECTION_TIMEOUT, "auto_scan_dwell_s": AUTO_SCAN_DWELL,
                   "config_path": config_path()},
        "runtime": {"uptime_s": round(time.monotonic() - started_monotonic, 1),
                    "python": os.sys.version.split()[0], "monitors_started": workers_started},
        "uart": uart, "probe": probe, "can": can, "serial_devices": serials, "can_interfaces": interfaces,
        "swd_probes": probes, "checks": checks, "events": recent_events,
    }


HTML = r'''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>135er Dyson Service Center</title>
<style>
:root{--bg:#07121d;--panel:#0d1b28;--line:#20384b;--blue:#168cff;--green:#29e477;--yellow:#f7b928;--red:#ff4d5e;--muted:#8fa6b8;--text:#f5f8fb}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:linear-gradient(135deg,#06101a,#0a1723);color:var(--text)}
header{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:18px 24px;border-bottom:1px solid var(--line);background:#081520}
.brand{font-size:28px;font-weight:800}.brand span{color:var(--blue)}.sub,.muted{color:var(--muted);font-size:13px}
.status{padding:8px 12px;border-radius:8px;font-size:13px;font-weight:800;background:#253342;color:#cdd9e2}.status.ok{background:#0f3b2a;color:#8affb7}.status.warn{background:#443919;color:#ffd765}.status.error{background:#4a2027;color:#ffc3ca}
.layout{display:grid;grid-template-columns:220px 1fr;min-height:calc(100vh - 74px)}nav{border-right:1px solid var(--line);padding:18px 12px;background:#081722}
nav button{display:block;width:100%;text-align:left;border:0;background:transparent;color:#c8d5df;padding:12px 14px;border-radius:8px;margin:4px 0;cursor:pointer;font-size:14px}nav button.active,nav button:hover{background:#0e6ee8;color:white}
main{padding:18px;overflow:auto}.page{display:none}.page.active{display:block}.grid{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:12px}.grid.two{grid-template-columns:1fr 1fr}
.card{background:linear-gradient(180deg,#0d1b28,#0a1823);border:1px solid var(--line);border-radius:12px;padding:15px}.card h3{margin:0 0 10px;font-size:16px}.metric{font-size:26px;font-weight:800}.metric.small{font-size:18px}
.models{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}.model{padding:10px 14px;border:1px solid var(--line);border-radius:10px;background:#0d1b28;font-weight:700}.model.ok{border-color:#1d7b50}.model.warn{border-color:#876b24}.model.exp{border-color:#7b4d24}
.badge{display:inline-block;padding:4px 8px;border-radius:999px;font-size:11px;font-weight:800}.badge.ok{background:#123b28;color:#74f0a4}.badge.warn,.badge.info{background:#443919;color:#ffd765}.badge.error{background:#4a2027;color:#ffc3ca}.badge.exp{background:#4b2e1b;color:#ffb26d}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:10px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}th{color:#cfe3f2;background:#0a1d2b;position:sticky;top:0}.signal{display:inline-block;background:#122c3f;border:1px solid #29465b;border-radius:6px;padding:3px 6px;margin:2px;font-size:11px}
.notice{border-left:4px solid var(--yellow);padding:12px 14px;background:#2b2717;border-radius:8px;margin:12px 0;color:#f7e5a4}.notice.red{border-color:var(--red);background:#2b171b;color:#ffc3ca}.notice.green{border-color:var(--green);background:#102b20;color:#a9f6c4}
input,select,button.action,a.action{padding:9px;border-radius:7px;border:1px solid #29465b;background:#0b1b27;color:white;text-decoration:none}.action{cursor:pointer;display:inline-block;margin:3px}.action.primary{background:#0e6ee8;border-color:#168cff}pre{white-space:pre-wrap;word-break:break-word;background:#061019;padding:10px;border-radius:8px;max-height:360px;overflow:auto}
.check{display:grid;grid-template-columns:125px 120px 1fr;gap:10px;padding:11px 0;border-bottom:1px solid var(--line)}.check:last-child{border:0}.remedy{color:#ffd765;margin-top:4px}.controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.controls label{font-size:12px;color:var(--muted)}
@media(max-width:900px){.layout{grid-template-columns:1fr}nav{display:flex;overflow:auto;border-right:0;border-bottom:1px solid var(--line)}nav button{min-width:130px}.grid,.grid.two{grid-template-columns:1fr 1fr}.check{grid-template-columns:90px 1fr}.check>div:last-child{grid-column:1/-1}}
@media(max-width:560px){header{padding:14px}.brand{font-size:21px}.grid,.grid.two{grid-template-columns:1fr}main{padding:10px}}
</style></head><body>
<header><div><div class="brand">135er <span>Dyson Service Center</span></div><div class="sub">Diagnose · UART/TLV · SWD · optional CAN · v{{version}}</div></div><div id="topStatus" class="status">● Prüfe System …</div></header>
<div class="layout"><nav>
<button class="active" onclick="showPage('dashboard',this)">Dashboard</button><button onclick="showPage('diagnose',this)">Diagnose</button><button onclick="showPage('uart',this)">UART Monitor</button><button onclick="showPage('pcb',this)">PCB & Adapter</button><button onclick="showPage('can',this)">CAN (optional)</button><button onclick="showPage('system',this)">System</button>
</nav><main>
<section id="dashboard" class="page active"><div class="models">{% for m in models %}<div class="model {{m.cls}}">{{m.name}}<br><span class="sub">{{m.state}}</span></div>{% endfor %}</div>
<div class="grid"><div class="card"><h3>Akku-Erkennung</h3><div id="batteryMetric" class="metric small">Prüfung läuft</div><div id="batteryDetail" class="muted">–</div></div><div class="card"><h3>Gültige Akku-Antworten</h3><div id="validMetric" class="metric">0</div><div class="muted">Antwortrolle + Größe + Marker + CRC8 + CRC32</div></div><div class="card"><h3>UART-Gerät</h3><div id="uartMetric" class="metric small">–</div><div id="uartDetail" class="muted">115200 / 8N1</div></div><div class="card"><h3>Diagnosefehler</h3><div id="errorMetric" class="metric">0</div><div id="warningMetric" class="muted">0 Warnungen</div></div></div>
<div class="notice green"><b>Korrigierter V11-Erkennungsweg:</b> Ein Akku gilt erst als erkannt, wenn eine echte Dyson-Antwort die Rollen-, Größen-, Marker-, CRC8- und CRC32-Prüfung besteht. Request-Echos und CAN-Aktivität können keinen Akku mehr vortäuschen.</div>
<div class="notice red"><b>Sicherheit:</b> Der Monitor ist passiv. Die manuell gestartete Leseabfrage sendet ausschließlich Battery-Type-/Status-Reads und keine Steuer- oder Schreibbefehle. Keine Packspannung an Pi/USB-Adapter anschließen; nur verifizierte 3,3-V-UART-Pads verwenden.</div></section>

<section id="diagnose" class="page"><div class="card"><div class="controls"><button class="action primary" onclick="runProbe()">Akku sicher abfragen</button><button class="action" onclick="runDiagnosis()">Diagnose aktualisieren</button><a class="action" href="/api/diagnostics/export">Bericht herunterladen</a></div><p class="muted">Prüft Betriebssystem → Adapter → Schnittstelle → Rohsignal → Dyson-Protokoll. „Akku sicher abfragen“ sendet zwei reine Leseanfragen und wartet auf eine CRC-geprüfte Akku-Antwort.</p><div id="probeResult" class="notice" style="display:none"></div><div id="diagChecks"></div></div><div class="card" style="margin-top:12px"><h3>Ereignisprotokoll</h3><pre id="eventLog">Noch keine Ereignisse.</pre></div></section>

<section id="uart" class="page"><div class="grid two"><div class="card"><h3>UART Setup</h3><div class="controls"><label>Gerät<br><select id="serialDevice"><option value="auto">Automatisch</option></select></label><label>Baudrate<br><select id="serialBaud">{% for baud in serial_bauds %}<option value="{{baud}}" {% if baud == serial_baud %}selected{% endif %}>{{baud}}</option>{% endfor %}</select></label><button class="action primary" onclick="setSerial()">Übernehmen</button></div><pre id="serialState"></pre></div><div class="card"><h3>Dyson-Frames</h3><pre id="uartFrames">Noch keine Frames.</pre></div></div><div class="notice">Bei Rohbytes ohne gültigen Frame: zuerst gemeinsame Masse, RX/TX-Zuordnung, 3,3-V-Pegel, 115200 Baud und Pogo-Kontakt prüfen. Bei zeitweisen Abbrüchen ist ein aktiver <code>serial-getty</code> ein typischer Softwarekonflikt.</div></section>

<section id="pcb" class="page"><div class="card"><h3>PCB- & Adapterdatenbank</h3><div class="muted">Suche nach Modell, PCB oder Schnittstelle.</div><p><input id="pcbSearch" placeholder="z. B. V11, 61462, UART" oninput="filterPCB()"></p><div style="overflow:auto;max-height:65vh"><table id="pcbTable"><thead><tr><th>Modell</th><th>PCB</th><th>Status</th><th>Schnittstelle</th><th>Signale</th><th>Adapter</th><th>Mechanik / Hinweis</th></tr></thead><tbody>{% for x in pcb %}<tr><td><b>{{x.model}}</b></td><td>{{x.pcb}}</td><td><span class="badge {{x.status_class}}">{{x.status}}</span></td><td>{{x.interface}}</td><td>{% for s in x.signals %}<span class="signal">{{s}}</span>{% endfor %}</td><td><code>{{x.adapter}}</code></td><td>{{x.mechanical}}<br><span class="muted">{{x.notes}}</span></td></tr>{% endfor %}</tbody></table></div></div></section>

<section id="can" class="page"><div class="grid two"><div class="card"><h3>Optionales CAN Setup</h3><div class="controls"><label>Interface<br><input id="canIface" value="{{can_iface}}"></label><label>Bitrate<br><select id="canBitrate">{% for bitrate in can_bitrates %}<option value="{{bitrate}}" {% if bitrate == can_bitrate %}selected{% endif %}>{{bitrate}}</option>{% endfor %}</select></label><button class="action" onclick="setCan()">Übernehmen</button></div><pre id="canState"></pre></div><div class="card"><h3>Read-only CAN Monitor</h3><pre id="canFrames">Noch keine Frames.</pre></div></div><div class="notice"><b>Hinweis:</b> Das dokumentierte Dyson-V11-Datenprotokoll läuft über UART. Diese CAN-Seite bleibt für externe Konverter, Versuchsaufbauten und andere Adapter erhalten, bestätigt aber allein keinen V11-Akku.</div></section>

<section id="system" class="page"><div class="card"><h3>Diagnose-API</h3><p><code>GET /api/diagnostics</code> – vollständige Prüfkette</p><p><code>POST /api/diagnostics/run</code> – neue Diagnoseaufnahme</p><p><code>POST /api/serial/probe</code> – sichere Battery-Type-/Status-Leseabfrage</p><p><code>GET /api/diagnostics/export</code> – JSON-Bericht zum Herunterladen</p><p><code>GET /api/serial/frames</code> – geprüfte Dyson-UART-Frames</p><p><code>POST /api/serial</code> – UART-Gerät/Baudrate setzen</p><p><code>GET /api/frames</code> – optionale CAN-Frames</p><p><code>POST /api/can</code> – CAN-Link setzen</p><p><code>GET /api/pcb-adapters</code> – PCB-/Adaptermatrix</p></div></section>
</main></div>
<script>
const byId=id=>document.getElementById(id);const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function showPage(id,btn){document.querySelectorAll('.page').forEach(x=>x.classList.remove('active'));document.getElementById(id).classList.add('active');document.querySelectorAll('nav button').forEach(x=>x.classList.remove('active'));btn.classList.add('active')}
function filterPCB(){const q=document.getElementById('pcbSearch').value.toLowerCase();document.querySelectorAll('#pcbTable tbody tr').forEach(r=>r.style.display=r.innerText.toLowerCase().includes(q)?'':'none')}
async function api(url,options){const r=await fetch(url,options);const d=await r.json();if(!r.ok)throw new Error(d.error||d.message||r.statusText);return d}
function renderDiagnosis(d){const b=d.battery,top=byId('topStatus');top.className='status '+(b.state==='detected'?'ok':(b.state==='waiting'||b.state==='activity'?'warn':'error'));top.textContent='● '+b.label;byId('batteryMetric').textContent=b.label;byId('batteryDetail').textContent=b.detail;byId('validMetric').textContent=d.uart.response_frames;byId('uartMetric').textContent=d.uart.active_device||d.config.serial_device;byId('uartDetail').textContent=d.uart.status+' · '+d.uart.baud+' Baud';byId('errorMetric').textContent=d.summary.errors;byId('warningMetric').textContent=d.summary.warnings+' Warnungen';
byId('diagChecks').innerHTML=d.checks.map(c=>`<div class="check"><div><span class="badge ${esc(c.status)}">${esc(c.status.toUpperCase())}</span></div><div><b>${esc(c.layer)}</b><br><span class="muted">${esc(c.label)}</span></div><div>${esc(c.summary)}${c.remedy?`<div class="remedy">→ ${esc(c.remedy)}</div>`:''}</div></div>`).join('');
byId('eventLog').textContent=(d.events||[]).slice().reverse().map(e=>`${e.ts} [${e.level.toUpperCase()}] ${e.source}/${e.code}: ${e.message}${e.detail?' · '+e.detail:''}`).join('\n')||'Noch keine Ereignisse.';byId('serialState').textContent=JSON.stringify(d.uart,null,2);byId('canState').textContent=JSON.stringify({monitor:d.can,interfaces:d.can_interfaces},null,2);
const select=document.getElementById('serialDevice'),wanted=d.config.serial_device,current=select.value;select.innerHTML='<option value="auto">Automatisch</option>'+d.serial_devices.map(x=>`<option value="${esc(x.path)}">${esc(x.path)}</option>`).join('');select.value=[...select.options].some(x=>x.value===wanted)?wanted:(current||'auto')}
async function refresh(){try{const [d,u,c]=await Promise.all([api('/api/diagnostics'),api('/api/serial/frames'),api('/api/frames')]);renderDiagnosis(d);byId('uartFrames').textContent=u.slice(-60).map(x=>`${x.ts} ${x.valid?'OK':'FEHLER'} ${x.kind||''} size=${x.size??'?'} ${x.errors?.join(',')||''}\n${x.raw}`).join('\n')||'Noch keine Frames.';byId('canFrames').textContent=c.slice(-100).map(x=>`${x.ts} ${x.iface} ${x.id}#${x.data}`).join('\n')||'Noch keine Frames.'}catch(e){const top=byId('topStatus');top.className='status error';top.textContent='● Diagnose nicht erreichbar: '+e.message}}
async function runDiagnosis(){try{renderDiagnosis(await api('/api/diagnostics/run',{method:'POST'}))}catch(e){alert(e.message)}}
async function runProbe(){if(!confirm('Nur fortfahren, wenn TX, RX und GND an verifizierten 3,3-V-UART-Pads angeschlossen sind. Sichere Leseabfrage starten?'))return;const box=byId('probeResult');box.style.display='block';box.className='notice';box.textContent='Leseabfrage läuft …';try{const r=await api('/api/serial/probe',{method:'POST'});box.className='notice green';box.textContent=r.detail;await refresh()}catch(e){box.className='notice red';box.textContent='Leseabfrage fehlgeschlagen: '+e.message;await refresh()}}
async function setSerial(){try{await api('/api/serial',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device:byId('serialDevice').value,baud:Number(byId('serialBaud').value)})});refresh()}catch(e){alert(e.message)}}
async function setCan(){try{await api('/api/can',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({iface:byId('canIface').value,bitrate:Number(byId('canBitrate').value)})});refresh()}catch(e){alert(e.message)}}
setInterval(refresh,2000);refresh();
</script></body></html>'''


def model_cards():
    model_state = {}
    for item in PCB_ADAPTERS:
        current = model_state.setdefault(item["model"], {"ok": 0, "warn": 0, "exp": 0})
        current[item["status_class"]] += 1
    result = []
    for name in ("V6", "V7", "V8", "V10", "V11", "V12", "V15"):
        status = model_state.get(name, {"ok": 0, "warn": 0, "exp": 1})
        if status["ok"]:
            css, state = "ok", "integriert"
        elif status["warn"]:
            css, state = "warn", "teilverifiziert"
        else:
            css, state = "exp", "experimentell"
        result.append({"name": name, "cls": css, "state": state})
    return result


@app.get("/")
def index():
    return render_template_string(HTML, version=APP_VERSION, pcb=PCB_ADAPTERS, models=model_cards(),
                                  serial_bauds=SUPPORTED_SERIAL_BAUDS, serial_baud=SERIAL_BAUD,
                                  can_bitrates=SUPPORTED_CAN_BITRATES, can_bitrate=CAN_BITRATE, can_iface=CAN_IFACE)


@app.get("/api/status")
def api_status():
    battery, uart, can = battery_snapshot()
    interfaces = can_interfaces()
    selected = next((item for item in interfaces if item.get("name") == CAN_IFACE), None)
    legacy = run_command(["ip", "-details", "link", "show", CAN_IFACE])
    return jsonify(version=APP_VERSION, battery=battery, uart=uart, can=can,
                   iface=CAN_IFACE, bitrate=CAN_BITRATE, link_ok=selected is not None,
                   details=legacy["stdout"] or legacy["stderr"])


@app.get("/api/diagnostics")
def diagnostics():
    return jsonify(build_diagnostics())


@app.post("/api/diagnostics/run")
def run_diagnostics():
    add_event("system", "info", "diagnostics_run", "Manuelle Diagnoseaufnahme gestartet")
    return jsonify(build_diagnostics())


@app.get("/api/diagnostics/export")
def export_diagnostics():
    report = build_diagnostics()
    with state_lock:
        report["uart_frames"] = list(uart_frames)[-100:]
        report["can_frames"] = list(can_frames)[-100:]
    response = make_response(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    filename = datetime.now(timezone.utc).strftime("dyson-diagnose-%Y%m%d-%H%M%SZ.json")
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@app.get("/api/events")
def get_events():
    with state_lock:
        return jsonify(list(events))


@app.get("/api/serial/frames")
def get_uart_frames():
    with state_lock:
        return jsonify(list(uart_frames)[-100:])


@app.post("/api/serial/probe")
def active_serial_probe():
    result = run_active_uart_probe()
    return jsonify(result), (200 if result.get("ok") else 503)


@app.post("/api/serial")
def set_serial():
    global SERIAL_DEVICE, SERIAL_BAUD, config_epoch
    data = request.get_json(silent=True) or {}
    device = str(data.get("device", "auto")).strip()
    try:
        baud = int(data.get("baud", 115200))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Ungültige UART-Baudrate"), 400
    if not serial_path_allowed(device) or baud not in SUPPORTED_SERIAL_BAUDS:
        return jsonify(ok=False, error="Ungültige UART-Einstellung"), 400
    try:
        path = persist_config({"SERIAL_DEVICE": device, "SERIAL_BAUD": baud})
    except OSError as exc:
        add_event("uart", "error", "config_write", "UART-Einstellung konnte nicht gespeichert werden", exc)
        return jsonify(ok=False, error=f"Konfiguration konnte nicht gespeichert werden: {exc}"), 500
    with state_lock:
        SERIAL_DEVICE, SERIAL_BAUD = device, baud
        config_epoch += 1
        monitor_state["uart"].update(configured_device=device, baud=baud, status="restarting")
    add_event("uart", "info", "config_changed", f"UART gesetzt: {device}, {baud} Baud")
    return jsonify(ok=True, device=device, baud=baud, config_path=path)


@app.get("/api/frames")
def get_can_frames():
    with state_lock:
        return jsonify(list(can_frames)[-100:])


@app.post("/api/can")
def set_can():
    global CAN_IFACE, CAN_BITRATE, config_epoch
    data = request.get_json(silent=True) or {}
    iface = str(data.get("iface", "can0")).strip()
    try:
        bitrate = int(data.get("bitrate", 500000))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Ungültige CAN-Bitrate"), 400
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,15}", iface) or bitrate not in SUPPORTED_CAN_BITRATES:
        return jsonify(ok=False, error="Ungültige CAN-Einstellung"), 400
    ok, detail = configure_can(iface, bitrate)
    if not ok:
        add_event("can", "error", "configure_failed", "CAN-Konfiguration fehlgeschlagen", detail.get("error"))
        return jsonify(ok=False, error=detail.get("error"), detail=detail), 500
    try:
        path = persist_config({"CAN_IFACE": iface, "CAN_BITRATE": bitrate})
    except OSError as exc:
        return jsonify(ok=False, error=f"CAN aktiv, aber Konfiguration nicht gespeichert: {exc}"), 500
    with state_lock:
        CAN_IFACE, CAN_BITRATE = iface, bitrate
        config_epoch += 1
        monitor_state["can"].update(iface=iface, status="restarting")
    add_event("can", "info", "config_changed", f"CAN gesetzt: {iface}, {bitrate} bit/s")
    return jsonify(ok=True, iface=iface, bitrate=bitrate, config_path=path, detail=detail)


@app.get("/api/pcb-adapters")
def pcb_adapters():
    return jsonify(PCB_ADAPTERS)


@app.get("/api/pcb-adapters/<pcb>")
def pcb_adapter(pcb):
    hits = [item for item in PCB_ADAPTERS if str(item["pcb"]).lower() == pcb.lower()]
    if not hits:
        return jsonify(error="PCB-Profil nicht gefunden"), 404
    return jsonify(hits)


def start_background_workers():
    global workers_started
    with state_lock:
        if workers_started or not START_MONITORS:
            return
        workers_started = True
    add_event("system", "info", "service_start", f"Dyson Service Center {APP_VERSION} gestartet")
    threading.Thread(target=serial_monitor, name="dyson-uart-monitor", daemon=True).start()
    threading.Thread(target=can_monitor, name="dyson-can-monitor", daemon=True).start()


if __name__ == "__main__":
    start_background_workers()
    app.run(host="0.0.0.0", port=WEB_PORT, threaded=True)
