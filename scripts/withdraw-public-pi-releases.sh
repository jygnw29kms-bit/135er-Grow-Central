#!/usr/bin/env bash
# Withdraw publicly downloadable Grow Central Pi image releases while retaining
# historical release metadata and assets for the repository operator.
# Requires authenticated GitHub CLI with "contents:write" on THIS repository.
# DRY RUN by default. Use --apply to make release visibility changes.
set -Eeuo pipefail
umask 077

REPO="jygnw29kms-bit/135er-Grow-Central"
MODE="dry-run"
case "${1:-}" in
  "") ;;
  --apply) MODE="apply" ;;
  *) echo "Usage: bash $0 [--apply]" >&2; exit 2 ;;
esac
if (($# > 1)); then
  echo "Usage: bash $0 [--apply]" >&2; exit 2
fi
for program in gh python3; do
  command -v "$program" >/dev/null || {
    echo "Missing dependency: $program" >&2; exit 2;
  }
done

# Do not print auth tokens or arbitrary API payloads to terminal logs.
if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI is not authenticated. No changes were made." >&2
  exit 3
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
# --paginate traverses ALL pages, not just the 100 newest releases.
gh api --paginate "repos/$REPO/releases?per_page=100" > "$tmp/releases.jsonl"

python3 - "$tmp/releases.jsonl" "$tmp/targets.tsv" <<'PY'
import json
from pathlib import Path
import re
import sys

raw = Path(sys.argv[1]).read_text(encoding="utf-8")
# gh api --paginate outputs separate JSON arrays without a separator.
decoder = json.JSONDecoder()
rows = []
cursor = 0
while cursor < len(raw):
    while cursor < len(raw) and raw[cursor].isspace():
        cursor += 1
    if cursor == len(raw):
        break
    array, offset = decoder.raw_decode(raw, cursor)
    if not isinstance(array, list):
        raise SystemExit("Unexpected release API response: expected JSON arrays")
    rows.extend(array)
    cursor = offset
seen = set()
out = []
for release in rows:
    tag = release.get("tag_name", "")
    release_id = release.get("id")
    if not isinstance(release_id, int) or release_id in seen:
        continue
    seen.add(release_id)
    # Restrict to actual Pi-image release tags AND matching image archives.
    if not re.fullmatch(r"pi-universal-alpha-[0-9.]+-[0-9]+", tag):
        continue
    images = [a["name"] for a in release.get("assets", [])
              if re.fullmatch(r"135er_Grow_Central_RPi3Plus_Universal_.*\.img(?:\.xz)?", a.get("name", ""))]
    if not images or release.get("draft") is True:
        continue
    out.append((release_id, tag, len(images)))
Path(sys.argv[2]).write_text(
    "".join(f"{rid}\t{tag}\t{count}\n" for rid, tag, count in out),
    encoding="utf-8",
)
print(f"RELEASES_INSPECTED={len(rows)}")
print(f"PUBLIC_PI_RELEASES_TO_WITHDRAW={len(out)}")
PY

count=0
while IFS=$'\t' read -r release_id tag image_count; do
  [[ "$release_id" =~ ^[0-9]+$ ]] || {
    echo "Unexpected release ID" >&2; exit 4;
  }
  [[ "$tag" =~ ^pi-universal-alpha-[0-9.]+-[0-9]+$ ]] || {
    echo "Unexpected release tag" >&2; exit 4;
  }
  echo "$MODE release=$tag images=$image_count"
  if [[ "$MODE" == "apply" ]]; then
    # PATCH changes release visibility without destroying old image data.
    gh api --method PATCH "repos/$REPO/releases/$release_id" -F draft=true >/dev/null
    visibility="$(gh api "repos/$REPO/releases/$release_id" --jq .draft)"
    if [[ "$visibility" != "true" ]]; then
      echo "FAILED to verify draft state for $tag" >&2
      exit 5
    fi
    echo "VERIFIED_PRIVATE_DRAFT=$tag"
  fi
  count=$((count + 1))
done < "$tmp/targets.tsv"
echo "PROCESSED=$count"
if [[ "$MODE" == "dry-run" ]]; then
  echo "DRY_RUN_ONLY: no GitHub release visibility changes."
else
  echo "ALL_TARGETED_PI_RELEASES_CONVERTED_TO_DRAFT"
fi
