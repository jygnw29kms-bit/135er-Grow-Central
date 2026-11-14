"""Prevent the Pi UI and authenticated Cloud Final Master from silently drifting."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LOCAL = (ROOT / "web/gc-final.html").read_text(encoding="utf-8")
CLOUD = (ROOT / "cloud/portal/cloud-master.html").read_text(encoding="utf-8")
LOCAL_JS = (ROOT / "web/gc-final.js").read_text(encoding="utf-8")
CLOUD_JS = (ROOT / "cloud/portal/gc-final-cloud.js").read_text(encoding="utf-8")
PORTAL = (ROOT / "cloud/portal/cloud-portal.js").read_text(encoding="utf-8")


def _tiles(page):
    match = re.search(r'<section id="liveTiles"[^>]*>.*?</section>', page, re.S)
    assert match, "Both Final Master pages must have the same telemetry component"
    return match.group(0)


def test_pi_and_cloud_use_identical_telemetry_markup():
    assert _tiles(LOCAL) == _tiles(CLOUD)
    labels = re.findall(r"<span>(Temperatur|Luftfeuchte|Bodenfeuchte|Lichtstufe|Lüfterdrehzahl)</span>", _tiles(LOCAL))
    assert labels == ["Temperatur", "Luftfeuchte", "Bodenfeuchte", "Lichtstufe", "Lüfterdrehzahl"]


def test_soil_measurements_and_phase_judgement_are_not_local_only():
    for template in (LOCAL, CLOUD):
        for marker in ("dashboardSoilValue", "homePhaseClimate", "climatePhasePanel", "climateSoilValue"):
            assert 'id="' + marker + '"' in template
        assert "Cannabis-Entwicklungsphase" not in template
    for script in (LOCAL_JS, CLOUD_JS):
        assert "soilTileReading(" in script
        assert "loadClimateOverview()" in script
        assert "sensor_fault" in script
        assert "out_of_calibration_range" in script
        assert "15*60*1000" in script
        assert "f.power_on===false?'AUS'" in script
        assert "tiles.querySelectorAll('.metric strong').forEach((e,i)" not in script


def test_cloud_only_offers_final_master_after_authentication():
    assert "if(!masterVisible)masterToggle();" in PORTAL
    assert "$('masterToggle').hidden=masterVisible;" in PORTAL
    assert "/cloud-master.html?v=20261114-ui-parity-1" in PORTAL
    assert "Live-Dashboard anzeigen" not in PORTAL
