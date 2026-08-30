#!/usr/bin/env bash
# DEPRECATED BUILD-COMPATIBILITY SHIM.
# Grow Central is permanently headless. This file exists only because the
# current image-builder verification still checks the historical path before
# the final headless prune. It must never start a graphical session.
set -u
printf '[grow-central] local kiosk removed; use web/mobile clients.\n'
exit 0
