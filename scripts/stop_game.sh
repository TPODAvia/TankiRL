#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -f runtime/game.pid ]]; then
 pid=$(cat runtime/game.pid)
 if [[ -r /proc/$pid/cmdline ]] && tr '\0' ' ' < "/proc/$pid/cmdline" | grep -q 'integrations/skilltanki/vite.config.mjs'; then
  kill "$pid"
  for i in {1..50}; do
   if [[ ! -r /proc/$pid/cmdline ]] || ! tr '\0' ' ' < "/proc/$pid/cmdline" | grep -q 'integrations/skilltanki/vite.config.mjs'; then break; fi
   sleep .1
  done
 fi
 rm -f runtime/game.pid
fi
