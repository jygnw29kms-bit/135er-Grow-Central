#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="${ROOT_DIR}/.work"
PI_GEN_DIR="${WORK_DIR}/pi-gen"
DEPLOY_DIR="${ROOT_DIR}/deploy"
# Bookworm branch snapshot. Pinning prevents the default pi-gen release and
# dependency model from changing underneath this Raspberry Pi 3 image build.
PI_GEN_COMMIT="4be6bbd0933c900517cb309d4f4f44267d2c2cac"

mkdir -p "$WORK_DIR" "$DEPLOY_DIR"
if [[ ! -d "$PI_GEN_DIR/.git" ]]; then
  mkdir -p "$PI_GEN_DIR"
  git -C "$PI_GEN_DIR" init
  git -C "$PI_GEN_DIR" remote add origin https://github.com/RPi-Distro/pi-gen.git
fi
git -C "$PI_GEN_DIR" fetch --depth 1 origin "$PI_GEN_COMMIT"
git -C "$PI_GEN_DIR" checkout --detach --force FETCH_HEAD

cp "$ROOT_DIR/config" "$PI_GEN_DIR/config"
rm -rf "$PI_GEN_DIR/stage-dyson"
cp -a "$ROOT_DIR/stage-dyson" "$PI_GEN_DIR/stage-dyson"
pushd "$PI_GEN_DIR" >/dev/null
sudo -E ./build.sh
popd >/dev/null
find "$PI_GEN_DIR/deploy" -maxdepth 1 -type f \( -name '*.img.xz' -o -name '*.zip' \) -exec cp -f {} "$DEPLOY_DIR/" \;
ls -lh "$DEPLOY_DIR"
