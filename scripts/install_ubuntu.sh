#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
scripts/check_environment.sh
missing=()
for pair in git:git curl:curl git-lfs:git-lfs ffmpeg:ffmpeg; do
 command -v "${pair%%:*}" >/dev/null || missing+=("${pair##*:}")
done
if ((${#missing[@]})); then sudo apt-get update; sudo apt-get install -y "${missing[@]}"; fi
command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; }
git lfs install --local
git submodule update --init --recursive
git -C third_party/skilltanki lfs pull
mkdir -p .tools
if [[ ! -x .tools/node/bin/node ]] && ! node --version 2>/dev/null | grep -q '^v22\.'; then
 curl -fL https://nodejs.org/dist/v22.23.4/SHASUMS256.txt -o .tools/node-shasums.txt
 curl -fL https://nodejs.org/dist/v22.23.4/node-v22.23.4-linux-x64.tar.xz -o .tools/node-v22.23.4-linux-x64.tar.xz
 (cd .tools; grep ' node-v22.23.4-linux-x64.tar.xz$' node-shasums.txt | sha256sum -c -; tar -xf node-v22.23.4-linux-x64.tar.xz; ln -sfn node-v22.23.4-linux-x64 node; rm node-v22.23.4-linux-x64.tar.xz)
fi
export PATH="$PWD/.tools/node/bin:$PATH"
npm ci
uv venv --python 3.11 .venv --allow-existing
uv pip sync requirements.lock
uv pip install --no-deps -e .
.venv/bin/python -m playwright install chromium
# If Chromium reports missing shared libraries, run:
# sudo .venv/bin/python -m playwright install-deps chromium
if [[ "${TANKIRL_SKIP_P2P_DOWNLOAD:-0}" != 1 ]]; then scripts/download_p2p.sh; fi
scripts/check_environment.sh
