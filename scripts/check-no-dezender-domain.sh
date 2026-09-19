#!/usr/bin/env bash
set -euo pipefail

LEGACY_DOMAIN='dezender\.de'

if git grep -n -I -i -E "$LEGACY_DOMAIN" -- .; then
  echo
  echo "ERROR: Legacy domain reference detected: dezender.de"
  echo "Use grow-central.de and the canonical subdomains instead."
  exit 1
fi

echo "Domain guard passed: no dezender.de references found in tracked text files."
