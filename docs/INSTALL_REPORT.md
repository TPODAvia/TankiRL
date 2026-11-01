# Installation and verification report

Executed locally on 2026-10-31 in `/home/rover2/TankiRL`. This is a working experimental game/control/inference/training pipeline, **not a trained autonomous combat product**. No official Tanki servers or public matches were used.

## Installed and checked

- Existing Git 2.34.1, Git LFS 3.0.2, uv and FFmpeg retained.
- Node 22.23.4 installed under `.tools/node`; Vite 6.4.5, PlayCanvas 2.23.1 and di-kit 1.1.1 installed in first-party node_modules. npm audit after the Vite patch update: zero known vulnerabilities.
- Python 3.11.12 isolated `.venv`; exact dependencies in requirements.lock. PyTorch 2.9.1+cu128, Gymnasium 1.2.3, Stable-Baselines3 2.9.2, sb3-contrib, TensorBoard, OpenCV, Playwright Chromium, Lightning and P2P inference dependencies installed. CUDA tensor calculation succeeded.
- RTX 4070, 12,282 MiB VRAM, existing driver 580.178.04; roughly 30 GiB RAM. No system Python or driver replacement. No DISPLAY/Wayland display in this session.
- All four pinned submodules initialized recursively. All 1,267 SkillTanki LFS objects hydrated. No upstream tracked files modified; Python cache output is redirected outside upstream code.
- Official Open-P2P 150M checkpoint downloaded (2,198,488,343 bytes). SHA-256 matches Hugging Face metadata: `2a3b43121144ca2d9c2b8aa605e313184c98ac5ef6d2c3b530c2d353d886c5bc`. Full provenance in model_provenance.json. Xet stalled; HTTP fallback succeeded. No authentication or training dataset was needed.
- Installer rerun with only the already-completed checkpoint download skipped: successful. Legacy dependencies additionally installed in `.venv-legacy` with Python 3.13.2.

## Required verification A–P

| Check | Result and evidence |
|---|---|
| A Recursive submodules | Passed; exact versions in upstreams.json |
| B Local assets | Passed; 1,267 LFS files hydrated |
| C Game starts | Passed; localhost:5173, headless Chromium/WebGL |
| D Enemy appears | Passed; rendered enemy and two-actor roster |
| E Movement | Passed; real player's physics position changes under keyboard input |
| F Independent turret | Passed; turret changes while hull heading stays within tolerance |
| G Actual shots | Passed; upstream shot listener fires; fixture produced 11 shots |
| H Actual damage | Passed; fixture dealt 268 HP; moving enemy dealt 144 HP to P2P player |
| I RGB screenshots | Passed; real scene reviewed visually, frame variance checked |
| J Scripted controller | Passed; 16-step run and demonstration recording; no combat-success claim |
| K Official P2P | Passed; real checkpoint and KV inference, translated actions executed; combat trial below |
| L Gymnasium | Passed; browser environment declared nondeterministic rather than claiming identical seeded pixels |
| M PPO smoke training | Passed; 64 transitions, real screenshots, CPU CNN PPO update |
| N Save/reload/resume | Passed; saved ZIP loaded; resume reached 128 total transitions |
| O Evaluation | Passed; two held-out seeds, deterministic policy actions, saved checkpoint |
| P Emergency controls | Passed; key release, pause/resume and browser-side watchdog |

Final automated suite: **11 passed**. Integration TypeScript check passed. Python Ruff undefined/unused checks passed. Detailed machine-readable evidence is in verification.json; generated raw logs and images remain under ignored `logs/`.

Also exercised: stage-2 alignment changes, three enemies (four tanks total), and `island_old_summer` as a second rendered map. Two-environment subprocess PPO completed a 64-transition smoke run. One-epoch behavior cloning completed on 16 recorded **scripted** transitions and saved weights. That tests the recorder/cloning pipeline, not human demonstration quality.

## Gameplay outcome

**A successful enemy hit and kill were demonstrated in the automated fixture:** a real Smoky fires at an aligned, immobile enemy using keyboard input. Actual weapon collision/health/death logic produced 268 damage and one kill. The fixture also fixes the player's physics body for repeatability. No damage or death was injected.

**No autonomous enemy hit or kill was demonstrated by P2P or PPO.** The P2P moving-enemy trial lasted 111 decisions (~11 simulation seconds): it produced non-neutral movement/turret/fire actions and fired one actual shot, but dealt zero damage and was killed after receiving 144 damage. The PPO smoke checkpoint fired two shots per short evaluation episode, with zero hits/kills. It is not a useful trained fighting policy.

## Measured performance

Measurements include browser/runtime overhead and are not promises for other hosts:

- Original rectangle screenshot path: approximately 250 ms capture; initial 64-step PPO smoke about 2.1 steps/s.
- Frame-end canvas path: a focused sample captured in about 91 ms; 64-step PPO smoke **4.67 steps/s** including resets/update.
- Two-environment smoke: **2.58 aggregate steps/s** during concurrent experiments; parallelism did not improve this measurement. One environment remains the default.
- P2P combat trial: mean inference **250 ms**, capture **145 ms**, action dispatch **16 ms**; **2.08 decisions/s** including startup of the game session. Allocated CUDA peak **587,876,864 bytes (~561 MiB)**, excluding Chromium and driver allocations. Model load time is outside that runner's gameplay timer.

Configured 10 Hz means ~99 ms of fixed-step simulation per decision. Wall-clock throughput is lower. GPU inference works, but this eager integration does not achieve 10–20 real-time policy FPS on this test host. Accelerated stepping reuses upstream physics; it does not remove WebGL/capture costs.

## Remaining limits and user actions

- No long training or navigation/combat mastery validation. Pursuit, obstacle avoidance and reliable aiming must be learned and evaluated; working PPO updates are not proof of those skills.
- Visible Chromium, actual human keyboard recording and a desktop preview were not interactively tested because this shell has no display. Run `--visible` from an Ubuntu desktop terminal. Automated Playwright keyboard and recorder paths were tested.
- Text-conditioned P2P, compiled inference, large checkpoints and CPU P2P were not validated. No-text 150M CUDA is the tested path. No direct PPO fine-tuning of P2P exists.
- Stage-2 alignment shaping is reward-only and bounded; its curriculum effectiveness was not established. Delayed burn/status damage lacks positive shooter attribution; use the tested Smoky baseline for initial reward studies.
- Legacy Python dependencies/imports and all 425 source files passed syntax inspection. MySQL provisioning, resource conversion, the Windows client and Wine remain unverified; `start_legacy_tanki.sh` explicitly reports this and exits 2.
- Licensing is unresolved for SkillTanki and legacy assets/source where no license file exists. See ARCHITECTURE.md before redistributing a combined product.

No Hugging Face login or sudo action is currently needed for the tested local primary pipeline. Exact commands are in USER_STEPS.md. Use a graphical desktop only if you want visible/manual gameplay.
