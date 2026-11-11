"""delta_core_py testleri için ortak düzen: derlenmiş modülün yolu ve robot nesnesi."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from hypothesis import settings

V2 = Path(__file__).resolve().parents[3]
BUILD = Path(os.environ.get("DELTA_CORE_BUILD", V2 / "build" / "core"))
sys.path.insert(0, str(BUILD))

import delta_core_py as dc  # noqa: E402

# Hypothesis örnek veritabanı tutulmaz: çalışma ağacında .hypothesis/ oluşmasın.
settings.register_profile("delta", database=None)
settings.load_profile("delta")


@pytest.fixture(scope="session")
def robot():
    """Depodaki config/robot.yaml ile kurulmuş kinematik."""
    return dc.DeltaKinematics(dc.load_params(str(V2 / "config" / "robot.yaml")))
