"""The Pi firmware staging update must restore code and files on a failed start."""
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import pytest

pytestmark = pytest.mark.skipif(os.name == 'nt', reason='sensor TLS installer requires POSIX root/systemd APIs')


def load():
    spec = importlib.util.spec_from_file_location('sensor_tls_installer', Path(__file__).resolve().parents[1]/'scripts/apply-sensor-tls-diagnostics.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_failed_restart_restores_existing_firmware_and_code(tmp_path, monkeypatch):
    module = load()
    repo = Path(__file__).resolve().parents[1]
    root = tmp_path/'pi'
    target = root/'app/provisioning/usb.py'
    target.parent.mkdir(parents=True)
    original = b'# existing tested installation\n'
    target.write_bytes(original)
    (root/'BUILD').write_text('369\n')
    destination = root/'firmware/gc-soil-node/dist'
    destination.mkdir(parents=True)
    (destination/'manifest.json').write_bytes(b'old manifest')
    (destination/'firmware.bin').write_bytes(b'old firmware')
    monkeypatch.setattr(module, 'ROOT', root)
    monkeypatch.setattr(module, 'BACKUPS', tmp_path/'backups')
    monkeypatch.setattr(module, 'OLD_SHA', hashlib.sha256(original).hexdigest())
    monkeypatch.setattr(module.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(sys, 'argv', ['installer'])
    def download(relative, output, digest):
        output.write_bytes((repo/relative).read_bytes())
    monkeypatch.setattr(module, 'download', download)
    calls = []
    def run(*args):
        calls.append(args)
        if args == ('systemctl', 'start', module.UNIT):
            raise RuntimeError('simulated service failure')
    monkeypatch.setattr(module, 'run', run)
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **kw: None)
    with pytest.raises(RuntimeError, match='simulated'):
        module.main()
    assert target.read_bytes() == original
    assert (destination/'manifest.json').read_bytes() == b'old manifest'
    assert (destination/'firmware.bin').read_bytes() == b'old firmware'
    assert not (destination/'bootloader.bin').exists()
    assert ('systemctl', 'stop', module.UNIT) in calls


def test_installer_uses_image_application_unit():
    module = load()
    repo = Path(__file__).resolve().parents[1]
    assert module.UNIT == '135er-grow-central.service'
    assert f'/etc/systemd/system/{module.UNIT}' in (repo/'.github/workflows/build-pi3-image.yml').read_text()
