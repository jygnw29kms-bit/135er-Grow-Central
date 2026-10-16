#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ALLOWED_PREFIXES = ("app/", "local/cloud_link/", "web/", "shared/")
ALLOWED_EXTENSIONS = {
    ".py", ".json", ".html", ".js", ".css", ".svg", ".png", ".webp",
    ".jpg", ".jpeg", ".ico", ".txt", ".md", ".toml", ".yaml", ".yml",
}
MAX_FILES = 500
MAX_BYTES = 50 * 1024 * 1024


def git(repo: Path, *args: str) -> str:
    run = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return run.stdout.strip()


def safe_path(value: str) -> bool:
    if "\\" in value or value.startswith("/") or not value.startswith(ALLOWED_PREFIXES):
        return False
    path = PurePosixPath(value)
    if not path.parts or any(part in {"", ".", ".."} or part.startswith(".") for part in path.parts):
        return False
    if path.name == "requirements.txt":
        return False
    return path.suffix.lower() in ALLOWED_EXTENSIONS


def changed_files(repo: Path, base: str, head: str) -> list[str]:
    raw = git(repo, "diff", "--name-status", "--no-renames", f"{base}..{head}", "--", *[p.rstrip("/") for p in ALLOWED_PREFIXES])
    rows: list[str] = []
    deleted: list[str] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        status, rel = line.split("\t", 1)
        if status == "D":
            deleted.append(rel)
            continue
        if status not in {"A", "M"}:
            raise SystemExit(f"unsupported git change {status}: {rel}")
        if not safe_path(rel):
            raise SystemExit(f"unsafe or unsupported hot-update path: {rel}")
        rows.append(rel)
    if deleted:
        raise SystemExit("hot-update contains deletions; use a full image/release: " + ", ".join(deleted))
    return sorted(set(rows))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def package(repo: Path, base: str, output: Path, head: str = "HEAD") -> tuple[Path, list[str]]:
    repo = repo.resolve()
    commit = git(repo, "rev-parse", head)
    base_commit = git(repo, "rev-parse", base)
    files = changed_files(repo, base_commit, commit)
    if not files:
        raise SystemExit("no hot-update compatible runtime changes found")
    if len(files) > MAX_FILES:
        raise SystemExit(f"too many files: {len(files)} > {MAX_FILES}")

    total = sum((repo / rel).stat().st_size for rel in files)
    if total > MAX_BYTES:
        raise SystemExit(f"payload too large: {total} > {MAX_BYTES}")

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="growcentral-update-") as tmp:
        root = Path(tmp)
        payload = root / "payload"
        sums: list[str] = []
        for rel in files:
            source = repo / rel
            if source.is_symlink() or not source.is_file():
                raise SystemExit(f"payload source must be a regular file: {rel}")
            target = payload / Path(*PurePosixPath(rel).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            sums.append(f"{sha256(target)}  {rel}")

        (root / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="ascii", newline="\n")
        (root / "MANIFEST").write_text(
            "\n".join(
                (
                    f"commit={commit}",
                    f"base={base_commit}",
                    f"created_utc={datetime.now(timezone.utc).isoformat()}",
                    f"file_count={len(files)}",
                )
            ) + "\n",
            encoding="ascii",
            newline="\n",
        )
        with tarfile.open(output, "w:gz") as archive:
            archive.add(root / "MANIFEST", arcname="MANIFEST")
            archive.add(root / "SHA256SUMS", arcname="SHA256SUMS")
            archive.add(payload, arcname="payload")
    return output, files


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a validated Grow-Central test-Pi hot-update payload.")
    parser.add_argument("--base", required=True, help="currently live Git SHA")
    parser.add_argument("--head", default="HEAD", help="target Git ref/SHA (default: HEAD)")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output, files = package(args.repo, args.base, args.output, args.head)
    print(f"PACKAGED={output}")
    print(f"FILES={len(files)}")
    for rel in files:
        print(rel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
