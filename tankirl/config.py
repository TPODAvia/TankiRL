from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load(path="configs/game.yaml"):
    with open(ROOT / path) as f:
        return yaml.safe_load(f)
