"""Regression tests for read-only Mars BLE controller freshness diagnostics."""
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_mars_ble_freshness.py"
spec = importlib.util.spec_from_file_location("mars_ble_freshness_check", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = datetime.now(timezone.utc)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, name, stamp):
        (self.root / name).write_text(json.dumps({"timestamp": stamp.isoformat(), "power_on": True}))

    def test_two_recent_controller_states(self):
        for filename, _ in module.DEVICES.values():
            self.save(filename, self.now - timedelta(seconds=12))
        self.assertEqual(module.inspect(self.root, 120, self.now), 0)

    def test_stale_and_missing_rejected(self):
        self.save("mars-fan-live.json", self.now - timedelta(hours=11))
        self.assertEqual(module.inspect(self.root, 120, self.now), 2)

    def test_invalid_timestamp_rejected(self):
        for filename, _ in module.DEVICES.values():
            (self.root / filename).write_text('{"timestamp":"not-a-date"}')
        self.assertEqual(module.inspect(self.root, 120, self.now), 2)

    def test_future_timestamp_rejected(self):
        for filename, _ in module.DEVICES.values():
            self.save(filename, self.now + timedelta(seconds=20))
        self.assertEqual(module.inspect(self.root, 120, self.now), 2)


if __name__ == "__main__":
    unittest.main()
