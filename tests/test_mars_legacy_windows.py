"""Offline tests for the Mars Legacy BLE time-window converter."""
import unittest
from scripts.mars_legacy_windows import convert


class WindowTests(unittest.TestCase):
    def test_half_open_and_exclusive_session(self):
        capture = [
            {"time_epoch": str(t), "device": "lamp", "session": "s1",
             "direction": "write", "characteristic_uuid": "1234", "payload_hex": "aa"}
            for t in (1, 2, 3)
        ]
        capture.append({"time_epoch": "2", "device": "fan", "session": "s1",
                        "direction": "write", "characteristic_uuid": "1234", "payload_hex": "bb"})
        windows = [{"start_epoch": "2", "end_epoch": "3", "device": "lamp",
                    "session": "s1", "action": "dim_50"}]
        self.assertEqual([x["action"] for x in convert(capture, windows)],
                         ["idle", "dim_50", "idle", "idle"])

    def test_overlapping_rejected(self):
        base = {"device": "lamp", "session": "s1", "action": "on"}
        with self.assertRaises(ValueError):
            convert([], [dict(base, start_epoch="1", end_epoch="3"),
                         dict(base, start_epoch="2", end_epoch="4")])

    def test_invalid_time_rejected(self):
        with self.assertRaises(ValueError):
            convert([], [{"device": "lamp", "session": "s", "action": "on",
                          "start_epoch": "nan", "end_epoch": "2"}])


if __name__ == "__main__":
    unittest.main()
