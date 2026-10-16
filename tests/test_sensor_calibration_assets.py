from pathlib import Path
import hashlib

EXPECTED = {
    "01-air-dry.png": "6843ac0dac507614692ad0e276e5995c66327b67045df599a8b4fae4009d6c45",
    "02-water-saturated.png": "5efce7b7bf9f482c9174c170aa8a3dd2e8906c99daa26df652c174a7286baa4c",
    "03-fresh-substrate-cc.png": "c16c6e9eeebb50f89f0feeea438fbf32a1234926d564337deac6d780cf240f5f",
}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def test_only_approved_calibration_master_images_are_bundled():
    for root in (Path("docs/assets/sensor-calibration"), Path("web/assets/sensor-calibration")):
        assert {p.name for p in root.glob("*.png")} == set(EXPECTED)
        assert {name: sha(root / name) for name in EXPECTED} == EXPECTED

def test_usb_onboarding_uses_all_three_approved_images_and_references():
    source = Path("web/usb_onboarding.js").read_text(encoding="utf-8")
    for name in EXPECTED:
        assert f"/static/assets/sensor-calibration/{name}" in source
    for reference in ("AIR_DRY", "WATER_SATURATED", "FRESH_SUBSTRATE_CC"):
        assert reference in source
    assert "box.append(air, airButton, wet, wetButton)" not in source
