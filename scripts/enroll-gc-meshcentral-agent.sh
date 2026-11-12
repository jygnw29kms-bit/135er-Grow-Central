#!/usr/bin/env bash
# Enroll the image-bundled MeshCentral service with owner-provided files.
# The MeshCentral controller/MCP server is external. No secret goes to Git.
set -Eeuo pipefail
umask 077
usage() {
  echo "Usage: sudo bash $0 --agent /local/path/meshagent --config /local/path/meshagent.msh" >&2
  exit 2
}
agent=""
config=""
while (($#)); do
  case "$1" in
    --agent) agent="${2:-}"; shift 2 ;;
    --config) config="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done
[[ -n "$agent" && -n "$config" && "$EUID" -eq 0 ]] || usage
[[ -f "$agent" && -f "$config" && ! -L "$agent" && ! -L "$config" ]] || {
  echo "Regular, non-symlink enrollment files required" >&2; exit 2;
}
[[ "$(stat -c %s "$agent")" -gt 10000 && "$(stat -c %s "$config")" -gt 16 ]] || {
  echo "Agent or enrollment configuration looks incomplete" >&2; exit 2;
}
# Avoid accepting shell scripts or other arbitrary executable formats.
if [[ "$(od -An -N4 -tx1 "$agent" | tr -d ' \n')" != "7f454c46" ]]; then
  echo "Linux ELF MeshCentral agent required" >&2; exit 2
fi
target=/opt/grow-central/mesh-agent
if [[ -e "$target/meshagent" || -e "$target/meshagent.msh" ]]; then
  echo "Existing enrollment found. Refusing to overwrite it." >&2
  exit 3
fi
install -d -o root -g root -m 0700 "$target"
install -o root -g root -m 0700 "$agent" "$target/meshagent"
install -o root -g root -m 0600 "$config" "$target/meshagent.msh"
systemctl daemon-reload
systemctl enable grow-central-mesh-agent.service
systemctl restart grow-central-mesh-agent.service
if ! systemctl is-active --quiet grow-central-mesh-agent.service; then
  echo "MeshCentral agent is not active; inspect journalctl -u grow-central-mesh-agent" >&2
  exit 4
fi
echo "MESH_AGENT_PROCESS_ACTIVE"
echo "Registration on the central MeshCentral server must be verified separately."
