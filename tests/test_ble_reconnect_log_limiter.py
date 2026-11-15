"""BLE reconnect log throttling and recovery without hardware."""
import logging
import unittest
from app.mars_ble_connect_gate import ReconnectLogLimiter, reconnect_delay


class Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


class LogLimiterTests(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("gc_ble_limiter_test")
        self.logger.setLevel(logging.DEBUG)
        self.capture = Capture()
        self.logger.addHandler(self.capture)

    def tearDown(self):
        self.logger.removeHandler(self.capture)

    def test_repeated_offline_errors_are_grouped(self):
        limiter = ReconnectLogLimiter(interval=900)
        self.assertTrue(limiter.failure(self.logger, "FC3000", ValueError(), now=0))
        for n in range(1, 10):
            self.assertFalse(limiter.failure(self.logger, "FC3000", ValueError(), now=n * 30))
        self.assertEqual(len(self.capture.messages), 1)
        self.assertTrue(limiter.failure(self.logger, "FC3000", ValueError(), now=901))
        self.assertIn("suppressed 9", self.capture.messages[-1])

    def test_changed_error_is_logged_immediately(self):
        limiter = ReconnectLogLimiter()
        limiter.failure(self.logger, "MZF002", ValueError(), now=0)
        self.assertTrue(limiter.failure(self.logger, "MZF002", RuntimeError(), now=1))
        self.assertEqual(len(self.capture.messages), 2)

    def test_recovery_resets_throttle(self):
        limiter = ReconnectLogLimiter()
        limiter.failure(self.logger, "FC3000", ValueError(), now=0)
        limiter.failure(self.logger, "FC3000", ValueError(), now=1)
        limiter.recovered(self.logger, "FC3000")
        self.assertIn("suppressed 1", self.capture.messages[-1])
        self.assertTrue(limiter.failure(self.logger, "FC3000", ValueError(), now=2))

    def test_backoff_is_unchanged(self):
        self.assertEqual(reconnect_delay(1), 4)
        self.assertEqual(reconnect_delay(2), 8)
        self.assertEqual(reconnect_delay(50), 60)


if __name__ == "__main__":
    unittest.main()
