from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Legacy *brand* forms only. Generic descriptive wording such as
# "grow control" or "Grow-Controller" is not the former product name and
# must not make the repository test fail.
LEGACY = re.compile(
    r"(?:135er[\s_-]*)?growcontrol\b|135er[\s_-]+grow[\s_-]+control\b",
    re.IGNORECASE,
)
TEXT_SUFFIXES = {
    "", ".cfg", ".conf", ".css", ".env", ".example", ".html", ".ini", ".js",
    ".json", ".md", ".py", ".service", ".sh", ".socket", ".sql", ".svg",
    ".timer", ".toml", ".txt", ".yaml", ".yml",
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    )
    return [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def test_legacy_branding_is_absent_from_current_tree():
    offenders: list[str] = []
    for path in tracked_files():
        relative = path.relative_to(ROOT).as_posix()
        if LEGACY.search(relative):
            offenders.append(f"filename:{relative}")
            continue
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if LEGACY.search(text):
            offenders.append(f"content:{relative}")
    assert not offenders, "Legacy product naming found: " + ", ".join(offenders)


def test_github_repository_uses_canonical_name_when_running_in_actions():
    repository = os.getenv("GITHUB_REPOSITORY", "")
    if repository:
        assert repository.endswith("/135er-Grow-Central")
