import time
from types import SimpleNamespace

from app import gui_auth


def test_gui_session_survives_process_memory_loss(tmp_path, monkeypatch):
    target = tmp_path / "sessions.json"
    monkeypatch.setattr(gui_auth, "SESSION_FILE", target)
    gui_auth.SESSIONS.clear()
    token = "restart-safe-token"
    gui_auth._persist_session(token, time.time() + 120)
    request = SimpleNamespace(cookies={gui_auth.COOKIE_NAME: token})
    assert gui_auth.authenticated(request) is True
    gui_auth.SESSIONS.clear()
    assert gui_auth.authenticated(request) is True


def test_logout_removes_persistent_session(tmp_path, monkeypatch):
    target = tmp_path / "sessions.json"
    monkeypatch.setattr(gui_auth, "SESSION_FILE", target)
    token = "logout-token"
    gui_auth._persist_session(token, time.time() + 120)
    assert gui_auth._token_hash(token) in gui_auth._load_persistent_sessions()
    gui_auth._remove_persistent_session(token)
    assert gui_auth._token_hash(token) not in gui_auth._load_persistent_sessions()
