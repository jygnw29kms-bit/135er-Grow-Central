#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="${ROOT_DIR}/.work"
PI_GEN_DIR="${WORK_DIR}/pi-gen"
DEPLOY_DIR="${ROOT_DIR}/deploy"
mkdir -p "$WORK_DIR" "$DEPLOY_DIR"
if [[ ! -d "$PI_GEN_DIR/.git" ]]; then
  git clone --depth 1 https://github.com/RPi-Distro/pi-gen.git "$PI_GEN_DIR"
else
  git -C "$PI_GEN_DIR" pull --ff-only
fi
cp "$ROOT_DIR/config" "$PI_GEN_DIR/config"
rm -rf "$PI_GEN_DIR/stage-dyson"
cp -a "$ROOT_DIR/stage-dyson" "$PI_GEN_DIR/stage-dyson"
pushd "$PI_GEN_DIR" >/dev/null
sudo -E ./build.sh
popd >/dev/null
find "$PI_GEN_DIR/deploy" -maxdepth 1 -type f \( -name '*.img.xz' -o -name '*.zip' \) -exec cp -f {} "$DEPLOY_DIR/" \;
ls -lh "$DEPLOY_DIR"
