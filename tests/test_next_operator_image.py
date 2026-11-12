"""Operator Pi next-image inventory gates; no hardware needed."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/build-pi3-image.yml"

class NextOperatorImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_embeds_source_revision_and_distribution_marker(self):
        for required in ("SOURCE_COMMIT", "IMAGE_DISTRIBUTION",
                         "OPERATOR_ONLY", "GITHUB_SHA", "BUILD"):
            with self.subTest(required=required):
                self.assertIn(required, self.workflow)

    def test_contains_mars_hydro_readonly_telemetry(self):
        for name in ("app/mars_hydro_ble.py", "app/mars_legacy_telemetry.py"):
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())
                self.assertIn("test -f /opt/135er-grow-central/" + name, self.workflow)
        decoder = (ROOT / "app/mars_legacy_telemetry.py").read_text(encoding="utf-8")
        self.assertIn("control_verified", decoder)
        self.assertIn("identity_verified", decoder)

    def test_remote_maintenance_and_diagnostics_bundled(self):
        for name in ("gc-firstboot-maintenance-provision",
                     "gc-remote-watchdog", "gc-operator-image-check"):
            with self.subTest(name=name):
                self.assertIn("/usr/local/sbin/" + name, self.workflow)
        self.assertIn("systemctl enable ssh.service", self.workflow)
        self.assertIn("grow-central-mesh-agent.service", self.workflow)
        self.assertTrue((ROOT / "image-builder/firstboot/gc-operator-image-check.sh").is_file())

    def test_no_public_image_or_shared_operator_password(self):
        self.assertNotIn("gh release create", self.workflow)
        self.assertNotIn("Grow-Central-RPi3Plus-Universal-Image-build-", self.workflow)
        self.assertNotIn("\n  push:", self.workflow)
        self.assertNotIn("Linus29052020", self.workflow)
        self.assertNotIn("Linus29952020", self.workflow)

    def test_hardware_paths_in_image(self):
        paths = ("app/provisioning/usb.py", "app/mars_hydro_ble.py",
                 "app/mars_legacy_telemetry.py", "image-builder/firstboot/apply_setup.py",
                 "web/platform.html")
        for name in paths:
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())

if __name__ == "__main__":
    unittest.main()
