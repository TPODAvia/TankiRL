import numpy as np


class ScriptedAgent:
    """Open-loop control smoke test. No telemetry and no claim of combat skill."""

    def __init__(self):
        self.n = 0

    def predict(self, frame):
        self.n += 1
        return np.array(
            [
                2 if self.n % 100 < 65 else 0,
                2 if self.n % 70 > 45 else 1,
                0 if self.n % 60 < 30 else 2,
                1,
            ]
        )
