"""Coordinate BLE connection attempts for the FC3000 and DF150-M.

Only connection setup is serialized. An established connection never holds the
gate, so lamp and fan can keep publishing measurements concurrently.
"""
import asyncio

CONNECT_GATE = asyncio.Lock()


def reconnect_delay(failures: int, *, base: float = 4.0, cap: float = 60.0) -> float:
    """Bound failed reconnect attempts without hammering BlueZ."""
    return min(cap, base * (2 ** min(max(0, failures - 1), 4)))


class ReconnectLogLimiter:
    """Group repeated BLE errors without changing retry behavior.

    Emit the first failure, a changed error type, or one summary per interval.
    Counters reset only after a successful connection.
    """

    def __init__(self, *, interval: float = 900.0):
        self.interval = interval
        self.last_emitted = None
        self.last_error = None
        self.suppressed = 0

    def failure(self, logger, device: str, exc: Exception, *, now=None):
        import time

        timestamp = time.monotonic() if now is None else now
        error = type(exc).__name__
        if (
            self.last_emitted is None
            or self.last_error != error
            or timestamp - self.last_emitted >= self.interval
        ):
            logger.warning(
                "%s BLE unavailable: %s (suppressed %d repeated failures)",
                device, error, self.suppressed,
            )
            self.last_emitted = timestamp
            self.last_error = error
            self.suppressed = 0
            return True
        self.suppressed += 1
        return False

    def recovered(self, logger, device: str):
        if self.last_emitted is not None:
            logger.info(
                "%s BLE reconnected (suppressed %d repeated failures)",
                device, self.suppressed,
            )
        self.last_emitted = None
        self.last_error = None
        self.suppressed = 0
