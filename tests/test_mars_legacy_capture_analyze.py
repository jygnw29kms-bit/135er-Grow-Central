"""Offline-only tests; run: python -m unittest discover -s tests -p 'test_mars_legacy_capture_analyze.py'"""
import unittest
from scripts.mars_legacy_capture_analyze import normalize, analyze


class LegacyCaptureTests(unittest.TestCase):
    def row(self, action, payload, direction="write", session="a"):
        return normalize({
            "ts": "2026-11-12T17:20:00+01:00",
            "action": action, "direction": direction,
            "characteristic_uuid": "f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d",
            "payload_hex": payload, "session": session, "device": "candidate-lamp",
        }, 1)

    def test_baseline_and_action_are_distinguished(self):
        report = analyze([self.row("idle", "01 02"), self.row("dim_50", "01:02"),
                          self.row("dim_50", "aa bb", session="b")])
        group = report["groups"][0]
        self.assertEqual(group["action"], "dim_50")
        self.assertEqual(group["unique_sessions"], 2)
        self.assertTrue(group["candidates"][0]["candidate_only"])
        self.assertTrue(next(x for x in group["candidates"]
                             if x["payload_hex"] == "0102")["observed_in_idle"])

    def test_rejects_malformed_hex(self):
        with self.assertRaises(ValueError):
            self.row("on", "zz")

    def test_rejects_bad_direction(self):
        with self.assertRaises(ValueError):
            self.row("on", "aa", "raw_write")


if __name__ == "__main__":
    unittest.main()
