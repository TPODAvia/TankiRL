import json
import time
from pathlib import Path
import numpy as np
from PIL import Image


class Recorder:
    """One PNG per pre-action RGB observation, JSONL transitions, metadata JSON."""

    def __init__(self, path, config, mode="manual"):
        self.root = Path(path)
        self.root.mkdir(parents=True, exist_ok=False)
        (self.root / "metadata.json").write_text(
            json.dumps(
                {
                    "format": "tankirl-demo-v1",
                    "config": config,
                    "mode": mode,
                    "action_order": ["throttle", "hull", "turret", "fire"],
                    "observation": "pre-action RGB",
                    "created_unix": time.time(),
                },
                indent=2,
            )
        )
        self.file = (self.root / "transitions.jsonl").open("w")
        self.n = 0
        self.start = time.monotonic()

    def add(self, frame, action, reward, done, telemetry):
        name = f"{self.n:07d}.png"
        Image.fromarray(frame).save(self.root / name)
        self.file.write(
            json.dumps(
                {
                    "frame": name,
                    "action": np.asarray(action).tolist(),
                    "reward": float(reward),
                    "terminated": bool(done),
                    "elapsed_seconds": time.monotonic() - self.start,
                    "sim_time_ms": telemetry["time_ms"],
                    "events": {
                        k: telemetry[k]
                        for k in ("damage_dealt", "damage_received", "kills", "deaths")
                    },
                }
            )
            + "\n"
        )
        self.file.flush()
        self.n += 1

    def close(self):
        self.file.close()
