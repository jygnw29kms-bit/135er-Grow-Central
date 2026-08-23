from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_current_feature_set_is_integrated():
    entry = read("app/entrypoint.py")
    console = read("web/console.html")
    setup_ap = read("image-builder/firstboot/setup-ap.sh")
    apt_bootstrap = read("scripts/add-135ercloud-apt-repo.sh")

    # Main application integrations.
    assert "camera_router" in entry
    assert "automation_router" in entry
    assert "rooms_router" in entry
    assert "install_rooms(app)" in entry
    assert "install_mdns_alias(app)" in entry

    # Current show/test GUI integrations.
    assert "RÄUME & GROW" in console
    assert "Growtagebuch" in console
    assert "Pflanzen" in console

    # The physically validated Build-85 AP/first-boot path must remain intact.
    assert 'CONNECTION="grow-central-setup-ap"' in setup_ap
    assert "802-11-wireless-security.pmf 1" in setup_ap
    assert "display-setup.sh" in setup_ap

    # Cloud bootstrap must self-heal legacy duplicate Signed-By sources.
    assert 'BACKUP_ROOT="/var/backups/135er-growcentral-apt"' in apt_bootstrap
    assert "clean_list_file" in apt_bootstrap
    assert "clean_sources_file" in apt_bootstrap
    assert "Signed-By: $KEY" in apt_bootstrap
    assert apt_bootstrap.index("Alte GrowCentral-APT-Quellen prüfen") < apt_bootstrap.index("apt-get update")


def test_release_workflow_still_builds_and_publishes_image():
    workflow = read(".github/workflows/build-pi3-image.yml")
    assert "workflow_dispatch:" in workflow
    assert "ubuntu-24.04-arm" in workflow
    assert "Boot and reboot the completed image userspace" in workflow
    assert "Verify published image is still pristine" in workflow
    assert "actions/upload-artifact" in workflow
    assert "gh release create" in workflow
