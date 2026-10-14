from pathlib import Path
import subprocess

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check-no-dezender-domain.sh'
OLD_HOST = 'dezender' + '.de'


def check(tmp_path, files):
    subprocess.run(['git', 'init', '-q'], cwd=tmp_path, check=True)
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    subprocess.run(['git', 'add', '.'], cwd=tmp_path, check=True)
    return subprocess.run(['bash', str(SCRIPT)], cwd=tmp_path, capture_output=True, text=True)


def test_guard_rejects_legacy_runtime_address(tmp_path):
    result = check(tmp_path, {'app/cloud.py': 'server = "https://' + OLD_HOST + '/GC"'})
    assert result.returncode == 1
    assert 'app/cloud.py:1' in result.stdout


def test_guard_allows_only_exact_external_downloads(tmp_path):
    url = 'https://' + OLD_HOST + '/godseye/grow-light-meter/GrowLightMeter-Android.zip'
    assert check(tmp_path, {'website/index.html': '<a href="' + url + '">Download</a>'}).returncode == 0
    path = tmp_path / 'website/index.html'
    path.write_text('<a href="' + url + '">Download</a><a href="https://' + OLD_HOST + '/GC">Old</a>')
    assert subprocess.run(['bash', str(SCRIPT)], cwd=tmp_path, capture_output=True).returncode == 1


def test_independent_project_exception_does_not_hide_grow_workflows(tmp_path):
    assert check(tmp_path, {'touran-deploy/README.md': 'https://' + OLD_HOST + '/touran'}).returncode == 0
    path = tmp_path / '.github/workflows/deploy-grow.yml'
    path.parent.mkdir(parents=True)
    path.write_text('url: https://' + OLD_HOST + '/GC')
    subprocess.run(['git', 'add', '.'], cwd=tmp_path, check=True)
    assert subprocess.run(['bash', str(SCRIPT)], cwd=tmp_path, capture_output=True).returncode == 1
