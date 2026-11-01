import argparse
from collections import Counter
import json
import time
from pathlib import Path
import numpy as np
from PIL import Image
from tankirl.config import load
from tankirl.game_bridge.browser import BrowserBridge
from tankirl.agents.scripted import ScriptedAgent


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--mode", choices=["random", "scripted", "manual", "p2p"], default="scripted"
    )
    p.add_argument("--visible", action="store_true")
    p.add_argument("--steps", type=int, default=300)
    p.add_argument("--map")
    p.add_argument("--enemies", type=int)
    p.add_argument("--stage", type=int, default=4)
    p.add_argument("--record")
    p.add_argument("--realtime", action="store_true")
    p.add_argument("--seed", type=int, default=1)
    args = p.parse_args()
    cfg = load() | {
        "headless": not args.visible,
        "stage": args.stage,
        "seed": args.seed,
        "stepped": not args.realtime and args.mode != "manual",
    }
    if args.mode == "manual" and not args.visible:
        p.error("manual mode requires --visible")
    if args.map:
        cfg["map"] = args.map
    if args.enemies is not None:
        cfg["enemies"] = args.enemies
    agent = ScriptedAgent()
    if args.mode == "p2p":
        from tankirl.agents.p2p_agent import P2PAgent

        agent = P2PAgent(load("configs/p2p.yaml"))
    rng = np.random.default_rng(args.seed)
    bridge = BrowserBridge(cfg)
    rec = None
    times = []
    start = time.perf_counter()
    count = 0
    action_counts = Counter()
    try:
        frame = bridge.reset(args.seed)
        if args.record:
            from tankirl.recording.recorder import Recorder

            rec = Recorder(args.record, cfg, args.mode)
        for step in range(args.steps):
            status = bridge.page.evaluate("tankirl.telemetry()")
            if status["stopped"]:
                break
            while status["paused"] and not status["stopped"]:
                bridge.emergency_stop()
                bridge.page.wait_for_timeout(100)
                status = bridge.page.evaluate("tankirl.telemetry()")
            if status["stopped"]:
                break
            before = frame
            tick = time.perf_counter()
            if args.mode == "manual":
                from tankirl.game_bridge.actions import keys_action

                action = keys_action(status["keys"])
                bridge.page.wait_for_timeout(100)
                bridge.telemetry = bridge.page.evaluate("tankirl.telemetry()")
                reward, _ = bridge.rewards.update(bridge.telemetry, action)
                frame = bridge.get_observation()
                done = bridge.is_terminated()
            else:
                action = (
                    rng.integers([0, 0, 0, 0], [3, 3, 3, 2])
                    if args.mode == "random"
                    else agent.predict(frame)
                )
                inference_ms = (time.perf_counter() - tick) * 1000
                frame, reward, done, info = bridge.step(
                    action, getattr(agent, "turret_seconds", None)
                )
                times.append({"inference_ms": inference_ms, **bridge.metrics})
            if rec:
                rec.add(before, action, reward, done, bridge.telemetry)
            action_counts[str(list(map(int, action)))] += 1
            count += 1
            if done:
                break
        Path("logs").mkdir(exist_ok=True)
        Image.fromarray(frame).save("logs/last_frame.png")
        result = {
            "mode": args.mode,
            "game_config": cfg,
            "steps": count,
            "wall_seconds": time.perf_counter() - start,
            "telemetry": bridge.telemetry,
            "browser_errors": bridge.errors,
            "timing_mean_ms": {
                k: float(np.mean([x[k] for x in times])) for k in times[0]
            }
            if times
            else {},
        }
        result["steps_per_second"] = count / result["wall_seconds"]
        result["action_counts"] = dict(action_counts)
        if args.mode == "p2p":
            result["vram_bytes"] = agent.vram_bytes()
            result["last_raw_prediction"] = agent.last_prediction._asdict()
        Path(f"logs/{args.mode}.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
    finally:
        if rec:
            rec.close()
        bridge.close()


if __name__ == "__main__":
    main()
