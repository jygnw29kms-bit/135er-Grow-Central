import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('project_boundaries', Path(__file__).resolve().parents[1] / 'scripts/check-grow-project-boundaries.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def test_printer_assets_and_workflow_rejected(tmp_path):
    assert len(checker.violations(tmp_path, ['website/downloads/3d/case.stl', '.github/workflows/deploy-printbench.yml'])) == 2


def test_printer_runtime_integration_rejected(tmp_path):
    (tmp_path / 'app').mkdir()
    (tmp_path / 'app/printer.py').write_text('service = "PRINTBENCH"')
    assert checker.violations(tmp_path, ['app/printer.py'])


def test_grow_camera_is_retained(tmp_path):
    (tmp_path / 'app').mkdir()
    (tmp_path / 'app/camera.py').write_text('command = ["ffmpeg", "-f", "v4l2"]')
    assert checker.violations(tmp_path, ['app/camera.py']) == []
