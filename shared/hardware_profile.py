"""Canonical GrowCentral Raspberry Pi hardware support profiles.

One universal image remains the default. Runtime components must consult this
module instead of branching on model strings independently.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

MODEL_PATH = Path("/proc/device-tree/model")


@dataclass(frozen=True)
class HardwareProfile:
    key: str
    support_class: str
    full_support: bool
    recommended: bool
    camera_max_height: int
    camera_max_fps: int
    kiosk_effects: str
    diagnostics_history: str
    worker_profile: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


LEGACY_LITE = HardwareProfile(
    key="legacy-lite",
    support_class="LEGACY_LITE",
    full_support=False,
    recommended=False,
    camera_max_height=720,
    camera_max_fps=15,
    kiosk_effects="reduced",
    diagnostics_history="compact",
    worker_profile="conservative",
)

FULL_STANDARD = HardwareProfile(
    key="full-standard",
    support_class="FULL_SUPPORT",
    full_support=True,
    recommended=True,
    camera_max_height=1080,
    camera_max_fps=30,
    kiosk_effects="full",
    diagnostics_history="standard",
    worker_profile="standard",
)

FULL_PERFORMANCE = HardwareProfile(
    key="full-performance",
    support_class="FULL_SUPPORT",
    full_support=True,
    recommended=True,
    camera_max_height=1080,
    camera_max_fps=30,
    kiosk_effects="full",
    diagnostics_history="extended",
    worker_profile="performance",
)

UNKNOWN = HardwareProfile(
    key="unknown",
    support_class="UNCLASSIFIED",
    full_support=False,
    recommended=False,
    camera_max_height=720,
    camera_max_fps=15,
    kiosk_effects="reduced",
    diagnostics_history="compact",
    worker_profile="conservative",
)


def classify_model(model: str) -> HardwareProfile:
    normalized = " ".join(model.replace("\x00", "").split()).lower()
    if "raspberry pi 3 model b" in normalized:
        return LEGACY_LITE
    if "raspberry pi 4 model b" in normalized or "raspberry pi 400" in normalized:
        return FULL_STANDARD
    if "raspberry pi 5 model b" in normalized:
        return FULL_PERFORMANCE
    if "compute module 4" in normalized:
        return FULL_STANDARD
    if "compute module 5" in normalized:
        return FULL_PERFORMANCE
    return UNKNOWN


def read_model(path: Path = MODEL_PATH) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").replace("\x00", "").strip()
    except OSError:
        return "Unknown Raspberry Pi"


def current_hardware() -> dict[str, object]:
    model = read_model()
    profile = classify_model(model)
    return {"model": model, "profile": profile.as_dict()}
