"""config/robot.yaml dosyasını okur. CAD betiklerinin tek parametre kaynağı budur."""

from __future__ import annotations

from pathlib import Path

import yaml

V2_ROOT = Path(__file__).resolve().parents[2]
ROBOT_YAML = V2_ROOT / "config" / "robot.yaml"


def load(path: Path = ROBOT_YAML) -> dict:
    """Robot tanımını sözlük olarak döndürür (birimler: mm, derece, g/cm3, g)."""
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)
