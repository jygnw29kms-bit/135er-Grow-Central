"""Exercise the actual route order, not just the isolated GUI router."""
import pytest
from fastapi.testclient import TestClient


def test_master_and_room_workspace_routes_remain_distinct(monkeypatch, tmp_path):
    from app import firstboot, auth_middleware
    from app.entrypoint import app

    provisioned = tmp_path / '.provisioned'
    provisioned.touch()
    monkeypatch.setattr(firstboot, 'MARKER', provisioned)
    monkeypatch.setattr(auth_middleware, 'configured', lambda: True)
    monkeypatch.setattr(auth_middleware, 'authenticated', lambda request: True)
    client = TestClient(app)

    master = client.get('/ui')
    assert master.status_code == 200
    assert 'class="app-shell master-shell"' in master.text
    assert 'id="roomDialog"' not in master.text
    workspace = client.get('/rooms?room=example&tab=sensors')
    assert workspace.status_code == 200
    assert 'id="roomDialog"' in workspace.text
    assert 'id="sensorDiagnostics"' in workspace.text
    assert workspace.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize(('route','status'), [('/rooms',303),('/api/v1/rooms/example/sensors.csv',401)])
def test_room_workspace_requires_gui_authentication(monkeypatch, tmp_path, route, status):
    from app import firstboot, auth_middleware
    from app.entrypoint import app

    provisioned = tmp_path / '.provisioned'
    provisioned.touch()
    monkeypatch.setattr(firstboot, 'MARKER', provisioned)
    monkeypatch.setattr(auth_middleware, 'configured', lambda: True)
    monkeypatch.setattr(auth_middleware, 'authenticated', lambda request: False)
    response = TestClient(app).get(route, follow_redirects=False)
    assert response.status_code == status
    if status == 303:
        assert response.headers['location'] == '/login'
