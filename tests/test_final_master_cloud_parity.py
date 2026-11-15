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
    assert "/cloud-master.html?v=20261115-channel-health-1" in PORTAL
    assert "Live-Dashboard anzeigen" not in PORTAL
    # Never expose the legacy telemetry panel during WebSocket authentication.
    assert "const panel=$('remoteDashboard');panel.hidden=true;" in PORTAL
    assert "const panel=$('remoteDashboard');panel.hidden=false;" not in PORTAL


def test_cloud_pwa_starts_at_cloud_login_not_local_pi_route():
    import json
    cloud_manifest = json.loads((ROOT / "cloud/portal/gc-manifest-cloud.webmanifest").read_text(encoding="utf-8"))
    pi_manifest = json.loads((ROOT / "web/gc-manifest.webmanifest").read_text(encoding="utf-8"))
    deploy = (ROOT / "cloud/portal/deploy_cloud_portal.sh").read_text(encoding="utf-8")
    assert cloud_manifest["start_url"] == "/"
    assert cloud_manifest["scope"] == "/"
    assert pi_manifest["start_url"] == "/ui"
    assert 'cp "$repo/cloud/portal/gc-manifest-cloud.webmanifest" "$stage/static/gc-manifest.webmanifest"' in deploy

def test_cloud_soil_tile_survives_initial_room_selection_race():
    assert "const dashboardRoom=rooms.find(r=>r.room_id===growJournal.roomId)||first;" in CLOUD_JS
    assert "soilTileState.dashboard=soilTileReading(dashboardRoom);" in CLOUD_JS
    assert "if(!document.hidden)loadClimateOverview();" in CLOUD_JS
    assert "if(!document.hidden&&!growJournal.roomId)loadRooms();" in CLOUD_JS
    assert "/static/gc-final.js?v=20261115-channel-health-1" in CLOUD

def test_cloud_link_status_does_not_depend_on_disconnected_mars_hydro_devices():
    assert "api('/api/health')" in CLOUD_JS
    assert "const connected=health.status==='fulfilled'&&health.value?.ok===true;" in CLOUD_JS
    assert "text('systemBadge',connected?'Cloud-Kanal verbunden':'Cloud-Kanal prüfen');" in CLOUD_JS
    assert "text('cloudRemoteStatus',connected?'Fernkanal verbunden':'Fernkanal nicht erreichbar');" in CLOUD_JS
    assert "text('systemBadge',ok?'Live verbunden':'Verbindung prüfen');" not in CLOUD_JS
    assert "text('cloudRemoteStatus','Fernkanal separat prüfen');" not in CLOUD_JS
