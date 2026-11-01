# Troubleshooting

Check `logs/game.log`, `scripts/check_environment.sh`, `scripts/check_game.sh` and `logs/verification/game.json`. After training finishes, check its log and checkpoint metadata; do not repeatedly poll an active training job.

- **Missing assets:** `git -C third_party/skilltanki lfs pull`. Git pointer text is not an image/model. The asset server is localhost and does not fall back to the official game.
- **Black canvas:** software WebGL uses `--use-angle=swiftshader --enable-unsafe-swiftshader`. Install missing Playwright system libraries if Chromium requests them. A browser UI screenshot alone does not establish that the scene rendered.
- **Slow capture:** default canvas frame-end capture is faster than Playwright's rectangle screenshot. Set `capture_backend: screenshot` for debugging. Decrease viewport size or history/image size for experiments (changing CNN input shape requires new compatible checkpoints). Training defaults to one browser; extra environments can compete for software-rendering CPU time.
- **Changes to browser integration seem ignored:** stop/start the game server. Hot reload and watching are disabled to prevent accidental mid-episode resets. Do not edit/restart it during training.
- **No display:** this session had no DISPLAY or WAYLAND_DISPLAY. Use headless commands, or run visible/manual mode from a real desktop terminal. Do not invent a display value.
- **Input stuck:** P pauses, Emergency stop releases everything, Ctrl+C closes the controller. A browser-side lease releases automated input if its Python controller stalls. Manual input is sampled in the same page, not captured globally.
- **Missing P2P checkpoint:** download 150M first; larger sizes require matching config paths. Downloads use HTTP (`HF_HUB_DISABLE_XET=1`) because Xet stalled on the test host. No token is saved in Git.
- **P2P compatibility:** use the pinned dependency lock and submodule commit. Directly invoking upstream inference with this Python environment bypasses TankiRL's documented inference-only compatibility layer. Full upstream Rust dataset training is not installed.
- **VRAM exhaustion:** use 150M and one controller. The existing driver is left intact. The eager model is slower than a well-tuned compiled setup; GPU availability alone does not guarantee real-time play.
- **No hits/kills:** control smoke tests do not teach fighting. The fixture kill deliberately aligns an immobile target and player. Evaluate pretrained and trained policies separately and read real combat counts.
- **Resume mismatch:** keep CHW resolution/history, action space and capture backend compatible. SB3 checkpoints restore the policy/optimizer, not a browser snapshot. Stage changes are explicit; the map resets.
- **Legacy backend:** optional and not operational here. Python 3.13+, MySQL schema/configuration, converted assets and a tested Windows/Wine client remain required. It must not block the native SkillTanki path.
