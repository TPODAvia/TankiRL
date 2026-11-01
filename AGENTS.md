# TankiRL contributor instructions

- Never modify files inside third_party, vendor code, or submodules. Use first-party integration code and explicit runtime adapters.
- Keep all services bound to localhost; never connect to official multiplayer servers.
- Actor and critic inputs must remain rendered RGB images and permitted image/action history. Telemetry is for rewards, termination, diagnostics, and tests only.
- Never substitute mock images or random model weights for real gameplay verification.
- Wait for training process completion before reading logs, metrics, checkpoints, or results. Do not poll training progress.
- Do not create new Markdown files unless explicitly requested.
- Use the isolated .venv and .tools/node installations. Do not change system Python or GPU drivers.
- Run unit tests and affected real-game integration checks. Distinguish fixture hits/kills from autonomous gameplay success.
- Never commit downloaded assets, checkpoints, recordings, credentials, or generated logs.
