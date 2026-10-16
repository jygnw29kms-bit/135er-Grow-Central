import os
import pytest
from pathlib import Path
import subprocess

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check-no-dezender-domain.sh'
OLD_HOST = 'dezender' + '.de'
pytestmark = pytest.mark.skipif(os.name == 'nt', reason='domain guard contract executes a POSIX shell script')

def check(tmp_path, files):
    subprocess.run(['git','init','-q'],cwd=tmp_path,check=True)
    for name,content in files.items():
        path=tmp_path/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(content)
    subprocess.run(['git','add','.'],cwd=tmp_path,check=True)
    return subprocess.run(['bash',str(SCRIPT)],cwd=tmp_path,capture_output=True,text=True)

def test_guard_rejects_legacy_runtime_address(tmp_path):
    result=check(tmp_path,{'app/cloud.py':'server = "https://'+OLD_HOST+'/GC"'})
    assert result.returncode==1
    assert 'app/cloud.py:1' in result.stdout

def test_guard_rejects_legacy_website_download(tmp_path):
    result=check(tmp_path,{'website/index.html':'<a href="https://'+OLD_HOST+'/old.zip">Download</a>'})
    assert result.returncode==1

def test_guard_allows_canonical_domain(tmp_path):
    result=check(tmp_path,{'website/index.html':'<a href="https://grow-central.de/downloads/light-meter/app.zip">Download</a>'})
    assert result.returncode==0
