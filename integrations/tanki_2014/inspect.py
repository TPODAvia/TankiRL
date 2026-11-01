"""Read-only legacy readiness check. Never starts official/public matches."""

import json, shutil
from pathlib import Path

root = Path(__file__).resolve().parents[2]
up = root / "third_party/tanki_2014"
cfg = json.loads((up / "configs/server_properties.json").read_text())
print(
    json.dumps(
        {
            "upstream": str(up),
            "python_required": ">=3.13",
            "bind_ip": cfg.get("ip"),
            "wine": shutil.which("wine"),
            "mysql": shutil.which("mysql"),
            "7z": shutil.which("7z"),
            "client_resources_archive": (up / "client_resources.7z").stat().st_size,
            "status": "Not integrated: Windows client, MySQL provisioning and converted resources required. Use SkillTanki.",
        },
        indent=2,
    )
)
