"""Cloud read relay: climate and room history stay scoped and read-only."""
import asyncio
import json
from types import SimpleNamespace
from urllib.parse import quote

from local.cloud_link import remote_agent


class WS:
    def __init__(self, requests):
        self.requests=requests
        self.out=[]
    def __aiter__(self):
        async def iterator():
            for req in self.requests:
                yield json.dumps(req)
        return iterator()
    async def send(self, raw):
        self.out.append(json.loads(raw))


class Local:
    def __init__(self):
        self.paths=[]
    async def get(self, path, **kwargs):
        self.paths.append(path)
        return SimpleNamespace(is_success=True,json=lambda: {"ok":True})


def request(path):
    return {"type":"read","request_id":"diagnostic-1","path":path}


def test_cloud_can_read_phase_climate(monkeypatch):
    monkeypatch.setattr(remote_agent,"local_headers",lambda:{})
    ws=WS([request("/api/v1/rooms/climate-overview")])
    local=Local()
    asyncio.run(remote_agent.serve(ws,local))
    assert local.paths==[remote_agent.LOCAL_API+"/api/v1/rooms/climate-overview"]
    assert ws.out[0]["ok"] is True


def test_cloud_history_requires_room_and_known_parameters(monkeypatch):
    monkeypatch.setattr(remote_agent,"local_headers",lambda:{})
    valid="/api/v1/history/points?room_id=room_abc123&limit=10000&start="+quote("2026-11-14T00:00:00.000Z",safe="")
    invalid=[
        "/api/v1/history/points",
        "/api/v1/history/points?room_id=../etc",
        "/api/v1/history/points?room_id=room_abc123&limit=99999",
        "/api/v1/history/points?room_id=room_abc123&extra=hidden",
        "/api/v1/history/points?room_id=room_abc123&room_id=room_abc124",
        "/api/v1/history/points?room_id=room_abc123&limit=nan",
    ]
    ws=WS([request(valid),*(request(p) for p in invalid)])
    local=Local()
    asyncio.run(remote_agent.serve(ws,local))
    assert local.paths==[remote_agent.LOCAL_API+valid]
    assert ws.out[0]["ok"] is True
    assert all(row.get("error")=="path_not_allowed" for row in ws.out[1:])


def test_status_bar_transport_separate_from_ble():
    from pathlib import Path
    code=(Path(__file__).resolve().parents[1]/"web/gc-final.js").read_text()
    assert "function showBleQuality(kind,status)" in code
    assert "function setNetworkIndicator(isConnected,isCloud)" in code
    block=code.split("async function refreshLive(){",1)[1].split("async function command(",1)[0]
    assert "setNetworkIndicator(" not in block
    assert "text('systemBadge'," not in block
    assert "showBleQuality('fan',fan)" in block
