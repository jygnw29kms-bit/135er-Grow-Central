from pathlib import Path

from app import edition


def test_default_is_free(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("GC_EDITION", raising=False)
    monkeypatch.delenv("GC_EDITION_TEST_MODE", raising=False)
    monkeypatch.setattr(edition, "TEST_STATE_FILE", tmp_path / "edition.json")
    payload = edition.edition_payload()
    assert payload["edition"] == "FREE"
    assert payload["local_core_unrestricted"] is True
    assert payload["features"]["local_control"] is True
    assert payload["features"]["remote_access"] is False


def test_legacy_aliases_are_normalized():
    assert edition.normalize_edition("BASIC") == "FREE"
    assert edition.normalize_edition("PLUS") == "LINK"
    assert edition.normalize_edition("INTERNAL") == "PRO"


def test_link_and_pro_only_extend_local_core(monkeypatch):
    monkeypatch.setenv("GC_EDITION", "LINK")
    link = edition.edition_payload()
    assert link["features"]["local_control"] is True
    assert link["features"]["remote_access"] is True
    assert link["features"]["multi_site"] is False
    monkeypatch.setenv("GC_EDITION", "PRO")
    pro = edition.edition_payload()
    assert pro["features"]["local_control"] is True
    assert pro["features"]["multi_site"] is True
