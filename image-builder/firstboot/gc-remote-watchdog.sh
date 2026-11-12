#!/usr/bin/env bash
# Image-bundled monitoring for authorized Grow Central maintenance connectors.
# This check NEVER downloads software, enrolls an agent, opens firewall ports,
# or executes commands from the internet. An agent must be enrolled separately.
set -Eeuo pipefail
if [[ "$EUID" -ne 0 ]]; then
  echo "root required" >&2; exit 1
fi
log() { logger -t grow-central-remote-watch "$*" || true; }

# Keep key-only SSH service available at boot and after crashes.
if systemctl list-unit-files ssh.service --no-legend 2>/dev/null | grep -q '^ssh.service'; then
  if ! systemctl is-active --quiet ssh.service; then
    log "SSH inactive, starting ssh.service"
    systemctl start ssh.service
  fi
fi

# MeshCentral enrollment is explicitly device-specific and optional.
# Starting is safe ONLY when both agent executable AND enrollment data exist.
if [[ -x /opt/grow-central/mesh-agent/meshagent &&
      -s /opt/grow-central/mesh-agent/meshagent.msh ]]; then
  if ! systemctl is-active --quiet grow-central-mesh-agent.service; then
    log "Authorized MeshCentral agent inactive, starting service"
    systemctl start grow-central-mesh-agent.service
  fi
fi
