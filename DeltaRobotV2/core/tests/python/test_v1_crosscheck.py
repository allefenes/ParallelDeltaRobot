"""V2 çekirdeğinin V1 kinematiğiyle sayısal çapraz doğrulaması.

Referans değerler tools/v1_vectors.py ile V1 kodundan üretildi ve V2 çerçevesine dönüştürüldü
(core/tests/data/v1_vectors.json). Geometri V1 ile aynıdır (64 / 201 / R65 / R35).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

DATA = json.loads((Path(__file__).resolve().parents[1] / "data" / "v1_vectors.json").read_text())


def test_enough_reference_cases():
    assert len(DATA["ik"]) > 300
    assert len(DATA["fk"]) > 100


@pytest.mark.parametrize("case", DATA["ik"], ids=lambda c: str(c["P"]))
def test_inverse_matches_v1(robot, case):
    th = robot.inverse(case["P"])
    assert th is not None
    for a, b in zip(th, case["theta"], strict=True):
        assert abs(a - b) < 1e-6


@pytest.mark.parametrize("case", DATA["fk"], ids=lambda c: str(c["theta"]))
def test_forward_matches_v1(robot, case):
    p = robot.forward(case["theta"])
    assert p is not None
    assert math.dist(p, case["P"]) < 1e-6
