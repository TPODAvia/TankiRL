# TankiRL

Ubuntu-native local SkillTanki experiments: real WebGL RGB observations, browser-scoped keyboard controls, an image-only PPO actor/critic, and a separate pretrained Open-P2P adapter. No official Tanki servers are used.

Start with [USER_STEPS](docs/USER_STEPS.md), [installation](docs/INSTALL_UBUNTU.md), and the candid [verification report](docs/INSTALL_REPORT.md). This is an experimental integration, not a trained combat agent. A stationary, aligned target kill is an integration test, not evidence of autonomous pursuit or aiming.

```bash
./scripts/install_ubuntu.sh
./scripts/start_game.sh
./scripts/run_scripted.sh --visible
./scripts/run_p2p.sh --visible
./scripts/train_rl.sh --timesteps 100000
./scripts/eval_rl.sh --checkpoint checkpoints/ppo.zip
```

The four upstream projects are pinned submodules. First-party Vite/Python integration imports their code without editing their files. Game data and model checkpoints remain ignored local downloads. See [architecture and licenses](docs/ARCHITECTURE.md) before redistribution.
