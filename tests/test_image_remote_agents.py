"""Regression gates for universal Grow Central image's remote maintenance baseline.

No external device access or credentials are used.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RemoteAgentImagePolicyTests(unittest.TestCase):
    def test_image_installs_and_enables_service_units(self):
        yml = (ROOT / ".github/workflows/build-pi3-image.yml").read_text(encoding="utf-8")
        self.assertIn("systemctl enable ssh.service grow-central-firstboot-maintenance.service grow-central-remote-watchdog.timer grow-central-mesh-agent.service", yml)
        self.assertIn("/usr/local/sbin/gc-firstboot-maintenance-provision", yml)
        self.assertIn("/usr/local/sbin/gc-remote-watchdog", yml)
        self.assertIn("/etc/systemd/system/ssh.service.d/20-grow-central-hostkeys.conf", yml)
        self.assertIn("rm -f /etc/ssh/ssh_host_*_key", yml)
        self.assertNotIn("sudo install -m 0600 image-builder/firstboot/test-maintenance.pub", yml)

    def test_no_generic_remote_enrollment(self):
        yml = (ROOT / ".github/workflows/build-pi3-image.yml").read_text(encoding="utf-8")
        self.assertIn("default: false", yml)
        self.assertIn("secrets.GC_TEST_PI_MAINTENANCE_PUBKEY != ''", yml)
        svc = (ROOT / "systemd/grow-central-mesh-agent.service").read_text(encoding="utf-8")
        self.assertIn("ConditionPathExists=/opt/grow-central/mesh-agent/meshagent.msh", svc)
        self.assertIn("Restart=on-failure", svc)
        provisioning = (ROOT / "image-builder/firstboot/gc-firstboot-maintenance-provision.sh").read_text(encoding="utf-8")
        self.assertIn("/boot/firmware/gc-maintenance.pub", provisioning)
        self.assertIn("--public-key-file", provisioning)

    def test_firstboot_does_not_disable_key_only_ssh(self):
        yml = (ROOT / ".github/workflows/build-pi3-image.yml").read_text(encoding="utf-8")
        py = (ROOT / "image-builder/firstboot/apply_setup.py").read_text(encoding="utf-8")
        self.assertIn("ssh-keygen -A >/dev/null", yml)
        self.assertIn("run(\"systemctl\", \"enable\", \"--now\", \"ssh.service\")", py)
        self.assertNotIn('run("systemctl", "disable", "--now", unit, check=False)', py)


if __name__ == "__main__":
    unittest.main()
