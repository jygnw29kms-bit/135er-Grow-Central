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


def test_scan_retries_when_only_mzf002_seen_and_merges_c260():
    from types import SimpleNamespace

    def result(name, address):
        dev = SimpleNamespace(name=name)
        adv = SimpleNamespace(local_name=name, rssi=-60, service_uuids=[], manufacturer_data={11825: b"1"})
        return {address: (dev, adv)}

    class Scanner:
        calls = 0

        @staticmethod
        async def discover(**kwargs):
            Scanner.calls += 1
            if Scanner.calls == 1:
                return result("MZ_MZF002_68756_A0A3B35EFDC8", "A0:A3:B3:5E:FD:CA")
            return result("MZ_MARS_0_FCB467AEC260", "FC:B4:67:AE:C2:62")

    with patch.object(ble, "adapter_diagnostics", return_value={"state": "ready", "hint": "Bereit"}), \
         patch.object(ble, "BleakScanner", Scanner):
        data = asyncio.run(ble.scan(seconds=3))
    assert data["attempts"] == 2
    assert data["found"] == 2
    assert data["mars_candidate_count"] == 2
    assert {r["name"] for r in data["devices"]} == {
        "MZ_MZF002_68756_A0A3B35EFDC8", "MZ_MARS_0_FCB467AEC260"
    }


def test_scan_stops_early_if_both_mars_devices_visible():
    from types import SimpleNamespace
    dev1 = SimpleNamespace(name="MZ_MZF002_68756_A0A3B35EFDC8")
    adv1 = SimpleNamespace(local_name=dev1.name, rssi=-67, service_uuids=[], manufacturer_data={})
    dev2 = SimpleNamespace(name="MZ_MARS_0_FCB467AEC260")
    adv2 = SimpleNamespace(local_name=dev2.name, rssi=-57, service_uuids=[], manufacturer_data={})

    class Scanner:
        calls = 0

        @staticmethod
        async def discover(**kwargs):
            Scanner.calls += 1
            return {"AA:11": (dev1, adv1), "BB:22": (dev2, adv2)}

    with patch.object(ble, "adapter_diagnostics", return_value={"state": "ready", "hint": "Bereit"}), \
         patch.object(ble, "BleakScanner", Scanner):
        data = asyncio.run(ble.scan(seconds=3))
    assert data["attempts"] == 1
    assert Scanner.calls == 1
    assert data["mars_candidate_count"] == 2


def test_mars_families_are_candidates_not_verified():
    lamp = ble.device_family("MZ_MARS_0_FCB467AEC260", [11827])
    fan = ble.device_family("MZ_MZF002_68756_A0A3B35EFDC8", [11825])
    assert lamp["target_role"] == "light"
    assert fan["target_role"] == "fan"
    assert not lamp["identity_verified"] and not lamp["control_validated"]
    assert not fan["identity_verified"] and not fan["control_validated"]


def test_known_mzf002_gatt_structure_does_not_validate_control_or_telemetry():
    service = {
        "uuid": ble.MZF002_SERVICE,
        "characteristics": [
            {"uuid": ble.MZF002_NOTIFY, "properties": ["notify"]},
            {"uuid": ble.MZF002_WRITE, "properties": ["write"]},
        ],
    }
    cap = ble.summarize_gatt_services([service])
    assert cap["mzf002_transport_confirmed"] is True
    assert cap["sensor_values_decoded"] is False
    assert cap["control_validated"] is False
    unknown = ble.summarize_gatt_services([{
        "uuid": ble.MZF002_SERVICE, "characteristics": [
            {"uuid": ble.MZF002_NOTIFY, "properties": ["read"]}
        ]
    }])
    assert unknown["mzf002_transport_confirmed"] is False
