"""V1 kinematiğinden çapraz doğrulama vektörleri üretir (bir kez, ana makinede çalıştırılır).

V1 koduna yalnız referans olarak dokunulur: KilavuzDeltaRobotics/modules/deltaRobot.py kendi
yerinden yüklenip çalıştırılır, V2'ye kod kopyalanmaz. Çıktı V2 çerçevesine dönüştürülür:
    V2 (x, y, z) = V1 (x, -y, -z);  V2 kol sırası [1, 2, 3] = V1 [1, 3, 2]
Çalıştırma (repo kökünden; numpy gerekir, FreeCAD'in Python'u yeterli):
    python DeltaRobotV2/tools/v1_vectors.py
Çıktı: DeltaRobotV2/core/tests/data/v1_vectors.json
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V1 = ROOT / "KilavuzDeltaRobotics" / "modules" / "deltaRobot.py"
OUT = ROOT / "DeltaRobotV2" / "core" / "tests" / "data" / "v1_vectors.json"


def load_v1():
    # V1 modülü grafik kütüphanelerini içe aktarır; hesapta gerekmedikleri için boş taklit verilir.
    mpl = types.ModuleType("matplotlib")
    mpl.pyplot = types.ModuleType("matplotlib.pyplot")
    art3d = types.ModuleType("art3d")
    art3d.Poly3DCollection = None
    tk = types.ModuleType("mpl_toolkits")
    tk.mplot3d = types.ModuleType("mplot3d")
    tk.mplot3d.art3d = art3d
    sys.modules.update(
        {
            "matplotlib": mpl,
            "matplotlib.pyplot": mpl.pyplot,
            "mpl_toolkits": tk,
            "mpl_toolkits.mplot3d": tk.mplot3d,
            "mpl_toolkits.mplot3d.art3d": art3d,
        }
    )
    spec = importlib.util.spec_from_file_location("v1_delta", V1)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # V1 myRobot.json değerleri; limitler V1 FK'sindeki reddi devre dışı bırakacak kadar geniş
    return mod.deltaRobot(
        la=64, lb=201, ra=65, rb=35, btf=240, minTurnAngle=0.29, cwMax=180, ccwMax=-180, jointMax=90
    )


def main() -> None:
    robot = load_v1()
    ik_cases, fk_cases = [], []
    for x in range(-80, 81, 20):
        for y in range(-80, 81, 20):
            for z in range(150, 251, 25):
                t = robot.inverseKinematic(float(x), float(y), float(z))
                if t is False or any(v != v for v in t):
                    continue
                ik_cases.append(
                    {"P": [x, -y, -z], "theta": [float(t[0]), float(t[2]), float(t[1])]}
                )
    for t1 in range(-40, 81, 20):
        for t2 in range(-40, 81, 30):
            for t3 in range(-40, 81, 40):
                r = robot.forwardKinematic(float(t1), float(t2), float(t3))
                if r is False:
                    continue
                d = r[0][3]
                fk_cases.append(
                    {"theta": [float(t1), float(t3), float(t2)], "P": [d[0], -d[1], -d[2]]}
                )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "kaynak": "V1 KilavuzDeltaRobotics/modules/deltaRobot.py; V2 çerçevesine dönüştürüldü",
        "ik": ik_cases,
        "fk": fk_cases,
    }
    OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"ik {len(ik_cases)}, fk {len(fk_cases)}")


if __name__ == "__main__":
    main()
