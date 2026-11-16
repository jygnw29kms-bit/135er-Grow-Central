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
    assert "/cloud-master.html?v=20261116-sidebar-brand-1" in PORTAL
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
    assert "/static/gc-final.css?v=20261116-sidebar-brand-1" in LOCAL
    assert "/static/gc-final.css?v=20261116-sidebar-brand-1" in CLOUD


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


def test_cloud_and_local_push_worker_display_identical_alerts():
    local = (ROOT / "web/gc-worker.js").read_text(encoding="utf-8")
    cloud = (ROOT / "cloud/portal/gc-push-worker.js").read_text(encoding="utf-8")
    marker = "/* Real Web Push:"
    assert marker in local and marker in cloud
    assert local[local.index(marker):] == cloud[cloud.index(marker):]
    assert "self.registration.showNotification(" in local
    # Do not accidentally reinstall the old Cloud offline-cache worker.
    assert "caches.open(" not in cloud
    deploy = (ROOT / "cloud/portal/deploy_cloud_portal.sh").read_text(encoding="utf-8")
    assert 'cp "$repo/cloud/portal/gc-push-worker.js" "$stage/gc-push-worker.js"' in deploy


def test_approved_dashboard_hero_is_top_header_on_both_access_paths():
    for document in (LOCAL, CLOUD):
        assert document.count('class="dashboard-masthead"') == 1
        assert document.count('class="hero hero-master"') == 1
        assert document.index('<main><div class="dashboard-masthead"') < document.index('<header class="topbar">')
        assert document.index('<header class="topbar">') < document.index('<section id="home"')
        assert document.index('<section id="home"') < document.index('<section id="liveTiles"')
        assert 'id="roomPicker"' in document
    local_masthead = re.search(r'<div class="dashboard-masthead"[^>]*>.*?</article></div>', LOCAL, re.S)
    cloud_masthead = re.search(r'<div class="dashboard-masthead"[^>]*>.*?</article></div>', CLOUD, re.S)
    assert local_masthead and cloud_masthead
    assert local_masthead.group(0) == cloud_masthead.group(0)
    marker = "/* Approved Final Master masthead:"
    local_css = (ROOT / "web/gc-final.css").read_text(encoding="utf-8")
    cloud_css = (ROOT / "cloud/portal/gc-final-cloud.css").read_text(encoding="utf-8")
    end = "/* Camera layout:"
    assert marker in local_css and marker in cloud_css
    assert local_css[local_css.index(marker):local_css.index(end)].strip() == cloud_css[cloud_css.index(marker):cloud_css.index(end)].strip()
    assert 'main:has(#home:not(.active))>.dashboard-masthead{display:none}' in local_css


def test_cloud_login_branding_moved_into_hero_not_header():
    entry = (ROOT / "cloud/portal/index.html").read_text(encoding="utf-8")
    assert 'class="gc-public-topline"' in entry
    assert 'class="gc-login-brand"' in entry
    assert entry.index('<header class="gc-public-topline"') < entry.index('<main>')
    assert entry.index('<main>') < entry.index('<div class="gc-login-brand"')
    assert entry.index('<div class="gc-login-brand"') < entry.index('<h1>')
    assert 'class="gc-login-symbol"' in entry
    assert 'src="/static/brand-mark.png"' in entry
    assert 'class="gc-login-wordmark"' in entry
    assert 'class="gc-login-title"' in entry
    assert 'class="gc-login-subtitle"' in entry
    assert '<span>135er-</span><span class="gc-grow">Grow</span><span>Central</span>' in entry
    assert 'mix-blend-mode:screen' in entry
    assert '.gc-login-symbol{height:82px' in entry
    assert 'src="/brand-logo.png"' not in entry
    assert 'body:has(#account:not([hidden])) .gc-login-brand{display:none}' in entry
    # The public login is a separate view, not a substitute Final Master.
    assert 'id="masterMount"' in entry


def test_sidebar_branding_matches_cloud_login_composition():
    local = re.search(r'<a class="brand gc-sidebar-brand"[^>]*>.*?</a>', LOCAL, re.S)
    cloud = re.search(r'<a class="brand gc-sidebar-brand"[^>]*>.*?</a>', CLOUD, re.S)
    assert local and cloud
    # Only the href intentionally differs: local /ui vs authenticated Cloud /.
    assert local.group(0).replace('href="/ui"', 'href="/"') == cloud.group(0)
    for html in (LOCAL, CLOUD):
        assert 'class="gc-sidebar-brand-symbol"' in html
        assert 'class="gc-sidebar-brand-title"' in html
        assert 'class="gc-sidebar-brand-subtitle"' in html
        assert 'src="/static/brand-mark.png"' in local.group(0)
        assert '<span>135er-</span><span class="gc-grow">Grow</span>' in html
        assert 'ENVIRONMENT CONTROL SYSTEM' in html
        assert '<img src="/static/brand-logo.png"' not in html
    login = (ROOT / "cloud/portal/index.html").read_text(encoding="utf-8")
    assert 'gc-login-wordmark' in login
    for path in ("web/gc-final.css", "cloud/portal/gc-final-cloud.css"):
        css = (ROOT / path).read_text(encoding="utf-8")
        assert '/* Final Master sidebar identity:' in css
        assert '.gc-sidebar-brand-symbol img{display:block;width:46px;' in css
        assert 'mix-blend-mode:screen' in css
    marker = "/* Final Master sidebar identity:"
    end = "/* Approved Final Master masthead:"
    local_css = (ROOT / "web/gc-final.css").read_text(encoding="utf-8")
    cloud_css = (ROOT / "cloud/portal/gc-final-cloud.css").read_text(encoding="utf-8")
    assert local_css[local_css.index(marker):local_css.index(end)] == cloud_css[cloud_css.index(marker):cloud_css.index(end)]
