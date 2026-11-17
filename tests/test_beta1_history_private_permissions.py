"""Archived room and Mars telemetry must not remain world-readable."""
from pathlib import Path

import pytest

from app import history_archive, mars_history


@pytest.mark.parametrize("module,attr", [
    (history_archive, "DATA_FILE"),
    (mars_history, "DB"),
])
def test_history_database_permissions_are_private(tmp_path, monkeypatch, module, attr):
    file = tmp_path / "history.sqlite3"
    monkeypatch.setattr(module, attr, file)
    with module.connect() as db:
        db.execute("SELECT 1")
    assert file.stat().st_mode & 0o077 == 0
    # A legacy group/world-readable archive is hardened the next time opened.
    file.chmod(0o644)
    with module.connect() as db:
        db.execute("SELECT 1")
    assert file.stat().st_mode & 0o077 == 0


@pytest.mark.parametrize("module,attr", [
    (history_archive, "DATA_FILE"),
    (mars_history, "DB"),
])
def test_database_symlink_is_rejected(tmp_path, monkeypatch, module, attr):
    actual = tmp_path / "actual.sqlite3"
    actual.touch()
    alias = tmp_path / "archive.sqlite3"
    alias.symlink_to(actual)
    monkeypatch.setattr(module, attr, alias)
    with pytest.raises(ValueError, match="symlink"):
        module.connect()
