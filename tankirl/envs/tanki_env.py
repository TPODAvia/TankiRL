from collections import deque
import cv2
import gymnasium as gym
import numpy as np
from tankirl.config import load
from tankirl.game_bridge.browser import BrowserBridge
from tankirl.game_bridge.actions import NVECS


class TankiEnv(gym.Env):
    metadata = {"render_modes": ["rgb_array"], "render_fps": 10}

    def __init__(self, config=None, render_mode=None):
        self.config = load() | (config or {})
        self.render_mode = render_mode
        # GPU/browser rendering and effects use wall time: seeded resets are
        # repeatable setup, not bitwise deterministic screenshot trajectories.
        self.spec = gym.envs.registration.EnvSpec(
            "TankiRL-v0",
            entry_point="tankirl.envs.tanki_env:TankiEnv",
            nondeterministic=True,
        )
        self.action_space = gym.spaces.MultiDiscrete(NVECS)
        c = self.config
        n = c["image_size"]
        self.observation_space = gym.spaces.Box(
            0, 255, (3 * c["frame_stack"], n, n), np.uint8
        )
        self.frames = deque(maxlen=c["frame_stack"])
        self.bridge = None
        self.last_frame = None

    def _obs(self, frame, reset=False):
        self.last_frame = frame
        im = cv2.resize(
            frame, (self.config["image_size"],) * 2, interpolation=cv2.INTER_AREA
        ).transpose(2, 0, 1)
        if reset:
            self.frames.clear()
            for _ in range(self.config["frame_stack"]):
                self.frames.append(im.copy())
        else:
            self.frames.append(im)
        return np.concatenate(self.frames, axis=0)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if self.bridge is None:
            self.bridge = BrowserBridge(self.config)
        if self.config.get("stage") == 6:
            self.bridge.config["map"] = str(
                self.np_random.choice(
                    self.config.get("maps", ["arena_old_summer", "island_old_summer"])
                )
            )
            self.bridge.config["difficulty"] = str(
                self.np_random.choice(["easy", "normal", "hard"])
            )
        frame = self.bridge.reset(
            seed=int(seed if seed is not None else self.np_random.integers(0, 2**31))
        )
        return self._obs(frame, True), {}

    def step(self, action):
        if not self.action_space.contains(np.asarray(action)):
            raise ValueError("Invalid action")
        frame, r, done, info = self.bridge.step(action)
        truncated = (
            self.bridge.telemetry["time_ms"] >= self.config["episode_seconds"] * 1000
        )
        # Privileged telemetry stays in info for diagnostics; actor AND critic see only _obs.
        return self._obs(frame), r, done, bool(truncated), info

    def render(self):
        return self.last_frame

    def close(self):
        if self.bridge:
            self.bridge.close()
            self.bridge = None
