"""Regression tests for Wi-Fi discovery during first boot.

Run with: python -m unittest discover -s tests -p 'test_wifi_scan_regression.py'
"""
import asyncio
import subprocess
import unittest
from unittest.mock import patch

from app import firstboot, network


class WifiScanRegressionTests(unittest.TestCase):
    @patch("app.network.wifi_interface", return_value="wlan0")
    @patch("app.network._run")
    def test_empty_scan_does_not_block_manual_ssid(self, run, _interface):
        run.return_value = subprocess.CompletedProcess([], 0, "", "")
        result = network._scan_sync()
        self.assertTrue(result["ok"])
        self.assertEqual(result["networks"], [])
        self.assertIn("manuell", result["message"])
        self.assertEqual(run.call_count, 1, "Never issue a duplicate rescan")

    @patch("app.network.wifi_interface", return_value="wlan0")
    @patch("app.network._run")
    def test_escaped_colon_and_deduplication(self, run, _interface):
        run.return_value = subprocess.CompletedProcess(
            [], 0, r"Cafe\\:West:35:WPA2:*" + "\n" + r"Cafe\\:West:80:WPA2:" + "\n", ""
        )
        result = network._scan_sync()
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["networks"][0]["ssid"], "Cafe:West")
        self.assertEqual(result["networks"][0]["signal"], 80)
        self.assertEqual(run.call_count, 1)

    @patch("app.firstboot.setup_active", return_value=True)
    @patch("app.firstboot.wifi_interface", return_value="wlan0")
    @patch("app.firstboot._command")
    @patch("app.firstboot._scan_sync")
    def test_setup_ap_allows_manual_wifi_name(self, scan, command, _wifi, _active):
        scan.return_value = {"ok": True, "networks": [], "message": "No networks"}
        command.return_value = subprocess.CompletedProcess([], 0, "grow-central-setup-ap:wlan0\n", "")
        result = asyncio.run(firstboot.networks())
        self.assertTrue(result["manual_ssid_required"])
        self.assertTrue(result["setup_ap_active"])
        self.assertEqual(result["networks"], [])


if __name__ == "__main__":
    unittest.main()
