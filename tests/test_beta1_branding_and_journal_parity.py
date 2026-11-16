"""Keep approved 135er-Grow Central branding while improving the beta UI."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = (ROOT / "web/gc-final.html").read_text(encoding="utf-8")
CLOUD = (ROOT / "cloud/portal/cloud-master.html").read_text(encoding="utf-8")
LOCAL_JS = (ROOT / "web/gc-final.js").read_text(encoding="utf-8")
CLOUD_JS = (ROOT / "cloud/portal/gc-final-cloud.js").read_text(encoding="utf-8")
LOCAL_CSS = (ROOT / "web/gc-final.css").read_text(encoding="utf-8")
CLOUD_CSS = (ROOT / "cloud/portal/gc-final-cloud.css").read_text(encoding="utf-8")


def test_approved_branding_survives_all_beta_gui_changes():
    for html in (LOCAL, CLOUD):
        assert 'gc-sidebar-brand-title' in html
        assert '<span>135er-</span>' in html
        assert '<span class="gc-grow">Grow</span>' in html
        assert '<span class="gc-central">Central</span>' in html
        assert 'ENVIRONMENT CONTROL SYSTEM' in html
        assert 'class="dashboard-masthead"' in html
        assert 'data-page="growbook"' in html
    for css in (LOCAL_CSS, CLOUD_CSS):
        assert '.gc-sidebar-brand' in css


def test_journal_snapshot_is_rendered_equally_on_both_access_paths():
    marker = "function journalSnapshotMarkup(row){"
    for js in (LOCAL_JS, CLOUD_JS):
        assert marker in js
        assert "historical.soil_moisture_percent" in js
        assert "historical.temperature_c" in js
        assert "historical.humidity_percent" in js
        assert "historical.timestamp" in js
    local_snapshot = LOCAL_JS.split(marker, 1)[1].split("function journalEntryDetail(row)", 1)[0]
    cloud_snapshot = CLOUD_JS.split(marker, 1)[1].split("function journalEntryDetail(row)", 1)[0]
    assert local_snapshot == cloud_snapshot
