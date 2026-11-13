"""Offline regression tests for owner opt-in Mars Hydro fan cloud adapter."""
import os
import unittest
from unittest.mock import patch

from app.mars_hydro_cloud_fan import configured, normalized_fan, FanControl


class TestMarsCloudFan(unittest.TestCase):
    def test_off_by_default_even_with_credentials(self):
        with patch.dict(os.environ, {
            "GC_MARS_CLOUD_ENABLE": "0",
            "GC_MARS_CLOUD_EMAIL": "test@example.invalid",
            "GC_MARS_CLOUD_PASSWORD": "test-secret",
        }):
            self.assertFalse(configured())

    def test_requires_credentials(self):
        with patch.dict(os.environ, {
            "GC_MARS_CLOUD_ENABLE": "1",
            "GC_MARS_CLOUD_EMAIL": "",
            "GC_MARS_CLOUD_PASSWORD": "",
        }):
            self.assertFalse(configured())

    def test_single_fan_configuration_does_not_require_id(self):
        with patch.dict(os.environ, {
            "GC_MARS_CLOUD_ENABLE": "1",
            "GC_MARS_CLOUD_EMAIL": "test@example.invalid",
            "GC_MARS_CLOUD_PASSWORD": "test-secret",
        }):
            self.assertTrue(configured())

    def test_normalized_state_excludes_credentials_and_id(self):
        result = normalized_fan({
            "id": "private-serial", "deviceName": "DF150-M",
            "deviceLightRate": "59", "temperature": 19.2,
            "token": "private-token",
        })
        self.assertEqual(result["speed_percent"], 59)
        self.assertNotIn("id", result)
        self.assertNotIn("token", result)
        self.assertNotIn("private-serial", str(result))
        self.assertNotIn("private-token", str(result))

    def test_bad_speed_is_not_accepted_as_state(self):
        self.assertIsNone(normalized_fan({"deviceLightRate": "nan"})["speed_percent"])
        self.assertIsNone(normalized_fan({"deviceLightRate": 120})["speed_percent"])

    def test_values_validated_by_request_contract(self):
        self.assertEqual(FanControl(action="speed", value=25, confirm=True).value, 25)
        from pydantic import ValidationError
        for action, value in (("speed", 101), ("other", 50)):
            with self.subTest(action=action, value=value):
                with self.assertRaises(ValidationError):
                    FanControl(action=action, value=value, confirm=True)


if __name__ == "__main__":
    unittest.main()
