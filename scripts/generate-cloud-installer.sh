#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "${BASH_SOURCE[0]%/*}/.." && pwd)"
payload="$root/scripts/install-135ercloud-v6.payload.sh"
output="$root/scripts/install-135ercloud-v6.sh"
temporary="${output}.generated"
{
  cat <<'HEADER'
#!/usr/bin/env bash
set -Eeuo pipefail
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
base64 -d <<'__GCLOUD_PAYLOAD__' | gzip -dc > "$TMP"
HEADER
  gzip -9c "$payload" | base64
  cat <<'FOOTER'
__GCLOUD_PAYLOAD__
chmod +x "$TMP"
exec "$TMP" "$@"
FOOTER
} > "$temporary"
mv "$temporary" "$output"
