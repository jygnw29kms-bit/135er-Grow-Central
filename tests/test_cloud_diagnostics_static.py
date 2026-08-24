from pathlib import Path


def test_cloud_diagnostics_contract_present():
    cloud = Path("cloud/app/diagnostics.py").read_text(encoding="utf-8")
    db = Path("cloud/app/db.py").read_text(encoding="utf-8")
    main = Path("cloud/app/main.py").read_text(encoding="utf-8")
    agent = Path("local/cloud_link/agent.py").read_text(encoding="utf-8")

    assert 'latest-pi-diagnostic.json' in cloud
    assert 'latest-pi-diagnostic.tar.gz' in cloud
    assert 'server-diagnostic.json' in cloud
    assert '_MAX_BUNDLE_BYTES' in cloud
    assert 'diagnostic_events' in db
    assert 'app.include_router(diagnostics_router)' in main
    assert '/api/v1/diagnostics/snapshot' in agent
    assert '/api/v1/diagnostics/bundle/' in agent
    assert 'mirror_bundle_if_changed' in agent
    assert 'GC_REMOTE_COMMANDS' in agent


def test_pi_diagnostics_cover_display_network_and_cloud():
    diagnostics = Path("app/diagnostics.py").read_text(encoding="utf-8")
    for unit in (
        '135er-grow-central-cloud-link.service',
        'grow-central-display-kiosk.service',
        'grow-central-setup-ap.service',
        'grow-central-apply-setup.service',
        'grow-central-healthcheck.service',
        'NetworkManager.service',
        'avahi-daemon.service',
    ):
        assert unit in diagnostics
    assert 'addresses' in diagnostics
    assert 'routes' in diagnostics
    assert 'rfkill' in diagnostics
