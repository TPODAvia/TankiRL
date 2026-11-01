from collections import deque
from urllib.parse import urlparse
import time
import base64
import cv2
import numpy as np
from playwright.sync_api import sync_playwright
from tankirl.config import load
from .actions import action_keys, KEYS
from .rewards import Rewards


class BrowserBridge:
    def __init__(self, config=None):
        self.config = load() | (config or {})
        c = self.config
        if urlparse(c["url"]).hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("Only localhost game URLs are permitted")
        self.keys = set()
        self.closed = False
        self.reward = 0.0
        self.metrics = {}
        self.history = deque(maxlen=c["frame_stack"])
        self.pw = sync_playwright().start()
        try:
            self.browser = self.pw.chromium.launch(
                headless=c["headless"],
                args=[
                    "--use-angle=swiftshader",
                    "--enable-unsafe-swiftshader",
                    "--disable-dev-shm-usage",
                    "--disable-background-timer-throttling",
                ],
            )
            self.context = self.browser.new_context(
                viewport={"width": c["width"], "height": c["height"]}
            )

            def route(r):
                if urlparse(r.request.url).hostname in (
                    "127.0.0.1",
                    "localhost",
                    "::1",
                ) or r.request.url.startswith(("data:", "blob:")):
                    r.continue_()
                else:
                    r.abort()

            self.context.route("**/*", route)
            self.page = self.context.new_page()
            self.errors = []
            self.page.on("pageerror", lambda e: self.errors.append(str(e)))
            self.page.goto(
                c["url"] + "/?bridge=1", wait_until="domcontentloaded", timeout=90000
            )
            self.page.wait_for_function("window.tankirl?.ready", timeout=120000)
        except BaseException:
            try:
                self.close()
            except Exception:
                pass
            raise

    def reset(self, seed=None):
        self.emergency_stop()
        c = self.config.copy()
        if seed is not None:
            c["seed"] = int(seed)
        self.telemetry = self.page.evaluate("(c)=>tankirl.reset(c)", c)
        self.page.wait_for_timeout(150)
        self.rewards = Rewards()
        self.rewards.reset(self.telemetry)
        self.reward = 0
        self.history.clear()
        frame = self.get_observation()
        for _ in range(self.config["frame_stack"]):
            self.history.append(frame.copy())
        return frame

    def set_action(self, action):
        wanted = action_keys(action)
        start = time.perf_counter()
        self.keys = set(self.page.evaluate("tankirl.telemetry().keys")) & KEYS
        self.page.locator("#app").focus()
        self.page.evaluate(
            "(ms)=>tankirl.lease(ms)", max(750, 1000 / self.config["decision_hz"] + 250)
        )
        for k in self.keys - wanted:
            self.page.keyboard.up(k)
        for k in wanted - self.keys:
            self.page.keyboard.down(k)
        self.keys = wanted
        self.metrics["action_ms"] = (time.perf_counter() - start) * 1000

    def step(self, action, turret_seconds=None):
        start = time.perf_counter()
        control = self.page.evaluate(
            "({paused:tankirl.telemetry().paused,stopped:tankirl.telemetry().stopped})"
        )
        if control["paused"] or control["stopped"]:
            self.emergency_stop()
            return self.get_observation(), 0.0, control["stopped"], {"paused": True}
        self.set_action(action)
        duration = 1 / self.config["decision_hz"]
        if self.config["stepped"]:
            ticks = max(1, round(duration / 0.033))
            if turret_seconds is not None:
                turning = min(ticks, max(0, round(turret_seconds / 0.033)))
                if turning:
                    self.page.evaluate("(n)=>tankirl.advance(n)", turning)
                self._release_turret()
                if ticks > turning:
                    self.page.evaluate("(n)=>tankirl.advance(n)", ticks - turning)
            else:
                self.page.evaluate("(n)=>tankirl.advance(n)", ticks)
        else:
            if turret_seconds is not None:
                self.page.wait_for_timeout(min(duration, turret_seconds) * 1000)
                self._release_turret()
                self.page.wait_for_timeout(max(0, duration - turret_seconds) * 1000)
            else:
                self.page.wait_for_timeout(duration * 1000)
        self.telemetry = self.page.evaluate("tankirl.telemetry()")
        self.reward, terms = self.rewards.update(self.telemetry, action)
        frame = self.get_observation()
        self.history.append(frame)
        self.metrics["step_ms"] = (time.perf_counter() - start) * 1000
        return (
            frame,
            self.reward,
            self.is_terminated(),
            {
                "reward_terms": terms,
                "telemetry": self.telemetry,
                "timing": self.metrics.copy(),
            },
        )

    def _release_turret(self):
        for k in ("KeyZ", "KeyX"):
            if k in self.keys:
                self.page.keyboard.up(k)
                self.keys.remove(k)

    def get_observation(self):
        start = time.perf_counter()
        if self.config.get("capture_backend") == "canvas":
            data = self.page.evaluate("tankirl.capture()")
            png = base64.b64decode(data.split(",", 1)[1])
        else:
            png = self.page.locator("#app").screenshot(timeout=30000)
        frame = cv2.cvtColor(
            cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR),
            cv2.COLOR_BGR2RGB,
        )
        self.metrics["capture_ms"] = (time.perf_counter() - start) * 1000
        return frame

    def get_reward(self):
        return self.reward

    def is_terminated(self):
        return (
            self.telemetry["deaths"] > 0
            or self.telemetry["phase"] == "over"
            or self.telemetry["stopped"]
        )

    def emergency_stop(self):
        if not hasattr(self, "page") or self.page.is_closed():
            return
        for k in KEYS:
            self.page.keyboard.up(k)
        self.keys.clear()
        self.page.evaluate("window.tankirl?.release()")

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.emergency_stop()
        finally:
            if hasattr(self, "browser"):
                self.browser.close()
            self.pw.stop()
