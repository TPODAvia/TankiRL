# Run TankiRL on Ubuntu

All commands below run from the repository root:

```bash
cd /home/rover2/TankiRL
```

Use your checkout path if it differs. This project is an experimental local integration. PPO starts untrained; a short smoke test does not teach it to fight.

## 1. Install

```bash
./scripts/install_ubuntu.sh
./scripts/check_environment.sh
```

The installer inspects existing tools, installs isolated dependencies, hydrates SkillTanki assets and downloads the official 150M checkpoint. It never downloads the P2P training dataset. If sudo is requested, enter your password locally. See INSTALL_UBUNTU.md for missing Chromium libraries.

## 2. Verify GPU

```bash
nvidia-smi
.venv/bin/python -c 'import torch; print(torch.__version__, torch.cuda.is_available()); print(torch.ones(1, device="cuda"))'
```

PPO defaults to CPU because this small CNN/browser baseline is often limited by capture, not neural computation. Use `--device cuda` for PPO GPU experiments. P2P defaults to CUDA. CPU inference is experimental and may be slow. No driver replacement is required by these scripts.

## 3. Start the local game

```bash
./scripts/start_game.sh
```

In Chromium open `http://127.0.0.1:5173/`. The page starts a real local map with one enemy bot. A visible browser requires an Ubuntu desktop session with DISPLAY/Wayland configured; headless tests do not.

```bash
./scripts/check_game.sh
```

This checks real RGB rendering, movement, turret motion, firing, enemy movement, damage, fixture destruction, reset and emergency release. Artifacts are in `logs/verification/`.

## 4. Choose a map, hull, turret and bots

A manual browser URL can specify:

```text
http://127.0.0.1:5173/?map=arena_old_summer&enemies=1&hull=Hunter&turret=Smoky&difficulty=easy&seed=1
```

`island_old_summer` is another map. Available IDs are in `third_party/skilltanki/assets/maps.json`, `hulls.json` and `turrets.json`, or the browser console `tankirl.catalog()`. Difficulty: `easy`, `normal`, `hard`; start with one enemy. Keep enemies within 0–11.

For Python modes edit `configs/game.yaml`: map, hull, turret, enemies, difficulty, resolution, image_size, frame_stack, decision_hz, seed and episode_seconds. CLI map/enemy overrides:

```bash
./scripts/run_scripted.sh --visible --map arena_old_summer --enemies 1
```

Stepped training advances upstream physics in 33 ms ticks; decision_hz is rounded to whole physics ticks. It is a simulation rate, not a promise of wall-clock FPS. No arbitrary game-speed multiplier is provided.

## 5. Manual controls

Click the game canvas. W/S move forward/reverse; A/D turn the hull; Z/X turn the turret; C centers the turret; Space fires. The page's Pause AI button controls automation, not the manual simulation. Browser input stays inside the dedicated page.

For a managed visible session:

```bash
.venv/bin/python -m tankirl.ui.run --mode manual --visible --steps 3000
```

## 6. Launch pretrained Open-P2P

```bash
./scripts/download_p2p.sh 150M
./scripts/run_p2p.sh --visible --steps 600
```

The runner creates its own game browser. It loads official weights, sends actual RGB images through the upstream KV-cache inference state, translates permitted keys and horizontal mouse motion, and presses browser keys. Mouse button `0` maps to fire. Other mouse movement/buttons are discarded. `configs/p2p.yaml` controls dead zone, sensitivity and maximum turret pulse duration. Test these settings: the pretrained model was not specifically trained on this turret mapping.

For larger weights, download the size, then change both `checkpoint` and `config` in `configs/p2p.yaml` to matching size paths. Larger models may exceed available VRAM. Text prompting and direct PPO fine-tuning of P2P are not implemented.

## 7. Watch AI drive and shoot

```bash
./scripts/run_scripted.sh --visible --steps 300
.venv/bin/python -m tankirl.ui.run --mode random --visible --steps 300
```

The scripted mode is an open-loop control diagnostic, not an aiming algorithm. P2P, random, scripted and manual modes are separate. For a continuously running simulation add `--realtime`; stepped mode is the default. The latest screenshot is `logs/last_frame.png`; per-mode JSON includes capture, inference, action and step timings. A render-FPS indicator appears in the window.

## 8. Pause, resume and stop

Press P in the game or click **Pause AI**; repeat to resume. **Emergency stop** releases controls and stops the runner. Ctrl+C in its terminal also closes the browser and releases keys. Closing the dedicated browser cannot send actions to another desktop application.

Stop the local web server:

```bash
./scripts/stop_game.sh
```

## 9. Record human demonstrations

```bash
.venv/bin/python -m tankirl.ui.run --mode manual --visible --steps 3000 --record recordings/human_001
```

Use a new directory name for each recording. Format: `metadata.json` (configuration and source mode), numbered RGB PNGs and `transitions.jsonl` (pre-action image, four action indices, reward, termination, wall/simulation timestamps, cumulative combat events). Recording is sampled at approximately 10 Hz; very short key taps between samples may be missed. Recorded keyboard state reflects the interval beginning at that frame. No global keyboard hooks are used.

Optional separate behavior cloning:

```bash
.venv/bin/python -m tankirl.training.behavior_clone recordings/human_001 --epochs 5 --output checkpoints/bc.pt
./scripts/train_rl.sh --bc-init checkpoints/bc.pt --timesteps 100000
```

Use the same image dimensions/history for cloning and PPO. This initializes the PPO CNN policy, not Open-P2P.

## 10. Train PPO

```bash
./scripts/train_rl.sh --smoke --stage 4 --output checkpoints/smoke
./scripts/train_rl.sh --stage 1 --timesteps 100000 --output checkpoints/driving
./scripts/train_rl.sh --stage 4 --timesteps 100000 --output checkpoints/ppo
```

Curriculum stages: 1 exploration without enemies; 2 stationary aiming target; 3 stationary firing target; 4 one moving bot; 5 three bots; 6 multiple maps/difficulties. Stage selection is explicit; there is no automatic mastery detector. Stages 2–3 share a stationary target setup with randomized initial turret angle. Stage 2 additionally rewards only improvements to the best horizontal alignment reached during the episode, capped at 0.2; repeated spinning cannot farm that reward. Stage 3 uses actual damage as its primary signal.

Both actor and critic receive stacked RGB screenshots. PPO normalizes uint8 inputs internally. No enemy positions, health variables or reward diagnostics are policy features. Positive terms reward actual damage/kills and small capped novel-cell exploration; inactivity and damage/death are penalized. Firing alone earns nothing. Direct weapon damage is instrumented; delayed status damage is not credited as player damage shaping.

For parallel browsers: `--n-envs 2` uses subprocesses. This increases CPU/RAM load; default is one environment. Do not assume linear speedup with software WebGL. Headless Chromium uses real WebGL rendering, not mock images.

## 11. TensorBoard

Respect the wait-until-training-finishes workflow. After the training command exits:

```bash
.venv/bin/tensorboard --logdir logs/tensorboard --host 127.0.0.1
```

Open `http://127.0.0.1:6006/`. Completion JSON next to the checkpoint records throughput/configuration. The agent does not poll training logs or checkpoints during training.

## 12. Resume

After the previous run finishes:

```bash
./scripts/train_rl.sh --resume checkpoints/ppo.zip --timesteps 100000 --stage 4 --output checkpoints/ppo_resumed
```

`timesteps` means additional requested transitions. Keep observation shape/history compatible. Optimizer and PPO state are saved in SB3 ZIPs; periodic checkpoints go to `<output>_snapshots/`. Browser physics state is reset, not serialized.

## 13. Select and load the best evaluated checkpoint

```bash
./scripts/eval_rl.sh --checkpoint checkpoints/ppo.zip --episodes 5 --seed 10001 --select-best
./scripts/eval_rl.sh --checkpoint checkpoints/ppo_resumed.zip --episodes 5 --seed 10001 --select-best
./scripts/eval_rl.sh --checkpoint checkpoints/best.zip --visible
```

Selection uses mean evaluation reward. Compare only the same stage/map/difficulty, duration and validation seeds. There is no prepackaged expert or guaranteed winning checkpoint. Training seeds and default evaluation seeds are separated.

## 14. Evaluate against bots

```bash
./scripts/eval_rl.sh --checkpoint checkpoints/ppo.zip --episodes 5 --seconds 60 --seed 10001
```

Evaluation uses deterministic policy actions, and reports hits, damage, kills, deaths and reward in `logs/evaluation.json`. Simulator/rendering trajectories are not bitwise deterministic. Check actual hit/kill counts; successful inference or saved checkpoints do not establish combat skill.

## 15. Troubleshoot

- Black screen: run `scripts/check_game.sh`; inspect `logs/game.log` and browser console. Ensure LFS assets are hydrated. The default SwiftShader backend avoids dependence on a display/GPU renderer.
- Missing model: run `scripts/download_p2p.sh 150M`; verify the checkpoint filename in `configs/p2p.yaml`. The downloader uses HTTP fallback because Xet stalled on the test host.
- GPU OOM: use 150M, close your own unused GPU workloads, or try `device: cpu` in p2p.yaml. Do not kill unrelated workloads automatically.
- Broken keys: click the canvas, resume AI, close menus, and test `scripts/check_game.sh`. Run only one controller per page.
- Visible launch fails: use a desktop terminal with DISPLAY configured; omit `--visible` for headless execution.
- Port busy: stop only TankiRL with `scripts/stop_game.sh`; check port 5173 ownership before restarting.

See TROUBLESHOOTING.md and INSTALL_REPORT.md for verified limits, legacy-backend status and test evidence.
