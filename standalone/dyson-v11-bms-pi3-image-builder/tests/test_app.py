import importlib.util
import os
import sys
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch


os.environ["DYSON_DISABLE_MONITORS"] = "1"

try:
    import flask  # noqa: F401
except ImportError:
    flask_stub = types.ModuleType("flask")

    class DummyApp:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            return lambda function: function

        def post(self, *args, **kwargs):
            return lambda function: function

    flask_stub.Flask = DummyApp
    flask_stub.jsonify = lambda *args, **kwargs: args[0] if args else kwargs
    flask_stub.make_response = lambda value: value
    flask_stub.render_template_string = lambda *args, **kwargs: ""
    flask_stub.request = types.SimpleNamespace(get_json=lambda **kwargs: {})
    sys.modules["flask"] = flask_stub


APP_PATH = (Path(__file__).parents[1] / "stage-dyson" / "00-install-packages" / "files" / "app.py")
SPEC = importlib.util.spec_from_file_location("dyson_service_app", APP_PATH)
dyson = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dyson)


KNOWN_DISCOVERY_FRAME = bytes.fromhex(
    "12 1A 00 31 00 C0 FF 03 00 00 20 00 00 00 00 00 00 00 00 00 00 00 00 10 00 FF 06 DA EE 2D 12"
)

KNOWN_STUFFED_RESPONSE = bytes.fromhex(
    "12 30 00 2B 01 C0 03 01 01 08 10 13 01 10 02 81 02 00 22 00 01 10 01 02 04 00 "
    "20 DB DE 0A 00 01 10 15 81 02 00 D8 72 01 10 14 81 02 00 76 48 01 00 F8 85 6C E5 12"
)


class DysonProtocolTests(unittest.TestCase):
    def test_known_capture_passes_all_protocol_checks(self):
        frames = dyson.DysonFrameParser().feed(KNOWN_DISCOVERY_FRAME)
        self.assertEqual(len(frames), 1)
        self.assertTrue(frames[0]["valid"])
        self.assertTrue(frames[0]["crc8_ok"])
        self.assertTrue(frames[0]["crc32_ok"])
        self.assertEqual(frames[0]["kind"], "Discovery")
        self.assertEqual(frames[0]["role"], "discovery")

    def test_fragmented_reads_preserve_frame(self):
        parser = dyson.DysonFrameParser()
        self.assertEqual(parser.feed(KNOWN_DISCOVERY_FRAME[:9]), [])
        frames = parser.feed(KNOWN_DISCOVERY_FRAME[9:])
        self.assertEqual(len(frames), 1)
        self.assertTrue(frames[0]["valid"])

    def test_corrupt_frame_is_not_a_battery_detection(self):
        corrupt = bytearray(KNOWN_DISCOVERY_FRAME)
        corrupt[-2] ^= 0x01
        frame = dyson.DysonFrameParser().feed(corrupt)[0]
        self.assertFalse(frame["valid"])
        self.assertIn("bad_crc32", frame["errors"])

    def test_stuffing_round_trip(self):
        self.assertEqual(dyson.unstuff_dyson(bytes.fromhex("AA DB DE BB DB DD")), bytes.fromhex("AA 12 BB DB"))

    def test_real_stuffed_capture_is_valid(self):
        frame = dyson.DysonFrameParser().feed(KNOWN_STUFFED_RESPONSE)[0]
        self.assertTrue(frame["valid"])
        self.assertEqual(frame["kind"], "Antwort")
        self.assertEqual(frame["role"], "battery_response")
        self.assertIn("12", frame["raw"])

    def test_active_probe_contains_reads_only(self):
        frames = dyson.DysonFrameParser().feed(dyson.build_dyson_read_probe(7))
        self.assertEqual(len(frames), 1)
        self.assertTrue(frames[0]["valid"])
        self.assertEqual(frames[0]["role"], "request")
        self.assertEqual(frames[0]["class"], 0x02)
        raw = bytes.fromhex(frames[0]["raw"])
        self.assertIn(bytes.fromhex("02 10 02 81"), raw)
        self.assertIn(bytes.fromhex("02 10 06 81"), raw)
        self.assertNotIn(bytes.fromhex("16 82"), raw)

    def test_noise_and_unterminated_frame_are_bounded(self):
        parser = dyson.DysonFrameParser()
        self.assertEqual(parser.feed(b"noise"), [])
        self.assertEqual(parser.noise_bytes, 5)
        overflow = parser.feed(b"\x12" + b"A" * 513)[0]
        self.assertEqual(overflow["errors"], ["frame_overflow"])
        self.assertEqual(len(overflow["raw"].split()), 192)


class MonitorTests(unittest.TestCase):
    def test_classic_and_fd_candump_lines(self):
        classic = dyson.parse_candump_line("(1.250000) can0 123#AABB")
        self.assertEqual(classic["id"], "123")
        self.assertEqual(classic["data"], "AABB")
        fd = dyson.parse_candump_line("(2.500000) can1 18DAF110##1010203")
        self.assertEqual(fd["fd_flags"], "1")
        self.assertEqual(fd["data"], "010203")
        self.assertIsNone(dyson.parse_candump_line("not a candump line"))

    def test_serial_path_is_restricted_to_tty_devices(self):
        self.assertTrue(dyson.serial_path_allowed("auto"))
        self.assertTrue(dyson.serial_path_allowed("/dev/ttyUSB0"))
        self.assertTrue(dyson.serial_path_allowed("/dev/serial/by-id/usb-FTDI_123-if00-port0"))
        self.assertFalse(dyson.serial_path_allowed("/etc/passwd"))

    def test_detection_requires_recent_valid_uart_frame(self):
        with dyson.state_lock:
            previous = dict(dyson.monitor_state["uart"])
            dyson.monitor_state["uart"]["last_response_frame_monotonic"] = time.monotonic()
        try:
            battery, _, _ = dyson.battery_snapshot()
            self.assertEqual(battery["state"], "detected")
            self.assertEqual(battery["source"], "UART")
        finally:
            with dyson.state_lock:
                dyson.monitor_state["uart"].clear()
                dyson.monitor_state["uart"].update(previous)

    def test_raw_bytes_can_never_claim_valid_detection(self):
        with dyson.state_lock:
            previous = dict(dyson.monitor_state["uart"])
            dyson.monitor_state["uart"].update(
                last_valid_frame_monotonic=None,
                last_response_frame_monotonic=None,
                last_byte_monotonic=time.monotonic(),
            )
        try:
            battery, _, _ = dyson.battery_snapshot()
            self.assertEqual(battery["state"], "invalid")
            self.assertNotEqual(battery["label"], "Dyson-Protokoll erkannt")
        finally:
            with dyson.state_lock:
                dyson.monitor_state["uart"].clear()
                dyson.monitor_state["uart"].update(previous)

    def test_stale_uart_connection_is_reported_lost(self):
        with dyson.state_lock:
            previous = dict(dyson.monitor_state["uart"])
            dyson.monitor_state["uart"]["last_response_frame_monotonic"] = (
                time.monotonic() - dyson.DETECTION_TIMEOUT - 1
            )
        try:
            battery, _, _ = dyson.battery_snapshot()
            self.assertEqual(battery["state"], "lost")
        finally:
            with dyson.state_lock:
                dyson.monitor_state["uart"].clear()
                dyson.monitor_state["uart"].update(previous)

    def test_can_activity_is_not_misreported_as_v11_detection(self):
        with dyson.state_lock:
            previous_uart = dict(dyson.monitor_state["uart"])
            previous_can = dict(dyson.monitor_state["can"])
            dyson.monitor_state["uart"].update(last_valid_frame_monotonic=None,
                                                  last_response_frame_monotonic=None,
                                                  last_byte_monotonic=None)
            dyson.monitor_state["can"]["last_frame_monotonic"] = time.monotonic()
        try:
            battery, _, _ = dyson.battery_snapshot()
            self.assertEqual(battery["state"], "activity")
            self.assertNotEqual(battery["label"], "Dyson-Protokoll erkannt")
        finally:
            with dyson.state_lock:
                dyson.monitor_state["uart"].clear()
                dyson.monitor_state["uart"].update(previous_uart)
                dyson.monitor_state["can"].clear()
                dyson.monitor_state["can"].update(previous_can)

    def test_valid_request_echo_is_not_misreported_as_battery(self):
        with dyson.state_lock:
            previous = dict(dyson.monitor_state["uart"])
            dyson.monitor_state["uart"].update(
                last_valid_frame_monotonic=time.monotonic(),
                last_response_frame_monotonic=None,
                last_byte_monotonic=time.monotonic(),
            )
        try:
            battery, _, _ = dyson.battery_snapshot()
            self.assertEqual(battery["state"], "activity")
            self.assertIn("keine Akku-Antwort", battery["label"])
        finally:
            with dyson.state_lock:
                dyson.monitor_state["uart"].clear()
                dyson.monitor_state["uart"].update(previous)

    def test_active_probe_succeeds_only_after_valid_battery_response(self):
        with dyson.state_lock:
            previous_uart = dict(dyson.monitor_state["uart"])
            previous_probe = dict(dyson.probe_state)
            previous_preferred = dyson.auto_preferred_device
            dyson.monitor_state["uart"]["response_frames"] = 4

        try:
            with patch.object(dyson, "serial_candidates", return_value=[
                     {"path": "/dev/ttyUSB0", "real_path": "/dev/ttyUSB0"}
                 ]), \
                 patch.object(dyson.os, "access", return_value=True), \
                 patch.object(dyson.os, "open", return_value=9), \
                 patch.object(dyson.os, "write", side_effect=lambda _fd, data: len(data)), \
                 patch.object(dyson.os, "read", return_value=KNOWN_STUFFED_RESPONSE), \
                 patch.object(dyson.os, "close"), \
                 patch.object(dyson, "configure_serial"), \
                 patch.object(dyson.select, "select", side_effect=lambda reads, writes, _errors, _timeout: (
                     list(reads), list(writes), []
                 )), \
                 patch.object(dyson.termios, "tcdrain"), \
                 patch.object(dyson.time, "sleep"):
                result = dyson.run_active_uart_probe(timeout=0.2, attempts=1)
            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "success")
        finally:
            with dyson.state_lock:
                dyson.monitor_state["uart"].clear()
                dyson.monitor_state["uart"].update(previous_uart)
                dyson.probe_state.clear()
                dyson.probe_state.update(previous_probe)
                dyson.auto_preferred_device = previous_preferred

    def test_active_probe_scans_past_silent_first_adapter(self):
        with dyson.state_lock:
            previous_uart = dict(dyson.monitor_state["uart"])
            previous_probe = dict(dyson.probe_state)
            previous_preferred = dyson.auto_preferred_device

        def selectable(reads, writes, _errors, _timeout):
            if writes:
                return [], list(writes), []
            if reads == [11]:
                return [11], [], []
            return [], [], []

        try:
            with patch.object(dyson, "serial_candidates", return_value=[
                     {"path": "/dev/ttyUSB0", "real_path": "/dev/ttyUSB0"},
                     {"path": "/dev/ttyUSB1", "real_path": "/dev/ttyUSB1"},
                 ]), \
                 patch.object(dyson.os, "access", return_value=True), \
                 patch.object(dyson.os, "open", side_effect=[10, 11]), \
                 patch.object(dyson.os, "write", side_effect=lambda _fd, data: len(data)), \
                 patch.object(dyson.os, "read", return_value=KNOWN_STUFFED_RESPONSE), \
                 patch.object(dyson.os, "close"), \
                 patch.object(dyson, "configure_serial"), \
                 patch.object(dyson.select, "select", side_effect=selectable), \
                 patch.object(dyson.termios, "tcdrain"), \
                 patch.object(dyson.time, "sleep"):
                result = dyson.run_active_uart_probe(timeout=0.02, attempts=1)
            self.assertTrue(result["ok"])
            self.assertEqual(result["device"], "/dev/ttyUSB1")
            self.assertEqual(result["devices"][0]["status"], "no_response")
            self.assertEqual(result["devices"][1]["status"], "success")
        finally:
            with dyson.state_lock:
                dyson.monitor_state["uart"].clear()
                dyson.monitor_state["uart"].update(previous_uart)
                dyson.probe_state.clear()
                dyson.probe_state.update(previous_probe)
                dyson.auto_preferred_device = previous_preferred

    def test_diagnostics_exposes_each_failure_layer(self):
        command_error = {"ok": False, "returncode": 127, "stdout": "", "stderr": "nicht installiert"}
        with patch.object(dyson, "serial_candidates", return_value=[]), \
             patch.object(dyson, "resolve_serial_device", return_value=None), \
             patch.object(dyson, "serial_getty_status", return_value=None), \
             patch.object(dyson, "can_interfaces", return_value=[]), \
             patch.object(dyson, "usb_debug_probes", return_value=[]), \
             patch.object(dyson, "run_command", return_value=command_error):
            report = dyson.build_diagnostics()
        identifiers = {item["id"] for item in report["checks"]}
        self.assertTrue({
            "protocol", "serial_device", "serial_open", "uart_signal", "dyson_frame",
            "active_probe", "swd_probe", "openocd", "can_link",
        }.issubset(identifiers))

    def test_can_setup_stops_at_exact_failed_stage(self):
        responses = [
            {"ok": True, "returncode": 0, "stdout": "", "stderr": ""},
            {"ok": False, "returncode": 2, "stdout": "", "stderr": "Invalid argument"},
        ]
        with patch.object(dyson, "can_interfaces", return_value=[{"name": "can0"}]), \
             patch.object(dyson, "run_command", side_effect=responses):
            ok, detail = dyson.configure_can("can0", 500000)
        self.assertFalse(ok)
        self.assertEqual(detail["stage"], "bitrate")
        self.assertEqual(len(detail["steps"]), 2)


@unittest.skipUnless(hasattr(dyson.app, "test_client"), "Flask ist lokal nicht installiert")
class FlaskRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = dyson.app.test_client()

    def test_dashboard_and_diagnostic_api_render(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Akku sicher abfragen", response.data)
        with patch.object(dyson, "serial_candidates", return_value=[]), \
             patch.object(dyson, "resolve_serial_device", return_value=None), \
             patch.object(dyson, "serial_getty_status", return_value=None), \
             patch.object(dyson, "can_interfaces", return_value=[]), \
             patch.object(dyson, "usb_debug_probes", return_value=[]), \
             patch.object(dyson, "run_command", return_value={
                 "ok": False, "returncode": 127, "stdout": "", "stderr": "nicht installiert"
             }):
            response = self.client.get("/api/diagnostics")
        self.assertEqual(response.status_code, 200)
        self.assertIn("active_probe", {item["id"] for item in response.get_json()["checks"]})

    def test_invalid_serial_path_and_missing_probe_device_fail_closed(self):
        response = self.client.post("/api/serial", json={"device": "/etc/passwd", "baud": 115200})
        self.assertEqual(response.status_code, 400)
        with patch.object(dyson, "serial_candidates", return_value=[]):
            response = self.client.post("/api/serial/probe")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.get_json()["ok"])


if __name__ == "__main__":
    unittest.main()
