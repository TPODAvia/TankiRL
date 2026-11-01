#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_HUB_DISABLE_XET=1
exec .venv/bin/python third_party/open_p2p/scripts/download_checkpoints.py "${1:-150M}"
