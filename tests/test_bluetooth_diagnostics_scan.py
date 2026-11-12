"""Bluetooth discovery diagnostics do not claim pairing or hardware control."""
from unittest.mock import patch
import asyncio
import pytest
from app import mars_hydro_ble as ble


def test_controller_ready():
    def command(*args):
        if args[0] == "bluetoothctl":
            return 0, "Controller DC:A6:32:00:00:00 (public)\n\tPowered: yes\n"
        return 0, "0: hci0: Bluetooth\n\tSoft blocked: no\n\tHard blocked: no"
    with patch.object(ble, "_command", side_effect=command):
        state = ble.adapter_diagnostics()
    assert state["state"] == "ready"
    assert state["powered"] is True


def test_blocked_radio_not_treated_as_empty_scan():
    def command(*args):
        if args[0] == "bluetoothctl":
            return 0, "Controller DC:A6:32:00:00:00\n\tPowered: yes\n"
        return 0, "0: hci0: Bluetooth\n\tSoft blocked: yes"
    with patch.object(ble, "_command", side_effect=command):
        state = ble.adapter_diagnostics()
    assert state["state"] == "radio_blocked"


def test_zero_devices_retries_and_reports_advertisement_absence():
    class Scanner:
        calls = 0
        @staticmethod
        async def discover(**kwargs):
            Scanner.calls += 1
            assert kwargs["return_adv"] is True
            return {}
    with patch.object(ble, "adapter_diagnostics", return_value={"state": "ready", "hint": "Bereit"}), \
         patch.object(ble, "BleakScanner", Scanner):
        result = asyncio.run(ble.scan(seconds=3))
    assert result["found"] == 0
    assert result["attempts"] == 2
    assert result["scan_seconds"] == 6
    assert Scanner.calls == 2
    assert "keine BLE-Werbesignale" in result["message"]


def test_blocked_adapter_does_not_start_scan():
    with patch.object(ble, "adapter_diagnostics", return_value={"state": "radio_blocked", "hint": "Funk gesperrt"}):
        result = asyncio.run(ble.scan())
    assert result["attempts"] == 0
    assert result["adapter"]["state"] == "radio_blocked"
