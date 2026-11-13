"""Read-only Mars Legacy MZF002 parser regression tests."""
import unittest
from app.mars_legacy_telemetry import mzf002_telemetry, fc3000_telemetry


def sample(*, state="1", setpoint="50", temp="17.1", humidity="52.4", rpm="2080"):
    fields = ["0", "opaque-session", "", "MZF002", "1.8", "68756",
              "1", "0", "", "", "", "-1", state, setpoint, "30", "0",
              "opaque-timestamp", "90168", "0,0", temp, humidity, rpm, "0"]
    return ("|".join(fields) + "\n").encode("ascii")



def fc3000_sample(*, state="1", brightness="50", firmware="3.4"):
    fields = ["0", "opaque-session", "", "MARS", firmware, "68756",
              "1", "0", "", "", "-1", "", state, brightness, "0", "0",
              "opaque-timestamp", "97496", "0"]
    return ("|".join(fields) + chr(10)).encode("ascii")

class TestMarsLegacyTelemetry(unittest.TestCase):
    def test_valid_redacted_values(self):
        row = mzf002_telemetry(sample())
        self.assertEqual((row["rpm"], row["temperature_c"], row["humidity_rh"]), (2080, 17.1, 52.4))
        self.assertTrue(row["power_on"])
        self.assertEqual(row["setpoint_percent"], 50)
        self.assertIsNone(row["airflow_cfm"])
        self.assertIsNone(row["pressure_pa"])
        self.assertNotIn("opaque-session", str(row))
        self.assertFalse(row["control_verified"])

    def test_off_retains_setpoint(self):
        row = mzf002_telemetry(sample(state="0", setpoint="100", rpm="0"))
        self.assertFalse(row["power_on"])
        self.assertEqual(row["setpoint_percent"], 100)
        self.assertEqual(row["rpm"], 0)

    def test_fc3000_lamp_status_is_read_only(self):
        for level in ("24", "26", "50", "75", "76", "100"):
            data = fc3000_telemetry(fc3000_sample(brightness=level))
            self.assertIsNotNone(data)
            self.assertTrue(data["power_on"])
            self.assertEqual(data["brightness_percent"], int(level))
            self.assertEqual(data["firmware_version"], "3.4")
            self.assertFalse(data["control_verified"])
            self.assertNotIn("opaque-session", str(data))
        off = fc3000_telemetry(fc3000_sample(state="0", brightness="25"))
        self.assertFalse(off["power_on"])
        self.assertEqual(off["brightness_percent"], 25)

    def test_fc3000_rejects_wrong_family_and_values(self):
        self.assertIsNone(fc3000_telemetry(sample()))
        self.assertIsNone(fc3000_telemetry(fc3000_sample(brightness="101")))
        self.assertIsNone(fc3000_telemetry(fc3000_sample(state="3")))
        self.assertIsNone(fc3000_telemetry(fc3000_sample(firmware="secret")))
        self.assertIsNone(fc3000_telemetry(b"corrupt"))

    def test_reject_wrong_family_and_bad_values(self):
        self.assertIsNone(mzf002_telemetry(sample().replace(b"MZF002", b"MARS")))
        self.assertIsNone(mzf002_telemetry(sample(humidity="125")))
        self.assertIsNone(mzf002_telemetry(sample(rpm="-1")))
        self.assertIsNone(mzf002_telemetry(sample(temp="nan")))
        self.assertIsNone(mzf002_telemetry(sample(setpoint="101")))
        self.assertIsNone(mzf002_telemetry(b"invalid"))


if __name__ == "__main__":
    unittest.main()
