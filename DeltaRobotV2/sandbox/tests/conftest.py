"""Ortak test ayarı: koşucu paketi `sandbox/runner/` altından içe aktarılır."""

import sys
from pathlib import Path

SANDBOX_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SANDBOX_DIR / "runner"))
