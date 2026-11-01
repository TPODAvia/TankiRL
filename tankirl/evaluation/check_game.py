"""Real-engine integration verification; fixture success is not autonomous aiming."""

import json
import math
from pathlib import Path
from PIL import Image
from tankirl.game_bridge.browser import BrowserBridge


def distance(a, b):
    return math.dist([a[k] for k in ("x", "y", "z")], [b[k] for k in ("x", "y", "z")])


def run():
    out = Path("logs/verification")
    out.mkdir(parents=True, exist_ok=True)
    b = BrowserBridge({"decision_hz": 2, "stage": 4})
    checks = {}
    try:
        f = b.reset(1)
        s = b.telemetry
        checks["rendered_rgb"] = bool(f.shape == (480, 640, 3) and f.std() > 15)
        checks["enemy_exists"] = len(s["actors"]) == 2
        initial = s["actors"]
        for _ in range(10):
            b.step([2, 1, 1, 0])
        current = b.telemetry["actors"]
        checks["player_moves"] = (
            distance(initial[0]["position"], current[0]["position"]) > 10
        )
        checks["enemy_moves"] = (
            distance(initial[1]["position"], current[1]["position"]) > 10
        )
        b.step([1, 1, 1, 0])
        before = b.telemetry["actors"][0]
        b.step([1, 1, 0, 0])
        after = b.telemetry["actors"][0]
        checks["independent_turret"] = (
            abs(after["turret"] - before["turret"]) > 0.1
            and abs(after["orientation"]["z"] - before["orientation"]["z"]) < 0.15
        )
        b.set_action([2, 2, 2, 1])
        b.emergency_stop()
        state = b.page.evaluate(
            "({keys:tankirl.telemetry().keys,input:tanki.touchInputService.snapshot()})"
        )
        checks["emergency_release"] = (
            not state["keys"]
            and not state["input"]["fire"]
            and state["input"]["stickX"]
            == state["input"]["stickY"]
            == state["input"]["turret"]
            == 0
        )
        b.set_action([2, 1, 1, 1])
        b.page.locator("#pause").click()
        stopped = b.page.evaluate("tankirl.telemetry()")
        checks["pause_releases"] = stopped["paused"] and not stopped["keys"]
        b.page.locator("#pause").click()
        checks["resume"] = not b.page.evaluate("tankirl.telemetry().paused")
        b.set_action([2, 1, 1, 1])
        b.page.wait_for_timeout(900)
        checks["watchdog_releases"] = not b.page.evaluate("tankirl.telemetry().keys")
        b.config["stage"] = 3
        b.config["fixture"] = True
        b.reset(3)
        reward_hit = False
        for _ in range(65):
            f, r, done, info = b.step([1, 1, 1, 1])
            reward_hit = reward_hit or (
                info["reward_terms"]["damage_dealt"] > 0 and r > 0
            )
            if b.telemetry["kills"] > 0:
                break
        checks["actual_shots"] = b.telemetry["shots"] > 0
        checks["actual_damage"] = (
            b.telemetry["damage_dealt"] > 0 and b.telemetry["hits"] > 0
        )
        checks["fixture_kill"] = b.telemetry["kills"] > 0
        checks["damage_reward"] = reward_hit
        Image.fromarray(f).save(out / "fixture.png")
        fixture = b.telemetry.copy()
        b.reset(1)
        checks["reset_clears_events"] = all(
            b.telemetry[k] == 0
            for k in (
                "damage_dealt",
                "damage_received",
                "hits",
                "kills",
                "deaths",
                "shots",
            )
        )
        checks["no_browser_errors"] = not b.errors
        result = {
            "checks": checks,
            "fixture_telemetry": fixture,
            "timing": b.metrics,
            "combat_success_scope": "Aligned stationary curriculum fixture; not learned pursuit or aiming",
            "browser_errors": b.errors,
        }
        (out / "game.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        assert all(checks.values()), checks
        return result
    finally:
        b.close()


if __name__ == "__main__":
    run()
