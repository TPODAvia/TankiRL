#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
export PATH="$PWD/.tools/node/bin:$PATH"
for tool in git uv node npm ffmpeg; do command -v "$tool" || true; done
git lfs version || true
node --version || true
python3 --version
free -h
df -h .
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv || true
printf 'DISPLAY=%s WAYLAND_DISPLAY=%s\n' "${DISPLAY:-unset}" "${WAYLAND_DISPLAY:-unset}"
if [[ -x .venv/bin/python ]]; then
 .venv/bin/python - <<'PY'
import torch, gymnasium, stable_baselines3
print('torch',torch.__version__,'CUDA',torch.cuda.is_available(),'runtime',torch.version.cuda)
print('gymnasium',gymnasium.__version__,'SB3',stable_baselines3.__version__)
if torch.cuda.is_available():
 x=torch.ones(16,device='cuda');print('GPU tensor test:',x.sum().item())
PY
fi
