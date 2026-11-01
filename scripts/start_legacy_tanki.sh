#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python integrations/tanki_2014/inspect.py
printf '\nLegacy backend is not launch-ready; see docs/ARCHITECTURE.md. No service was started.\n' >&2
exit 2
