import argparse
import json
from pathlib import Path
import numpy as np
import torch
from stable_baselines3 import PPO
from tankirl.config import load
from tankirl.envs.tanki_env import TankiEnv


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", default="checkpoints/ppo.zip")
    p.add_argument("--episodes", type=int, default=3)
    p.add_argument("--seconds", type=float, default=60)
    p.add_argument("--seed", type=int, default=10001)
    p.add_argument("--visible", action="store_true")
    p.add_argument("--output", default="logs/evaluation.json")
    p.add_argument("--select-best", action="store_true")
    args = p.parse_args()
    torch.set_num_threads(2)
    metadata = Path(args.checkpoint).with_suffix(".json")
    saved = json.loads(metadata.read_text()) if metadata.exists() else {}
    cfg = (
        load()
        | saved.get("game", {})
        | {"episode_seconds": args.seconds, "headless": not args.visible}
    )
    env = TankiEnv(cfg)
    model = PPO.load(args.checkpoint, device="cpu")
    runs = []
    try:
        for i in range(args.episodes):
            obs, _ = env.reset(seed=args.seed + i)
            total = 0
            steps = 0
            while True:
                action, _ = model.predict(obs, deterministic=True)
                obs, r, done, truncated, info = env.step(action)
                total += r
                steps += 1
                if done or truncated:
                    break
            stats = {
                k: env.bridge.telemetry[k]
                for k in (
                    "hits",
                    "kills",
                    "deaths",
                    "damage_dealt",
                    "damage_received",
                    "shots",
                )
            }
            runs.append(
                {"seed": args.seed + i, "reward": total, "steps": steps, **stats}
            )
        result = {
            "checkpoint": args.checkpoint,
            "episodes": runs,
            "mean_reward": float(np.mean([x["reward"] for x in runs])),
        }
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        if args.select_best:
            best = Path("checkpoints/best_evaluation.json")
            previous = (
                json.loads(best.read_text())
                if best.exists()
                else {"mean_reward": -float("inf")}
            )
            if result["mean_reward"] > previous["mean_reward"]:
                model.save("checkpoints/best")
                best.write_text(json.dumps(result, indent=2))
                Path("checkpoints/best.json").write_text(json.dumps(saved))
    finally:
        env.close()


if __name__ == "__main__":
    main()
