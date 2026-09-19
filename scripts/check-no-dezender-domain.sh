#!/usr/bin/env bash
set -euo pipefail

LEGACY_HOST_PART='dezender'
LEGACY_TLD='.de'
LEGACY_PATTERN="${LEGACY_HOST_PART}\\.de"

# The repository also contains independent standalone projects (for example
# Dyson V11 BMS and Gods Eye) that intentionally still use dezender.de.
# Domain Guard protects Grow Central only and must not flag those projects.
EXCLUDES=(
  ':(exclude)standalone/**'
  ':(exclude).github/workflows/deploy-dyson-v11-bms-apt-sftp.yml'
  ':(exclude).github/workflows/deploy-godseye-web.yml'
)

if git grep -n -I -i -E "$LEGACY_PATTERN" -- . "${EXCLUDES[@]}"; then
  echo
  echo "ERROR: Legacy Grow Central domain reference detected."
  echo "Replace it with grow-central.de or the canonical Grow Central subdomain."
  exit 1
fi

echo "Domain guard passed: no legacy Grow Central domain references found in tracked project files."
