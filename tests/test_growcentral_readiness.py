"""Tests for the read-only Pi/Cloud readiness contract."""
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/verify_growcentral_readiness.py"
spec = importlib.util.spec_from_file_location("gc_readiness", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fake_http(url, *, method="GET"):
    if url.endswith("/api/health"):
        return 200, {}, json.dumps({"ok": True}).encode()
    if url.endswith("/api/v1/rooms"):
        return 401, {}, b""
    if url.endswith("/static/gc-manifest.webmanifest"):
        return 200, {}, json.dumps({"start_url": "/"}).encode()
    if any(url.endswith(x) for x in (
        "/static/gc-final.html", "/static/gc-worker.js",
        "/index.plesk-original.backup.html"
    )):
        return 404, {}, b""
    return 200, {"X-Content-Type-Options": "nosniff"}, b""


class ReadinessTests(unittest.TestCase):
    @patch.object(mod, "http", side_effect=fake_http)
    def test_combined_mode_accepts_offline_hardware(self, _):
        result = mod.check("all", check_services=False, data_root=None)
        self.assertTrue(result["ok"])
        self.assertTrue(result["checks"]["pi:rooms-auth-protection"]["ok"])

    @patch.object(mod, "http", side_effect=fake_http)
    def test_data_integrity_blocks_readiness_on_invalid_storage(self, _, tmp_path=None):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "rooms.json").write_text('{"rooms":[{"id":"room1"}],"plants":[{"id":"plant1","room_id":"room_missing"}]}')
            result = mod.check("pi", check_services=False, data_root=root)
            self.assertFalse(result["ok"])
            self.assertFalse(result["checks"]["pi:data-integrity"]["ok"])

    @patch.object(mod, "http", side_effect=fake_http)
    def test_data_integrity_allows_valid_storage(self, _):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "rooms.json").write_text('{"rooms":[{"id":"room1"}],"archived_rooms":[],"plants":[],"sensor_history":[],"room_journal":[],"grow_events":[],"plant_journal":[],"assignments":{}}')
            result = mod.check("pi", check_services=False, data_root=root)
            self.assertTrue(result["checks"]["pi:data-integrity"]["ok"])

    @patch.object(mod, "http", side_effect=fake_http)
    def test_cloud_requires_correct_start_url(self, mocked):
        result = mod.check("cloud", check_services=False)
        self.assertTrue(result["ok"])
        mocked.side_effect = lambda url, **kw: (
            (200, {}, b'{"start_url":"/ui"}')
            if url.endswith("/gc-manifest.webmanifest") else fake_http(url, **kw)
        )
        result = mod.check("cloud", check_services=False)
        self.assertFalse(result["ok"])
        self.assertFalse(result["checks"]["cloud:pwa-start"]["ok"])

    @patch.object(mod, "http", side_effect=fake_http)
    def test_exposed_deprecated_page_fails(self, mocked):
        mocked.side_effect = lambda url, **kw: (
            (200, {}, b"old") if url.endswith("/static/gc-final.html")
            else fake_http(url, **kw)
        )
        result = mod.check("cloud", check_services=False)
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
