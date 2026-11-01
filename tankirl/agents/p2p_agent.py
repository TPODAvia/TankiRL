"""Linux pixel adapter using upstream Stage3 loader and KVCacheInferenceState."""

import importlib.util
import sys
import types
from pathlib import Path
import cv2
from tankirl.config import ROOT
from tankirl.game_bridge.actions import keys_action


def prepare_upstream():
    sys.pycache_prefix = str(ROOT / "runtime" / "pycache")
    sys.path.insert(0, str(ROOT / "third_party/open_p2p"))
    # Upstream imports the Rust *training dataset queue* unconditionally. It is
    # never called by inference. Fail explicitly if anyone tries to use it.
    # No model, action mapping, attention, or checkpoint code is replaced.
    try:
        from elefant_rust import zmq_queue  # noqa: F401 - native-extension availability check
    except ImportError:
        module = types.ModuleType("elefant_rust")

        class UnavailableQueue:
            def __getattr__(self, name):
                raise RuntimeError(
                    "P2P dataset pipelines require the upstream Rust build; this adapter supports inference only"
                )

        module.zmq_queue = UnavailableQueue()
        sys.modules["elefant_rust"] = module


class MouseTurretAdapter:
    def __init__(self, dead_zone=2.0, sensitivity=0.01, max_seconds=0.1):
        if dead_zone < 0 or sensitivity < 0 or max_seconds <= 0:
            raise ValueError("Invalid mouse adapter settings")
        self.dead_zone = dead_zone
        self.sensitivity = sensitivity
        self.max_seconds = max_seconds

    def translate(self, prediction):
        mapping = {k: "Key" + k.upper() for k in "wasdzxc"}
        mapping.update(
            {
                "UpArrow": "KeyW",
                "DownArrow": "KeyS",
                "LeftArrow": "KeyA",
                "RightArrow": "KeyD",
            }
        )
        keys = {mapping.get(k, k) for k in prediction.keys}
        # Upstream uses lowercase letters and numbered mouse buttons.
        action = keys_action(keys)
        dx = float(prediction.mouse_delta_x)
        duration = 0.0
        if abs(dx) > self.dead_zone:
            action[2] = 2 if dx > 0 else 0
            duration = min(
                self.max_seconds, (abs(dx) - self.dead_zone) * self.sensitivity
            )
        elif action[2] != 1:
            duration = self.max_seconds
        if "0" in prediction.mouse_buttons:
            action[3] = 1
        return action, duration


class P2PAgent:
    def __init__(self, config):
        import torch

        self.config = config
        self.device = config.get("device", "cuda")
        self.turret_seconds = 0
        path = ROOT / config["checkpoint"]
        if not path.is_file():
            raise FileNotFoundError(f"{path}: run scripts/download_p2p.sh")
        prepare_upstream()
        from elefant.config import load_config
        from elefant.policy_model.config import LightningPolicyConfig

        # Python 3.13 upstream annotation uses AsyncGenerator[T]. Postpone
        # annotations in memory for the isolated Python 3.11 integration.
        name = "elefant.policy_model.inference"
        if name not in sys.modules:
            spec = importlib.util.spec_from_file_location(
                name, ROOT / "third_party/open_p2p/elefant/policy_model/inference.py"
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            source = Path(spec.origin).read_text()
            exec(
                compile(
                    "from __future__ import annotations\n" + source, spec.origin, "exec"
                ),
                module.__dict__,
            )
        from elefant.policy_model.inference import KVCacheInferenceState
        from elefant.policy_model.stage3_finetune import Stage3LabelledBCLightning
        from elefant.data.action_mapping import UniversalAutoregressiveActionMapping

        cfg = load_config(str(ROOT / config["config"]), LightningPolicyConfig)
        # No-text mode uses the same zero [1,768] embedding as upstream's
        # get_action(frame, None), without loading gated Gemma unnecessarily.
        cfg.shared.text_tokenizer_config.text_tokenizer_name = None
        if self.device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA unavailable; set device: cpu for experimental CPU inference"
            )
        torch.set_num_threads(2)
        torch.compiler.set_stance("force_eager")
        self.model = Stage3LabelledBCLightning.load_from_checkpoint(
            str(path),
            config=cfg,
            inference_mode=True,
            map_location="cpu",
            weights_only=False,
        )
        self.model = self.model.to(device=self.device, dtype=torch.bfloat16).eval()
        self.model.bc_transformer.block_mask_to_device(self.device)
        self.model.bc_transformer.action_decoder._setup_kv_cache_state()
        with torch.device(self.device):
            self.model.action_mapping = UniversalAutoregressiveActionMapping(
                config=cfg.shared.action_mapping
            )
        self.state = KVCacheInferenceState(
            cfg,
            UniversalAutoregressiveActionMapping(config=cfg.shared.action_mapping),
            self.model,
            max_virtual_steps=12000,
        )
        self.adapter = MouseTurretAdapter(
            config["mouse_dead_zone"],
            config["mouse_sensitivity"],
            config["max_turret_seconds"],
        )
        self.last_prediction = None

    def reset(self):
        self.state.reset()

    def predict(self, frame):
        import torch

        # Upstream resize_image_for_model calls an undefined _canonical_resize
        # at this pinned commit. Resize real RGB with explicit INTER_AREA here.
        resized = cv2.resize(frame, (192, 192), interpolation=cv2.INTER_AREA)
        tensor = torch.from_numpy(resized.transpose(2, 0, 1).copy()).to(self.device)
        with torch.inference_mode(), torch.compiler.set_stance("force_eager"):
            self.last_prediction = self.state.get_action(tensor, None)
        action, self.turret_seconds = self.adapter.translate(self.last_prediction)
        return action

    def vram_bytes(self):
        import torch

        return torch.cuda.max_memory_allocated() if torch.cuda.is_available() else 0
