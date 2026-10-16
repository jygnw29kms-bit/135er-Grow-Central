from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from app.grow_photo_ui import GrowPhotoUiMiddleware


def test_grow_enhancements_are_injected_only_into_product_shell():
    app = FastAPI()
    app.add_middleware(GrowPhotoUiMiddleware)

    @app.get("/")
    async def product():
        return HTMLResponse('<html><body><section id="growlog"></section><script src="/static/menu-live.js"></script></body></html>')

    @app.get("/setup")
    async def setup():
        return HTMLResponse('<html><body>Setup</body></html>')

    client = TestClient(app)
    product = client.get("/")
    assert product.status_code == 200
    assert '/static/grow-photos.js?v=20261016-photo1' in product.text
    assert '/static/plant-doctor.js?v=20261016-doctor1' in product.text
    assert product.headers["cache-control"] == "no-store"

    setup = client.get("/setup")
    assert setup.status_code == 200
    assert "grow-photos.js" not in setup.text
    assert "plant-doctor.js" not in setup.text


def test_photo_ui_uses_camera_upload_and_canonical_backend():
    source = Path("web/grow-photos.js").read_text(encoding="utf-8")
    assert "capture=\"environment\"" in source
    assert "/api/v1/grow-photos" in source
    assert "/plants`" in source
    assert "stopImmediatePropagation" in source
    assert "8 MiB" in source


def test_plant_doctor_uses_existing_diagnosis_api_and_sensor_results():
    source = Path("web/plant-doctor.js").read_text(encoding="utf-8")
    assert "/diagnosis`" in source
    assert "save_event:true" in source
    assert "sensor_snapshot" in source
    assert "Mögliche Ursachen, keine sichere Diagnose" in source
    assert "gcDoctorSymptoms" in source
    assert "gcDoctorZone" in source
