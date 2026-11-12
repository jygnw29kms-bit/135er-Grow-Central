"""Read-only Mars Legacy MZF002 parser regression tests."""
import unittest
from app.mars_legacy_telemetry import mzf002_telemetry


def sample(*, state="1", setpoint="50", temp="17.1", humidity="52.4", rpm="2080"):
    fields = ["0", "opaque-session", "", "MZF002", "1.8", "68756",
              "1", "0", "", "", "", "-1", state, setpoint, "30", "0",
              "opaque-timestamp", "90168", "0,0", temp, humidity, rpm, "0"]
    return ("|".join(fields) + "\n").encode("ascii")


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

    def test_reject_wrong_family_and_bad_values(self):
        self.assertIsNone(mzf002_telemetry(sample().replace(b"MZF002", b"MARS")))
        self.assertIsNone(mzf002_telemetry(sample(humidity="125")))
        self.assertIsNone(mzf002_telemetry(sample(rpm="-1")))
        self.assertIsNone(mzf002_telemetry(sample(temp="nan")))
        self.assertIsNone(mzf002_telemetry(sample(setpoint="101")))
        self.assertIsNone(mzf002_telemetry(b"invalid"))


if __name__ == "__main__":
    unittest.main()
