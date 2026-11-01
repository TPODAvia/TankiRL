import argparse
import json
import time
from pathlib import Path
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback
from tankirl.agents.ppo_agent import make_ppo
from tankirl.config import load
from tankirl.envs.tanki_env import TankiEnv


def factory(config):
    return lambda: Monitor(TankiEnv(config))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--timesteps", type=int)
    p.add_argument("--resume")
    p.add_argument("--output", default="checkpoints/ppo")
    p.add_argument("--stage", type=int, choices=range(1, 7), default=4)
    p.add_argument("--n-envs", type=int)
    p.add_argument("--device")
    p.add_argument("--seed", type=int)
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--bc-init")
    p.add_argument("--game-config", default="configs/game.yaml")
    args = p.parse_args()
    torch.set_num_threads(2)
    cfg = load("configs/rl.yaml")
    game = load(args.game_config)
    game["stage"] = args.stage
    if args.stage == 1:
        game["enemies"] = 0
    if args.stage in (2, 3, 4):
        game["enemies"] = 1
    if args.stage == 5:
        game["enemies"] = 3
    if args.stage == 6:
        game["enemies"] = 3
        game["difficulty"] = "normal"
    for key in ("timesteps", "n_envs", "device", "seed"):
        if getattr(args, key) is not None:
            cfg[key] = getattr(args, key)
    if args.smoke:
        cfg.update(timesteps=64, n_steps=32, batch_size=16, n_epochs=1)
        game["episode_seconds"] = 3
    if cfg["n_envs"] < 1:
        raise ValueError("n_envs must be positive")
    factories = [
        factory(game | {"seed": cfg["seed"] + i}) for i in range(cfg["n_envs"])
    ]
    env = (
        DummyVecEnv(factories)
        if len(factories) == 1
        else SubprocVecEnv(factories, start_method="spawn")
    )
    env.seed(cfg["seed"])
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    try:
        model = (
            PPO.load(args.resume, env=env, device=cfg["device"])
            if args.resume
            else make_ppo(env, cfg)
        )
        if args.bc_init:
            model.policy.load_state_dict(
                torch.load(args.bc_init, map_location=cfg["device"], weights_only=True)
            )
        callback = CheckpointCallback(
            save_freq=max(1, cfg["checkpoint_freq"] // cfg["n_envs"]),
            save_path=args.output + "_snapshots",
        )
        model.learn(
            total_timesteps=cfg["timesteps"],
            reset_num_timesteps=not bool(args.resume),
            callback=callback,
        )
        model.save(args.output)
        result = {
            "timesteps": model.num_timesteps,
            "wall_seconds": time.perf_counter() - start,
            "requested_steps": cfg["timesteps"],
            "game": game,
            "rl": cfg,
            "cuda_peak_bytes": torch.cuda.max_memory_allocated()
            if torch.cuda.is_available()
            else 0,
        }
        result["steps_per_second"] = cfg["timesteps"] / result["wall_seconds"]
        Path(args.output + ".json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
    finally:
        env.close()


if __name__ == "__main__":
    main()
