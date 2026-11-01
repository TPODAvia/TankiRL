#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv venv --python 3.13.2 .venv-legacy --allow-existing
uv pip install --python .venv-legacy/bin/python -r third_party/tanki_2014/requirements.txt
printf 'Python dependencies only. MySQL, resources and a working client are still required.\n'
