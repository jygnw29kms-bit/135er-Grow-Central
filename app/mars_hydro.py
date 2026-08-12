"""Mars Hydro hardware metadata for 135er-Grow Central alpha-0.7.4.

This module deliberately contains no guessed iConnect write protocol. It provides
one authoritative hardware-family model that can be shared by discovery, API,
GUI and future adapters while the real communication path is validated.
"""
from __future__ import annotations

from typing import Any

ECOSYSTEM_ID = "mars_hydro_iconnect"
ECOSYSTEM_LABEL = "Mars Hydro / iConnect"

AUTHORITATIVE_HARDWARE: tuple[dict[str, Any], ...] = (
    {
        "id": "mars-hydro-fc3000-2024",
        "vendor": "Mars Hydro",
        "model": "FC3000",
        "generation": "2024",
        "interfaces": ["USB", "iConnect"],
        "role": "lighting",
        "integration": "iconnect_target",
        "validated": False,
    },
    {
        "id": "mars-hydro-ifresh-df100",
        "vendor": "Mars Hydro",
        "model": "DF100 / iFresh",
        "generation": "iFresh",
        "interfaces": ["iConnect"],
        "role": "ventilation",
        "integration": "iconnect_target",
        "validated": False,
    },
)

BLE_DIAGNOSTIC_PROFILE: dict[str, Any] = {
    "id": "mars-hydro-df100m-ble-diagnostics",
    "vendor": "Mars Hydro",
    "model": "DF100M / MZ_MZF002",
    "observed_firmware": "V1.8",
    "role": "ventilation_diagnostics",
    "integration": "experimental_ble_diagnostics_fallback",
    "validated": False,
    "writes_enabled_by_default": False,
}


def public_hardware_profile() -> dict[str, Any]:
    """Return non-secret hardware metadata safe for the local API/UI."""
    return {
        "ecosystem_id": ECOSYSTEM_ID,
        "ecosystem_label": ECOSYSTEM_LABEL,
        "authoritative_hardware": [dict(item) for item in AUTHORITATIVE_HARDWARE],
        "ble_diagnostics": dict(BLE_DIAGNOSTIC_PROFILE),
        "local_authority": "Raspberry Pi",
        "esp32_target": False,
    }


def is_mars_hydro_ble_candidate(name: str, name_hint: str = "MZ_MZF002") -> bool:
    """Conservatively classify BLE advertisements used by the diagnostics path."""
    lowered = (name or "").lower()
    return any(token in lowered for token in (name_hint.lower(), "mzf", "mars", "df100m", "ifresh"))
