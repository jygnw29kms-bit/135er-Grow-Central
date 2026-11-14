"""Regression coverage for BLE reconnect coordination."""
import asyncio

from app.mars_ble_connect_gate import CONNECT_GATE, reconnect_delay
from app.mars_fast_fan import fast_fan
from app.mars_fast_lamp import fast_lamp


def test_ble_reconnect_delay_bounded():
    assert reconnect_delay(1) == 4
    assert reconnect_delay(2) == 8
    assert reconnect_delay(3) == 16
    assert reconnect_delay(4) == 32
    assert reconnect_delay(9) == 60
    assert reconnect_delay(0) == 4
    assert reconnect_delay(8, base=3, cap=45) == 45


def test_fast_sessions_share_one_connection_gate():
    # Regression: both modules need a shared gate, not per-device locks.
    from app import mars_fast_fan, mars_fast_lamp
    assert mars_fast_fan.CONNECT_GATE is CONNECT_GATE
    assert mars_fast_lamp.CONNECT_GATE is CONNECT_GATE
    assert fast_fan.lock is not fast_lamp.lock


def test_connect_gate_does_not_hold_lock_forever():
    async def task():
        async with CONNECT_GATE:
            assert CONNECT_GATE.locked()
        assert not CONNECT_GATE.locked()
    asyncio.run(task())
