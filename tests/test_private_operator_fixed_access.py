"""Private operator image: fixed-password sudo and bundled management agent policy."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class OperatorAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder=(ROOT/"scripts/build-private-pi-image.sh").read_text()
        cls.firstboot=(ROOT/"image-builder/firstboot/gc-firstboot-maintenance-provision.sh").read_text()
        cls.patch=(ROOT/"scripts/patch-private-operator-image-access.sh").read_text()
        cls.agent=(ROOT/"systemd/grow-central-mesh-agent.service").read_text()

    def test_fixed_password_never_in_source(self):
        self.assertIn("--operator-password-file",self.builder)
        self.assertIn("openssl passwd -6 -stdin",self.builder)
        self.assertIn("operator-maint-password.hash",self.builder)
        self.assertIn("operator-maint-password.hash",self.firstboot)
        self.assertIn('usermod --password "$password_hash" gc-maint',self.firstboot)
        self.assertIn("Match User gc-maint",self.firstboot)
        self.assertIn("PasswordAuthentication yes",self.firstboot)
        self.assertIn("sshd -t",self.firstboot)

    def test_agent_is_real_binary_not_just_unit(self):
        self.assertIn('install -m 0700 "$agent"',self.builder)
        self.assertIn('install -m 0600 "$config"',self.builder)
        self.assertIn("grow-central-mesh-agent.service",self.builder)
        self.assertIn("Restart=on-failure",self.agent)
        self.assertIn("ExecStart=/opt/grow-central/mesh-agent/meshagent",self.agent)

    def test_existing_private_image_can_be_upgraded_safely(self):
        self.assertIn("fixed-maintenance.img",self.patch)
        self.assertIn("openssl passwd -6 -stdin",self.patch)
        self.assertIn("operator-maint-password.hash",self.patch)
        self.assertIn("gc-firstboot-maintenance-provision.sh",self.patch)
        self.assertIn("sha256sum",self.patch)

    def test_real_sudo_not_just_group_membership(self):
        installer=(ROOT/"scripts/install-gc-maintenance-agent.sh").read_text()
        firstboot_unit=(ROOT/"systemd/grow-central-firstboot-maintenance.service").read_text()
        finalizer=(ROOT/"scripts/finalize-private-operator-image-root.sh").read_text()
        self.assertIn('runuser -u "$USER_NAME" -- sudo -n /usr/bin/id -u',installer)
        self.assertIn('[[ "$verified_uid" != 0 ]]',installer)
        self.assertIn('MAINTENANCE_SUDO_VERIFIED=UID_0',installer)
        self.assertIn('NoNewPrivileges=no',firstboot_unit)
        self.assertIn("operator-maint-password.hash",finalizer)
        self.assertIn("grow-central-mesh-agent.service",finalizer)

    def test_no_shared_secret_published(self):
        source="\n".join((self.builder,self.firstboot,self.patch))
        self.assertNotIn("Linus29052020",source)
        self.assertNotIn("Linus29952020",source)
        self.assertNotIn("PRIVATE KEY-----",source)

if __name__=="__main__":
    unittest.main()
