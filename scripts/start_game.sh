#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$PWD/.tools/node/bin:$PATH"
mkdir -p logs runtime
if [[ -f runtime/game.pid ]]; then
 pid=$(cat runtime/game.pid)
 if [[ -r /proc/$pid/cmdline ]] && tr '\0' ' ' < "/proc/$pid/cmdline" | grep -q 'integrations/skilltanki/vite.config.mjs'; then
  echo 'Game server already running: http://127.0.0.1:5173'; exit 0
 fi
 rm -f runtime/game.pid
fi
setsid nohup node node_modules/vite/bin/vite.js --config integrations/skilltanki/vite.config.mjs > logs/game.log 2>&1 &
pid=$!
echo "$pid" > runtime/game.pid
for i in {1..50}; do
 if ! kill -0 "$pid" 2>/dev/null; then cat logs/game.log; rm -f runtime/game.pid; exit 1; fi
 if curl -fsS http://127.0.0.1:5173/ >/dev/null 2>&1; then
  echo 'Local game: http://127.0.0.1:5173 (open Chromium, or run scripts/run_scripted.sh --visible)'; exit 0
 fi
 sleep .2
done
cat logs/game.log
exit 1
