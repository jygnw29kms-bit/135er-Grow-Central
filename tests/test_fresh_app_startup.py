from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_entrypoint_imports_in_fresh_python_process(tmp_path: Path):
    env = os.environ.copy()
    env["GC_DATA_DIR"] = str(tmp_path / "data")
    env["GC_CALIBRATION_DB"] = str(tmp_path / "calibration.db")
    result = subprocess.run(
        [sys.executable, "-c", "import app.entrypoint; print(app.entrypoint.app.title)"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "Grow Central" in result.stdout
