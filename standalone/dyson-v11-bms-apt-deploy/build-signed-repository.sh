#!/usr/bin/env bash
set -euo pipefail

PACKAGE_VERSION="0.3.0-1"
PACKAGE_FILE="dyson-v11-bms_${PACKAGE_VERSION}_all.deb"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${1:?Ausgabeverzeichnis fehlt}"

for command_name in apt-ftparchive dpkg-deb dpkg-scanpackages gpg gpgv gzip sha256sum; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "Benötigtes Programm fehlt: $command_name" >&2
    exit 1
  }
done

if [ -d "$OUTPUT_DIR" ] && find "$OUTPUT_DIR" -mindepth 1 -print -quit | grep -q .; then
  echo "Ausgabeverzeichnis muss leer sein: $OUTPUT_DIR" >&2
  exit 1
fi
install -d -m 0755 "$OUTPUT_DIR"

SIGNING_KEY_FILE="${DYSON_APT_SIGNING_KEY_FILE:-}"
SIGNING_FINGERPRINT="${DYSON_APT_SIGNING_FINGERPRINT:-}"
if [ -n "$SIGNING_KEY_FILE" ]; then
  command -v sq >/dev/null 2>&1 || {
    echo "Benötigtes Programm fehlt: sq" >&2
    exit 1
  }
  test -s "$SIGNING_KEY_FILE"
  sq key extract-cert --force --no-cert-store \
    --output "$OUTPUT_DIR/repo-key.asc" "$SIGNING_KEY_FILE"
  detected_fingerprint="$(gpg --batch --show-keys --with-colons "$OUTPUT_DIR/repo-key.asc" 2>/dev/null \
    | awk -F: '$1 == "fpr" && !fingerprint {fingerprint = $10} END {print fingerprint}')"
  if [ -z "$detected_fingerprint" ]; then
    echo "Signierschlüssel ist keine lesbare OpenPGP-Schlüsseldatei" >&2
    exit 1
  fi
  if [ -n "$SIGNING_FINGERPRINT" ] && [ "$SIGNING_FINGERPRINT" != "$detected_fingerprint" ]; then
    echo "Signierschlüssel-Fingerprint stimmt nicht überein" >&2
    exit 1
  fi
  SIGNING_FINGERPRINT="$detected_fingerprint"
else
  if [ -z "$SIGNING_FINGERPRINT" ]; then
    SIGNING_FINGERPRINT="$(gpg --batch --with-colons --list-secret-keys \
      | awk -F: '$1 == "fpr" && !fingerprint {fingerprint = $10} END {print fingerprint}')"
  fi
  if [ -z "$SIGNING_FINGERPRINT" ]; then
    echo "Kein privater APT-Signierschlüssel gefunden" >&2
    exit 1
  fi
  gpg --batch --list-secret-keys "$SIGNING_FINGERPRINT" >/dev/null
fi

POOL_DIR="$OUTPUT_DIR/apt/pool/main/d/dyson-v11-bms"
DIST_DIR="$OUTPUT_DIR/apt/dists/stable"
ARMHF_DIR="$DIST_DIR/main/binary-armhf"
ARM64_DIR="$DIST_DIR/main/binary-arm64"
install -d -m 0755 "$POOL_DIR" "$ARMHF_DIR" "$ARM64_DIR" "$OUTPUT_DIR/downloads"

"$SCRIPT_DIR/build-current-package.sh" "$POOL_DIR"
cp -f "$POOL_DIR/$PACKAGE_FILE" "$OUTPUT_DIR/downloads/$PACKAGE_FILE"

(
  cd "$OUTPUT_DIR/apt"
  dpkg-scanpackages --multiversion pool /dev/null
) > "$ARMHF_DIR/Packages"
cp -f "$ARMHF_DIR/Packages" "$ARM64_DIR/Packages"
gzip -9n -c "$ARMHF_DIR/Packages" > "$ARMHF_DIR/Packages.gz"
gzip -9n -c "$ARM64_DIR/Packages" > "$ARM64_DIR/Packages.gz"

for index_dir in "$ARMHF_DIR" "$ARM64_DIR"; do
  install -d -m 0755 "$index_dir/by-hash/SHA256"
  for index_file in Packages Packages.gz; do
    index_sha="$(sha256sum "$index_dir/$index_file" | awk '{print $1}')"
    cp -f "$index_dir/$index_file" "$index_dir/by-hash/SHA256/$index_sha"
  done
done

RELEASE_TEMP="$(mktemp)"
(
  cd "$OUTPUT_DIR"
  apt-ftparchive \
    -o APT::FTPArchive::Release::Origin="135er Service Center" \
    -o APT::FTPArchive::Release::Label="Dyson V11 BMS" \
    -o APT::FTPArchive::Release::Suite="stable" \
    -o APT::FTPArchive::Release::Codename="stable" \
    -o APT::FTPArchive::Release::Architectures="armhf arm64" \
    -o APT::FTPArchive::Release::Components="main" \
    -o APT::FTPArchive::Release::Acquire-By-Hash="yes" \
    -o APT::FTPArchive::Release::Description="135er Dyson Service Center" \
    release apt/dists/stable
) > "$RELEASE_TEMP"
install -m 0644 "$RELEASE_TEMP" "$DIST_DIR/Release"
rm -f -- "$RELEASE_TEMP"

if [ -n "$SIGNING_KEY_FILE" ]; then
  sq sign --force --no-cert-store --cleartext-signature \
    --signer-file "$SIGNING_KEY_FILE" \
    --output "$DIST_DIR/InRelease" "$DIST_DIR/Release"
  sq sign --force --no-cert-store --detached \
    --signer-file "$SIGNING_KEY_FILE" \
    --output "$DIST_DIR/Release.gpg" "$DIST_DIR/Release"
else
  gpg --batch --yes --armor --export "$SIGNING_FINGERPRINT" > "$OUTPUT_DIR/repo-key.asc"
  gpg --batch --yes --pinentry-mode loopback --local-user "$SIGNING_FINGERPRINT" \
    --clearsign --output "$DIST_DIR/InRelease" "$DIST_DIR/Release"
  gpg --batch --yes --pinentry-mode loopback --local-user "$SIGNING_FINGERPRINT" \
    --armor --detach-sign --output "$DIST_DIR/Release.gpg" "$DIST_DIR/Release"
fi

PACKAGE_SHA="$(sha256sum "$POOL_DIR/$PACKAGE_FILE" | awk '{print $1}')"
KEY_SHA="$(sha256sum "$OUTPUT_DIR/repo-key.asc" | awk '{print $1}')"

cat > "$OUTPUT_DIR/install.sh" <<'EOF'
#!/bin/bash
set -euo pipefail

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "Bitte als root ausführen: curl -fsSL https://dezender.de/dyson-v11-bms/install.sh | sudo bash" >&2
  exit 1
fi

arch="$(dpkg --print-architecture)"
case "$arch" in
  armhf|arm64) ;;
  *) echo "Nicht unterstützte Architektur: $arch (erwartet armhf oder arm64)" >&2; exit 1 ;;
esac

export DEBIAN_FRONTEND=noninteractive
if ! command -v curl >/dev/null 2>&1; then
  echo "curl fehlt. Bitte zuerst installieren: sudo apt install curl" >&2
  exit 1
fi

key_file="$(mktemp)"
cleanup() { rm -f -- "$key_file"; }
trap cleanup EXIT
curl -fsSL https://dezender.de/dyson-v11-bms/repo-key.asc -o "$key_file"
echo "__KEY_SHA__  ${key_file}" | sha256sum -c -
install -d -m 0755 /usr/share/keyrings
install -m 0644 "$key_file" /usr/share/keyrings/dyson-v11-bms-repo.asc

cat > /etc/apt/sources.list.d/dyson-v11-bms.list <<EOFREPO
deb [arch=${arch} signed-by=/usr/share/keyrings/dyson-v11-bms-repo.asc] https://dezender.de/dyson-v11-bms/apt stable main
EOFREPO

apt-get update
apt-get install -y 'dyson-v11-bms=__PACKAGE_VERSION__'
systemctl is-active dyson-v11-bms.service >/dev/null
echo "Dyson Service Center __PACKAGE_VERSION__ installiert: http://$(hostname -I | awk '{print $1}'):8080/"
EOF

cat > "$OUTPUT_DIR/update.sh" <<'EOF'
#!/bin/bash
set -euo pipefail

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "Bitte als root ausführen: curl -fsSL https://dezender.de/dyson-v11-bms/update.sh | sudo bash" >&2
  exit 1
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "curl fehlt. Bitte zuerst installieren: sudo apt install curl" >&2
  exit 1
fi

arch="$(dpkg --print-architecture)"
case "$arch" in
  armhf|arm64) ;;
  *) echo "Nicht unterstützte Architektur: $arch (erwartet armhf oder arm64)" >&2; exit 1 ;;
esac

# Einmaliger, SHA-256-geprüfter Schlüsselwechsel für Installationen, die noch
# dem bisherigen Repository-Schlüssel vertrauen. Danach übernimmt APT selbst.
key_file="$(mktemp)"
cleanup() { rm -f -- "$key_file"; }
trap cleanup EXIT
curl -fsSL https://dezender.de/dyson-v11-bms/repo-key.asc -o "$key_file"
echo "__KEY_SHA__  ${key_file}" | sha256sum -c -
install -d -m 0755 /usr/share/keyrings
install -m 0644 "$key_file" /usr/share/keyrings/dyson-v11-bms-repo.asc

cat > /etc/apt/sources.list.d/dyson-v11-bms.list <<EOFREPO
deb [arch=${arch} signed-by=/usr/share/keyrings/dyson-v11-bms-repo.asc] https://dezender.de/dyson-v11-bms/apt stable main
EOFREPO

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y dyson-v11-bms
installed="$(dpkg-query -W -f='${Version}' dyson-v11-bms)"
systemctl is-active dyson-v11-bms.service >/dev/null
echo "Dyson Service Center ${installed} ist jetzt APT-verwaltet."
echo "Künftige Updates: sudo apt update && sudo apt upgrade"
EOF

sed -i \
  -e "s/__KEY_SHA__/$KEY_SHA/g" \
  -e "s/__PACKAGE_VERSION__/$PACKAGE_VERSION/g" \
  "$OUTPUT_DIR/install.sh" "$OUTPUT_DIR/update.sh"
chmod 0755 "$OUTPUT_DIR/install.sh" "$OUTPUT_DIR/update.sh"

cat > "$OUTPUT_DIR/README.txt" <<EOF
135er Dyson Service Center APT Repository

Installation:
  curl -fsSL https://dezender.de/dyson-v11-bms/install.sh | sudo bash

Einmalige Migration bestehender 0.2/0.3-Direktinstallationen:
  curl -fsSL https://dezender.de/dyson-v11-bms/update.sh | sudo bash

Danach normale Aktualisierung:
  sudo apt update
  sudo apt upgrade

Version: $PACKAGE_VERSION
Signing fingerprint: $SIGNING_FINGERPRINT
EOF

cat > "$OUTPUT_DIR/repo-info.json" <<EOF
{
  "package": "dyson-v11-bms",
  "version": "$PACKAGE_VERSION",
  "package_sha256": "$PACKAGE_SHA",
  "repository_key_sha256": "$KEY_SHA",
  "signing_fingerprint": "$SIGNING_FINGERPRINT"
}
EOF

bash -n "$OUTPUT_DIR/install.sh" "$OUTPUT_DIR/update.sh"
grep -q '^Package: dyson-v11-bms$' "$ARMHF_DIR/Packages"
grep -q "^Version: $PACKAGE_VERSION$" "$ARMHF_DIR/Packages"
grep -q '^Package: dyson-v11-bms$' "$ARM64_DIR/Packages"
grep -q "^Version: $PACKAGE_VERSION$" "$ARM64_DIR/Packages"
grep -q '^Filename: pool/main/d/dyson-v11-bms/' "$ARMHF_DIR/Packages"
grep -q '^Acquire-By-Hash: yes$' "$DIST_DIR/Release"
VERIFY_KEY="$(mktemp)"
cleanup_verify() {
  case "$VERIFY_KEY" in
    /tmp/*) rm -f -- "$VERIFY_KEY" ;;
    *) echo "Unerwarteter Prüfpfad: $VERIFY_KEY" >&2; exit 1 ;;
  esac
}
trap cleanup_verify EXIT
gpg --batch --yes --dearmor --output "$VERIFY_KEY" "$OUTPUT_DIR/repo-key.asc"
gpgv --keyring "$VERIFY_KEY" "$DIST_DIR/InRelease"
gpgv --keyring "$VERIFY_KEY" "$DIST_DIR/Release.gpg" "$DIST_DIR/Release"
echo "Signiertes APT-Repository $PACKAGE_VERSION erstellt."
