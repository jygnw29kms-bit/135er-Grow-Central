"""Runtime audit contract, using temporary fake install trees only."""
import importlib.util
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/verify_pi_installed_files.py"
SPEC = importlib.util.spec_from_file_location("pi_runtime_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RuntimeAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.src = Path(self.tmp.name) / "src"
        self.install = Path(self.tmp.name) / "installed"
        for base in (self.src, self.install):
            (base / "app").mkdir(parents=True)
            (base / "web").mkdir()
            (base / "app" / "entrypoint.py").write_text("ok\n")
            (base / "README.md").write_text("test\n")
        (self.src / "web" / "console.html").write_text("legacy")
        (self.src / "web" / "gc-final.js").write_text("current")
        (self.install / "web" / "gc-final.js").write_text("current")

    def tearDown(self):
        self.tmp.cleanup()

    def test_runtime_file_set_excludes_deprecated_web_pages(self):
        names = MODULE.runtime_files(self.src)
        self.assertIn("app/entrypoint.py", names)
        self.assertIn("web/gc-final.js", names)
        self.assertNotIn("web/console.html", names)

    def test_drift_is_detected(self):
        with redirect_stdout(StringIO()) as output:
            rc = MODULE.verify(self.src, self.install, ["app/entrypoint.py", "README.md"])
        self.assertEqual(rc, 0)
        self.assertIn("2/2", output.getvalue())
        (self.install / "README.md").write_text("drift")
        with redirect_stdout(StringIO()) as output:
            rc = MODULE.verify(self.src, self.install, ["app/entrypoint.py", "README.md"])
        self.assertEqual(rc, 1)
        self.assertIn("DIFF", output.getvalue())


if __name__ == "__main__":
    unittest.main()
