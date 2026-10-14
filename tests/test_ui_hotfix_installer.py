import hashlib
import importlib.util
import io
from pathlib import Path
import subprocess
from types import SimpleNamespace
import pytest

spec=importlib.util.spec_from_file_location('ui_hotfix',Path(__file__).resolve().parents[1]/'scripts/apply-grow-ui-hotfix.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)


@pytest.fixture
def installation(tmp_path,monkeypatch):
    root=tmp_path/'app';root.mkdir();(root/'BUILD').write_text('369')
    old=b'value = 1\n';new=b'value = 2\n'
    (root/'sample.py').write_bytes(old)
    monkeypatch.setattr(installer,'ROOT',root)
    monkeypatch.setattr(installer,'BACKUP_ROOT',tmp_path/'backups')
    monkeypatch.setattr(installer,'FILES',{'sample.py':{'base':hashlib.sha256(old).hexdigest(),'new':hashlib.sha256(new).hexdigest()}})
    monkeypatch.setattr(installer.os,'geteuid',lambda:0)
    monkeypatch.setattr(installer.os,'chown',lambda *_:None)
    monkeypatch.setattr(installer.grp,'getgrnam',lambda _:SimpleNamespace(gr_gid=1000))
    monkeypatch.setattr('sys.argv',['hotfix'])
    calls=[];monkeypatch.setattr(installer,'run',lambda *args:calls.append(args))
    monkeypatch.setattr(installer.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0))
    monkeypatch.setattr(installer.urllib.request,'urlopen',lambda url,**k:io.BytesIO(b'{"ok":true}' if '/api/health' in url else new))
    return root,old,new,calls


def test_hotfix_downloads_checks_backs_up_and_restarts(installation):
    root,old,new,calls=installation
    installer.main()
    assert (root/'sample.py').read_bytes()==new
    saved=list(installer.BACKUP_ROOT.glob('ui-hotfix-*/sample.py'))
    assert len(saved)==1 and saved[0].read_bytes()==old
    assert calls==[('systemctl','stop',installer.UNIT),('systemctl','start',installer.UNIT)]


def test_hotfix_preserves_unrecognized_local_edits(installation):
    root,old,new,calls=installation
    (root/'sample.py').write_text('custom = 99')
    with pytest.raises(RuntimeError,match='Lokale Änderung'):installer.main()
    assert (root/'sample.py').read_text()=='custom = 99' and not calls


def test_hotfix_rolls_back_when_restart_fails(installation,monkeypatch):
    root,old,new,calls=installation
    def run(*args):
        if args[1]=='start':raise subprocess.CalledProcessError(1,args)
    monkeypatch.setattr(installer,'run',run)
    with pytest.raises(subprocess.CalledProcessError):installer.main()
    assert (root/'sample.py').read_bytes()==old
