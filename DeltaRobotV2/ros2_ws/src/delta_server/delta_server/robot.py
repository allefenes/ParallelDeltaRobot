"""Robot tanımına erişim: config/robot.yaml yolu, delta_core kinematiği ve birim dönüşümleri.

Birimler: delta_core mm ve derece kullanır; ROS mesajları metre ve radyan kullanır. Dönüşüm
yalnız bu modüldeki yardımcılarla yapılır ki birim karışmasın.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path

import delta_core_py as dc
import yaml

DEFAULT_ROBOT_YAML = "/opt/delta/config/robot.yaml"
JOINT_NAMES = ("motor_1", "motor_2", "motor_3")
MM_PER_M = 1000.0


def robot_yaml_path(param: str = "") -> str:
    """robot.yaml yolunu seçer: parametre > DELTA_ROBOT_YAML ortam değişkeni > imaj varsayılanı."""
    for cand in (param, os.environ.get("DELTA_ROBOT_YAML", ""), DEFAULT_ROBOT_YAML):
        if cand:
            if not Path(cand).is_file():
                raise FileNotFoundError(f"robot.yaml bulunamadı: {cand}")
            return cand
    raise FileNotFoundError("robot.yaml yolu verilmedi")


@dataclass(frozen=True)
class Robot:
    """Kinematik nesnesi + robot.yaml'ın ham içeriği (görev ve eklem istifi ölçüleri için)."""

    kin: dc.DeltaKinematics
    spec: dict
    path: str

    @classmethod
    def load(cls, path: str = "") -> Robot:
        """robot.yaml'ı okur ve delta_core kinematiğini kurar."""
        p = robot_yaml_path(path)
        with open(p, encoding="utf-8") as f:
            spec = yaml.safe_load(f)
        return cls(kin=dc.DeltaKinematics(dc.load_params(p)), spec=spec, path=p)

    @property
    def params(self) -> dc.DeltaParams:
        """Geometri ve limitler (mm, derece)."""
        return self.kin.params

    @property
    def home_mm(self) -> tuple[float, float, float]:
        """Başlangıç (montaj) pozu P, mm: robot.yaml assembly_pose."""
        a = self.spec["assembly_pose"]
        return (float(a["x"]), float(a["y"]), float(a["z"]))

    @property
    def rod_half_spacing_mm(self) -> float:
        """Paralel çubuk çiftinin eksene göre yarı aralığı (mm): joint_stack.rod_spacing / 2."""
        return float(self.spec["joint_stack"]["rod_spacing"]) / 2.0

    @property
    def board_top_mm(self) -> float:
        """Tabla üst yüzünün z'si (mm): zemin (-base_to_floor) + tabla kalınlığı."""
        return -float(self.params.base_to_floor) + float(self.spec["task"]["board_thickness"])


def rad_to_deg(values) -> list[float]:
    """Radyan dizisini dereceye çevirir."""
    return [math.degrees(v) for v in values]


def deg_to_rad(values) -> list[float]:
    """Derece dizisini radyana çevirir."""
    return [math.radians(v) for v in values]


def mm_to_m(values) -> list[float]:
    """mm -> m."""
    return [v / MM_PER_M for v in values]
