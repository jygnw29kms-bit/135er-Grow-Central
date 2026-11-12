"""Never allow public image or operator enrollment distribution from this repo."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class OperatorOnlyImagePolicyTests(unittest.TestCase):
    def test_main_image_build_never_publishes(self):
        source = (WORKFLOWS / "build-pi3-image.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", source)
        self.assertNotIn("\n  push:", source)
        self.assertNotIn("- name: Publish GitHub prerelease", source)
        self.assertNotIn("- name: Upload workflow artifact", source)
        self.assertNotIn("gh release create", source)
        self.assertNotIn("135er-Grow-Central-RPi3Plus-Universal-Image-build-", source)
        self.assertIn("PRIVATE_OPERATOR_ONLY", source)

    def test_legacy_dispatch_workflows_are_disabled(self):
        for name in ("force-current-image-build.yml", "force-image-build-pr.yml"):
            with self.subTest(name=name):
                source = (WORKFLOWS / name).read_text(encoding="utf-8")
                self.assertNotIn("\n  push:", source)
                self.assertNotIn("\n  pull_request:", source)
                self.assertNotIn("gh workflow run", source)
                self.assertNotIn("gh release upload", source)
                self.assertNotIn("actions/upload-artifact", source)

    def test_operator_builder_is_separate(self):
        source = (ROOT / "scripts" / "build-private-pi-image.sh").read_text(encoding="utf-8")
        self.assertIn("--mesh-config", source)
        self.assertIn("--public-key", source)
        self.assertIn("chmod 0600", source)
        self.assertIn("PRIVATE_OWNER_IMAGE_READY", source)


if __name__ == "__main__":
    unittest.main()
