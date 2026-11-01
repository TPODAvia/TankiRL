# Ubuntu installation

Ubuntu 22.04/24.04+, x86-64. From the repository root:

```bash
./scripts/install_ubuntu.sh
./scripts/check_environment.sh
```

The installer first inspects available software. Missing Git, Git LFS, curl or FFmpeg require apt/sudo; otherwise system packages are left alone. It uses uv-managed Python 3.11, project-local Node 22.23.4, npm's lockfile, requirements.lock, and Playwright-managed Chromium. No NVIDIA driver changes. The default PyTorch wheel supports CUDA 12.8 and also runs on CPU; development and PPO smoke tests use CPU. The lock includes P2P inference dependencies. A fresh install downloads several GB of wheels plus a roughly 2.2 GB official checkpoint.

If Chromium identifies missing shared libraries:

```bash
sudo .venv/bin/python -m playwright install-deps chromium
```

Initialize the exact submodule commits and hydrate the game data:

```bash
git submodule update --init --recursive
git -C third_party/skilltanki lfs pull
git -C third_party/skilltanki lfs ls-files
```

A `*` before the asset path means a hydrated LFS file; `-` means a pointer remains. No data is downloaded from the Open-P2P training dataset.

Open-P2P weights are downloaded with the unchanged upstream downloader, limited to the chosen size:

```bash
./scripts/download_p2p.sh 150M
# optional: 300M, 600M, 1200M
```

The installer defaults to 150M. To defer only the checkpoint download:

```bash
TANKIRL_SKIP_P2P_DOWNLOAD=1 ./scripts/install_ubuntu.sh
```

No-text inference does not need Gemma authentication: the adapter preserves the upstream zero text embedding shape and skips loading the unused text encoder. Text-conditioned inference is not implemented. Upstream's separate text-conditioned server requires access to google/embeddinggemma-300M and a Hugging Face login; never place a token in the repository.

Full upstream P2P dataset training is a different installation: Python 3.13.2, Rust, Clang, FFmpeg 7 and the native elefant_rust extension. They are not required for this project's RGB inference path, demonstration cloning, or PPO. This project does not claim to reproduce the complete upstream training installation.
