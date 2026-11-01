"""Supervised initialization of the separate PPO CNN, never P2P fine-tuning."""

import argparse
import json
from pathlib import Path
import cv2
import numpy as np
import torch
from tankirl.config import load
from tankirl.envs.tanki_env import TankiEnv
from tankirl.agents.ppo_agent import make_ppo


def main():
    p = argparse.ArgumentParser()
    p.add_argument("dataset")
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--output", default="checkpoints/bc.pt")
    a = p.parse_args()
    torch.set_num_threads(2)
    root = Path(a.dataset)
    meta = json.loads((root / "metadata.json").read_text())
    cfg = load() | meta["config"]
    env = TankiEnv(cfg)
    model = make_ppo(env, load("configs/rl.yaml"))
    rows = [
        json.loads(x) for x in (root / "transitions.jsonl").read_text().splitlines()
    ]
    if not rows:
        raise ValueError("Empty demonstration")
    samples = []
    history = []
    for row in rows:
        frame = cv2.cvtColor(cv2.imread(str(root / row["frame"])), cv2.COLOR_BGR2RGB)
        im = cv2.resize(frame, (cfg["image_size"],) * 2).transpose(2, 0, 1)
        if not history:
            history = [im.copy() for _ in range(cfg["frame_stack"])]
        else:
            history = (history + [im])[-cfg["frame_stack"] :]
        samples.append((np.concatenate(history), row["action"]))
        if row["terminated"]:
            history = []
    opt = torch.optim.Adam(model.policy.parameters(), lr=1e-4)
    model.policy.set_training_mode(True)
    for epoch in range(a.epochs):
        losses = []
        for start in range(0, len(samples), 32):
            batch = samples[start : start + 32]
            obs = torch.as_tensor(np.stack([x[0] for x in batch]), device=model.device)
            actions = torch.tensor([x[1] for x in batch], device=model.device)
            loss = -model.policy.get_distribution(obs).log_prob(actions).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
            losses.append(loss.item())
        print(
            json.dumps(
                {"epoch": epoch, "negative_log_likelihood": float(np.mean(losses))}
            )
        )
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.policy.state_dict(), a.output)
    env.close()


if __name__ == "__main__":
    main()
