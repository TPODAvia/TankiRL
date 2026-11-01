# Architecture and upstream audit

## Native primary backend

SkillTanki at the commit in `upstreams.json` is a Vite/TypeScript mobile-first browser game. It uses PlayCanvas 2.23.1 WebGL, a ported tank/weapon physics engine, di-kit services, and a fixed 33 ms simulation loop. Its manifests contain 53 maps, 7 hulls, 9 turrets and 101 paints at this commit. The upstream README's higher headline map counts do not match this manifest.

The documented development route uses a Cloudflare Worker on 8787, local R2 asset upload and a Vite proxy. Another upstream route uses Bun, Redis, MongoDB and MinIO. None of those lobby/signalling services is needed by `BattleSessionService.start` in offline mode. TankiRL uses first-party Vite middleware to serve the same hydrated `assets/` directory at `/assets/`, and a separate entry point imports the unmodified client services. Local `/api` and `/ws` routes reject requests. The Python browser additionally blocks non-local network requests.

Built-in bots use navigation grids, pathfinding, stuck recovery, turret aiming, weapon triggering and difficulty-specific decisions. Deathmatch creates hostile bots; their commands pass through the same TankDriver as human keyboard input. `TouchInputService.attachKeyboard` confirms W/S, A/D, Z/X, C and Space. Z is left (+1 upstream turret axis), X right (-1); the Python MultiDiscrete index convention is left=0, neutral=1, right=2.

`BattleStateService` contains actors, simulation time and phase. `BattleEventService` emits deaths and local respawn countdowns; `ScoreService` wraps kill/death attribution. Actual damage occurs in `Tank.takeDamage`; `CombatService.listenerFor` receives actual weapon shots. Our runtime wrappers preserve those original methods and count changes in actual health, scoped to the shooting actor's `updateWeapon` call. Direct damage is attributed accurately, including multiple bots. Delayed burn/status damage is not credited as player damage shaping. Receiving damage and death still penalize the player. All counters reset per episode. Respawn remains upstream behavior; PPO terminates on the player's first death.

Reset disposes and reconstructs a battle, seeds JavaScript randomness and restores counters. Render effects still use wall time, so the environment is explicitly marked nondeterministic. Stage 2/3 replaces enemy control with idle input and fixes the target physics body in place. An optional test-only fixture also fixes the player and aligns both tanks; it does not inject damage, health loss or shots.

## Visual policy boundary

`BrowserBridge` sends keyboard events only to its dedicated Playwright page. MultiDiscrete `[3,3,3,2]` permits simultaneous drive, hull steering, turret steering and fire, while preventing opposite inputs on an axis. Focus, key-up transitions, blur release, pause, emergency stop and a short browser-side input lease limit stuck controls. No OS-global keyboard injection occurs.

`capture_backend: canvas` captures the actual rendered canvas at frame-end, excluding DOM HUD overlays. The `screenshot` fallback captures the canvas rectangle including overlaid HUD elements. Neither path synthesizes images. Python resizes RGB to 84x84 and stacks four frames as CHW uint8. SB3's CNN normalizes pixels to [0,1]. Both actor and critic are visual. Telemetry appears only in reward/termination/test/diagnostic paths and is not concatenated to policy inputs.

In stepped mode, the integration stops the scheduled battle loop and invokes its existing frame advancement in whole 33 ms ticks. The same collision, weapon, bot and rendering systems run. Rendering remains asynchronous Chromium WebGL, so this is not a massively parallel native physics simulator. Default 10 Hz decisions advance 99 ms per action; achieved wall throughput is measured separately. One browser per environment; SubprocVecEnv supports multiple isolated processes.

PPO uses Stable-Baselines3 CnnPolicy with stacked history, not an LSTM. sb3-contrib is installed but RecurrentPPO is not the baseline. Exploration reward is capped at 0.2 per episode and paid once per visited cell. Damage is scaled by 1/100; kill/death are +/-5. Time/inactivity penalties are small. There is no reward for firing. Stage 2 additionally rewards improvement in the best horizontal target alignment reached, capped at 0.2 per episode; moving away and realigning cannot repeat that reward. This privileged scalar is reward-only. Stages 2–3 randomize the initial turret angle. Curriculum advancement is manual; stage 6 samples map/difficulty at reset.

## Open-P2P inference and Recap replacement

The pinned Open-P2P inference expects a CHW uint8 RGB tensor of 192x192. `Stage3LabelledBCLightning.load_from_checkpoint(..., inference_mode=True)` loads official weights; `KVCacheInferenceState.get_action` maintains autoregressive temporal KV history, samples keyboard and mouse tokens, and decodes them through `UniversalAutoregressiveActionMapping.tensor_to_action`. Configuration must come from the matching `config/policy_model/<size>.yaml`, not the deprecated YAML bundled with the download.

Decoded keyboard names include lowercase `w/a/s/d/z`, arrow names and `Space`; mouse buttons are strings `"0"`, `"1"`, `"2"`. TankiRL allowlists only supported game controls, maps left mouse button 0 to fire, and maps horizontal mouse delta to bounded Z/X pulses with a dead zone. It discards vertical mouse deltas and other keys/buttons. This mapping changes the meaning of model actions and zero-shot competence is not assumed. Upstream KV history records model predictions, including mouse actions; this is not a new Tanki-trained action model.

First-party compatibility adaptations, with no submodule edits:

- The upstream inference module uses a Python-3.13-only typing annotation. It is compiled in memory with postponed annotations for the isolated Python 3.11 runtime.
- Inference imports a Rust dataset queue unconditionally. A fail-fast unavailable queue placeholder allows imports; any attempt to use dataset operations raises. It never provides model predictions, observations or training data.
- Upstream's resize helper calls an undefined `_canonical_resize` at this commit. Actual browser RGB is resized using documented OpenCV INTER_AREA instead.
- No-text mode keeps the 1x768 zero text embedding and skips the unused gated Gemma encoder by setting only the tokenizer name to None. Network architecture and checkpoint tensors remain unchanged. Text-conditioned mode is not exposed.
- After loading on CPU and moving weights to the selected device, the adapter uses upstream `block_mask_to_device` and the action decoder's cache setup method, recreates the action mapping's auxiliary tensors there, then initializes the temporal KV cache on that device.
- Eager inference avoids upstream's automatic 10,000-frame startup benchmark and compile prerequisites. bfloat16/autocast follow upstream inference. No random-weight fallback is used.

Recap itself is Windows Rust/GStreamer code with Win32 capture and keyboard/mouse simulation. Its documented protocol sends RGB24 frames and receives action protobufs via `/tmp/uds.recap`: a four-byte little-endian length prefixes each protobuf. Frames carry width/height/data/frame IDs; responses carry keyboard states and mouse motion/buttons. TankiRL replaces transport/capture/execution with direct Python calls and Playwright. It does not run Recap or its Windows input hooks, and does not claim wire-protocol interoperability testing.

Pretrained P2P, human demonstration cloning into the PPO CNN, and PPO reward-based learning are separate modes. No PPO fine-tuning of Open-P2P is implemented.

## Optional 2014 backend

The original 2014 server is explicitly described by its author as unfinished and not robust. It is Python server/client-schema code with Panda3D-related tooling, MySQL access, Windows launch scripts and a compressed resource archive. Upstream recommends Python >=3.13 because of thread shutdown errors in some older versions. The pinned requirements include mysql-connector-python 9.6.0, Panda3D 1.10.16 and NumPy 2.4.4. Its default network configuration points to 127.0.0.1 and HTTP resources on port 8000.

An isolated Python 3.13.2 environment successfully installed all pinned legacy requirements; MySQL Connector, Panda3D and NumPy imported, and all 425 Python files parsed without syntax errors. Reproduce dependency setup with `scripts/install_legacy_dependencies.sh`. No database was provisioned and no legacy match was run. Resource conversion has Windows-specific path constants; it would need first-party configuration overlays. `python3 -m http.server 8000 --bind 127.0.0.1 --directory <converted-client-resources>` can replace the Windows static HTTP executable only after resources/config.xml are prepared. It does not replace the Windows game client. Wine compatibility has not been demonstrated; Windows EXEs are not native Ubuntu programs. `start_legacy_tanki.sh` performs a read-only readiness report and exits with code 2 rather than pretending to launch a working backend. SkillTanki is independent of this path.

## Licenses and provenance

Exact commits, URLs, file counts and detected license files are recorded in `upstreams.json`.

- Open-P2P source: MIT (upstream LICENSE). Model weights are separately downloaded from the upstream-designated Hugging Face repository; source licensing alone does not establish model/data redistribution rights.
- Recap: GNU GPL v3 text in upstream LICENSE. TankiRL does not link or copy its implementation; distributing it still requires respecting its license.
- SkillTanki: no LICENSE file found in the pinned tracked tree. Game assets are separately LFS-managed and include material derived from Tanki. Public availability does not establish permission to redistribute/relicense them.
- Tanki 2014 server/client resources: no LICENSE file found in the pinned tracked tree. Do not infer a redistribution license from the public repository.

This checkout records dependencies as gitlinks and does not package downloaded models or duplicate game source/assets. Obtain appropriate permissions before publishing a combined game distribution. No blanket license for third-party material is asserted.
