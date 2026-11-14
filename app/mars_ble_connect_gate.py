"""Coordinate BLE connection attempts for the FC3000 and DF150-M.

Only connection setup is serialized. An established connection never holds the
gate, so lamp and fan can keep publishing measurements concurrently.
"""
import asyncio

CONNECT_GATE = asyncio.Lock()


def reconnect_delay(failures: int, *, base: float = 4.0, cap: float = 60.0) -> float:
    """Bound failed reconnect attempts without hammering BlueZ."""
    return min(cap, base * (2 ** min(max(0, failures - 1), 4)))
