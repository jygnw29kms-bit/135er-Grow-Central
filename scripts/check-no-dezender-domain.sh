#!/usr/bin/env bash
set -euo pipefail

LEGACY_HOST_PART='dezender'
LEGACY_TLD='.de'
LEGACY_DOMAIN="${LEGACY_HOST_PART}${LEGACY_TLD}"
LEGACY_PATTERN="${LEGACY_HOST_PART}\.de"

if git grep -n -I -i -E "$LEGACY_PATTERN" -- .; then
  echo
  echo "ERROR: Legacy project domain reference detected."
  echo "Replace it with grow-central.de or the canonical Grow Central subdomain."
  exit 1
fi

echo "Domain guard passed: no legacy project-domain references found in tracked text files."
