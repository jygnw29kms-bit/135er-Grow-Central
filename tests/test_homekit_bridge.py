from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.responses import FileResponse

import app.homekit_bridge as homekit


def test_homekit_status_and_qr(tmp_path: Path, monkeypatch):
    status_file = tmp_path / "status.json"
    qr_file = tmp_path / "pairing.svg"
    status_file.write_text('{"running":true,"paired":false,"setup_code":"123-45-678","setup_uri":"X-HM://TEST"}', encoding="utf-8")
    qr_file.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")
    monkeypatch.setattr(homekit, "STATUS_FILE", status_file)
    monkeypatch.setattr(homekit, "QR_FILE", qr_file)
    state = asyncio.run(homekit.homekit_status())
    assert state["available"] is True
    assert state["running"] is True
    assert state["paired"] is False
    assert state["setup_code"] == "123-45-678"
    response = asyncio.run(homekit.homekit_pairing_qr())
    assert isinstance(response, FileResponse)
    assert Path(response.path) == qr_file
    assert response.media_type == "image/svg+xml"


def test_homekit_final_master_ui_and_image_contract():
    root = Path(__file__).resolve().parents[1]
    html = (root / "web/platform.html").read_text(encoding="utf-8")
    js = (root / "web/platform-master.js").read_text(encoding="utf-8")
    css = (root / "web/platform-master.css").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/build-pi3-image.yml").read_text(encoding="utf-8")
    requirements = (root / "requirements.txt").read_text(encoding="utf-8")
    assert 'data-view="applehome"' in html
    assert 'id="homekitQr"' in html
    assert 'id="homekitCode"' in html
    assert "/api/v1/homekit/status" in js
    assert "/api/v1/homekit/pairing.svg" in js
    assert ".homekit-qr-card" in css
    assert "HAP-python[QRCode]==5.0.0" in requirements
    assert "grow-central-homekit.service" in workflow
    assert "ufw allow 51827/tcp" in workflow