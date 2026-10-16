import subprocess
import sys
import tarfile
from pathlib import Path


def test_commit_bundle_builder_emits_lf_exact_git_blobs(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "bundle.tar.gz"
    subprocess.run(
        [sys.executable, str(root / "scripts/build-growcentral-commit-bundle.py"), "HEAD", str(output)],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert output.exists()
    with tarfile.open(output, "r:gz") as tf:
        for name in ["web/platform.html", "web/menu-live.js", "app/automation.py", "scripts/build-growcentral-commit-bundle.py"]:
            archived = tf.extractfile(name).read()
            blob = subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=root)
            assert b"\r\n" not in archived
            assert archived == blob
