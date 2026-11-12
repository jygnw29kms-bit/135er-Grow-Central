"""FC3000 isolation checks for offline Mars Legacy ATT analysis."""
import unittest
from scripts.fc3000_legacy_offline_audit import audit
from scripts.mars_legacy_capture_analyze import normalize


def event(device="lamp", action="light_on", session="session-1", payload="01"):
    return normalize({
        "ts": "2026-11-12T18:00:00+01:00",
        "action": action, "direction": "write", "characteristic_uuid": "1234",
        "payload_hex": payload, "device": device, "session": session,
    }, 1)


class FC3000IsolationTests(unittest.TestCase):
    def test_single_lamp_session_is_candidate_only(self):
        result = audit([event()])
        self.assertEqual(result["device_scope"], "FC3000_only")
        self.assertFalse(result["control_enabled"])
        self.assertFalse(result["identity_verified"])
        self.assertFalse(result["groups"][0]["candidates"][0]["validated"])

    def test_ventilator_data_rejected(self):
        with self.assertRaisesRegex(ValueError, "fan data rejected"):
            audit([event(), event(device="fan")])

    def test_unexpected_actions_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported FC3000 action"):
            audit([event(action="fan_75")])

    def test_missing_session_rejected(self):
        with self.assertRaisesRegex(ValueError, "session label"):
            audit([event(session="unknown")])

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            audit([])


if __name__ == "__main__":
    unittest.main()
