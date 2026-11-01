import math


class Rewards:
    """Actual damage and kills dominate bounded, once-per-cell exploration."""

    def reset(self, telemetry):
        self.prev = telemetry
        self.seen = set()
        self.budget = 0.2
        self.idle_seconds = 0
        self.best_aim = telemetry.get("aim_alignment") or 0
        self.seen.add(self._cell(telemetry))

    def _cell(self, t):
        p = next(a for a in t["actors"] if a["local"])["position"]
        return (math.floor(p["x"] / 300), math.floor(p["y"] / 300))

    def update(self, t, action):
        p = self.prev
        delta = {
            k: t[k] - p[k]
            for k in ("damage_dealt", "damage_received", "kills", "deaths", "hits")
        }
        r = (
            delta["damage_dealt"] / 100
            - delta["damage_received"] / 100
            + 5 * delta["kills"]
            - 5 * delta["deaths"]
        )
        cell = self._cell(t)
        bonus = 0
        if cell not in self.seen:
            self.seen.add(cell)
            bonus = min(0.005, self.budget)
            self.budget -= bonus
        dt = max(0, (t["time_ms"] - p["time_ms"]) / 1000)
        old = next(a for a in p["actors"] if a["local"])["position"]
        new = next(a for a in t["actors"] if a["local"])["position"]
        moved = math.hypot(new["x"] - old["x"], new["y"] - old["y"])
        self.idle_seconds = self.idle_seconds + dt if moved < 1 else 0
        penalty = 0.002 * dt + (0.01 * dt if self.idle_seconds > 3 else 0)
        aim = t.get("aim_alignment")
        engagement = 0.0
        if aim is not None:
            engagement = 0.2 * max(0.0, aim - self.best_aim)
            self.best_aim = max(self.best_aim, aim)
        r += bonus + engagement - penalty
        self.prev = t
        return float(r), {
            **delta,
            "exploration": bonus,
            "aim_improvement": engagement,
            "inactivity_penalty": penalty,
        }
