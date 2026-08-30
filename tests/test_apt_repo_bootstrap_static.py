from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "add-135ercloud-apt-repo.sh"


def test_bootstrap_cleans_legacy_growcentral_sources_before_apt_update():
    text = SCRIPT.read_text(encoding="utf-8")
    cleanup = text.index("Alte GrowCentral-APT-Quellen prüfen")
    update = text.index("apt-get update")
    assert cleanup < update
    assert "repo\\.dezender\\.de/apt" in text
    assert "growcentral-archive-keyring" in text
    assert "*.sources" in text
    assert "*.list" in text


def test_bootstrap_backs_up_sources_before_replacing_them():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "BACKUP_ROOT=\"/var/backups/135er-growcentral-apt\"" in text
    assert "backup_file" in text
    assert "cp -a \"$file\"" in text
    assert "chmod -R go-rwx \"$BACKUP_DIR\"" in text


def test_bootstrap_writes_one_canonical_signed_by_source():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'SOURCE="/etc/apt/sources.list.d/135er-growcentral.sources"' in text
    assert 'KEY="/usr/share/keyrings/135er-growcentral-archive-keyring.gpg"' in text
    assert "Signed-By: $KEY" in text


def test_firstboot_ap_keeps_network_path_but_has_no_factory_key():
    setup_ap = (ROOT / "image-builder" / "firstboot" / "setup-ap.sh").read_text(encoding="utf-8")
    assert 'CONNECTION="grow-central-setup-ap"' in setup_ap
    assert "ipv4.method shared" in setup_ap
    assert "wifi-sec.psk" not in setup_ap
    assert "wifi-sec.key-mgmt wpa-psk" not in setup_ap
    assert "passwd --lock GrowCentral" in setup_ap
