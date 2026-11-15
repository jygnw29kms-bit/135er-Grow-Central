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
    assert "/cloud-master.html?v=20261115-status-parity-1" in PORTAL
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
    assert "/static/gc-final.js?v=20261115-status-parity-1" in CLOUD

def test_cloud_link_status_does_not_depend_on_disconnected_mars_hydro_devices():
    assert "api('/api/health')" in CLOUD_JS
    assert "const connected=health.status==='fulfilled'&&health.value?.ok===true;" in CLOUD_JS
    assert "setNetworkIndicator(connected,true);" in CLOUD_JS
    assert "text('cloudRemoteStatus',connected?'Fernkanal verbunden':'Fernkanal nicht erreichbar');" in CLOUD_JS
    assert "text('systemBadge',ok?'Live verbunden':'Verbindung prüfen');" not in CLOUD_JS
    assert "text('cloudRemoteStatus','Fernkanal separat prüfen');" not in CLOUD_JS

def test_cloud_climate_overview_is_declared_before_strict_mode_assignment():
    # Regresses the iPhone Cloud screenshot: missing declaration made both
    # phase evaluation and soil-moisture rendering fail after an HTTP 200.
    declaration = CLOUD_JS.index("let climateOverview={rooms:[]};")
    loader = CLOUD_JS.index("async function loadClimateOverview(){")
    assignment = CLOUD_JS.index("climateOverview=data;", loader)
    assert declaration < loader < assignment
    assert "'use strict';" in CLOUD_JS


def test_mobile_camera_stays_inside_final_master_viewport():
    local_css = (ROOT / "web/gc-final.css").read_text(encoding="utf-8")
    cloud_css = (ROOT / "cloud/portal/gc-final-cloud.css").read_text(encoding="utf-8")
    required = (
        "#largeCam.camframe.large{width:100%;max-width:100%;min-width:0;min-height:0;",
        "#camera .camera-toolbar{max-width:100%;min-width:0}",
        "#largeCam .osd{max-width:calc(100% - 16px);overflow-wrap:anywhere}",
    )
    for css in (local_css, cloud_css):
        for rule in required:
            assert rule in css
    assert "/static/gc-final.css?v=20261115-status-parity-1" in LOCAL
    assert "/static/gc-final.css?v=20261115-status-parity-1" in CLOUD


def test_camera_osd_shows_fresh_soil_without_mars_hydro_ble():
    for js in (LOCAL_JS, CLOUD_JS):
        assert "function updateCameraClimateOverlay(){" in js
        assert "if(soilTileState.dashboard.valid)parts.push('🌱 Boden '+soilTileState.dashboard.value);" in js
        assert "cameraClimateMetrics.temperature=f&&Number.isFinite(f.temperature_c)?f.temperature_c:null;" in js
        assert "cameraClimateMetrics.humidity=f&&Number.isFinite(f.humidity_rh)?f.humidity_rh:null;" in js
        assert "const overlay=parts.length?parts.join(' · '):'Keine aktuellen Messwerte';" in js
        assert "Keine aktuellen Klimamesswerte" not in js
    assert "/static/gc-final.js?v=20261115-status-parity-1" in CLOUD
    assert "/static/gc-final.js?v=20261115-status-parity-1" in LOCAL


def _function_source(script, start, next_function):
    begin = script.index(start)
    end = script.index(next_function, begin)
    return script[begin:end].strip()


def test_local_and_cloud_camera_osd_have_exact_same_implementation():
    # Transport handlers may differ; user-visible OSD rendering must not.
    start = "let cameraClimateMetrics={temperature:null,humidity:null};"
    end = "function updateSoilTiles(){"
    assert _function_source(LOCAL_JS, start, end) == _function_source(CLOUD_JS, start, end)
    # Update call must remain in the shared soil-rendering flow.
    for script in (LOCAL_JS, CLOUD_JS):
        update = _function_source(script, "function updateSoilTiles(){", "function setMetrics(")
        assert "updateCameraClimateOverlay();" in update


def test_local_and_cloud_mobile_camera_styles_are_identical():
    marker = "/* Camera layout: prevent wide iPhone frames from expanding the page/iframe. */"
    local_css = (ROOT / "web/gc-final.css").read_text(encoding="utf-8")
    cloud_css = (ROOT / "cloud/portal/gc-final-cloud.css").read_text(encoding="utf-8")
    assert marker in local_css and marker in cloud_css
    assert local_css[local_css.index(marker):].strip() == cloud_css[cloud_css.index(marker):].strip()


def test_cloud_and_local_mobile_navigation_match_exactly():
    pattern = r'<nav class="mobilebar"[^>]*>.*?</nav>'
    local_nav = re.search(pattern, LOCAL, re.S)
    cloud_nav = re.search(pattern, CLOUD, re.S)
    assert local_nav and cloud_nav
    assert local_nav.group(0) == cloud_nav.group(0)
    assert 'data-page="rooms"' in cloud_nav.group(0)
    assert 'data-page="growbook"' not in cloud_nav.group(0)


def test_cloud_and_local_status_badges_have_same_structure_and_logic():
    pattern = r'<div class="gc-transport-status"[^>]*>.*?</div>'
    local_status = re.search(pattern, LOCAL, re.S)
    cloud_status = re.search(pattern, CLOUD, re.S)
    assert local_status and cloud_status
    assert local_status.group(0) == cloud_status.group(0)
    for identifier in ('bleLampSignal','bleFanSignal','systemBadge'):
        assert 'id="'+identifier+'"' in cloud_status.group(0)
    for name in ("showBleQuality","setNetworkIndicator"):
        marker = "function "+name+"("
        # Transport selection is allowed to differ, presentation must not.
        start_a = LOCAL_JS.index(marker)
        start_b = CLOUD_JS.index(marker)
        stop_a = LOCAL_JS.index("\n}",start_a)+2
        stop_b = CLOUD_JS.index("\n}",start_b)+2
        assert LOCAL_JS[start_a:stop_a] == CLOUD_JS[start_b:stop_b]
    for js in (LOCAL_JS,CLOUD_JS):
        assert "showBleQuality('lamp',lamp);" in js
        assert "showBleQuality('fan',fan);" in js


def test_dashboard_panel_order_is_identical():
    for html in (LOCAL, CLOUD):
        markers = ('id="liveTiles"', 'id="homePhaseClimate"',
                   'id="homeSoilPanel"', 'id="controlMount"')
        positions = [html.index(m) for m in markers]
        assert positions == sorted(positions), markers
