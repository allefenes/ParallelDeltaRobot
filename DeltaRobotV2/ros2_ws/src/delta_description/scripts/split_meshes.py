#!/usr/bin/env python3
"""CAD bağ mesh'lerini malzeme bölgelerine ayırır (yalnız görsel renk için).

Girdi: cad/out/meshes/<bağ>.stl (ikili STL, bağın yerel çerçevesinde, mm).
Çıktı: <out>/<bağ>__<malzeme>.stl ve <out>/manifest.yaml ({bağ: [malzeme, ...]}).

Kurallar config/visual_materials.yaml dosyasındadır; her üçgen ilk eşleşen kurala atanır.
Kol çerçevesi (frame: arm) robot.yaml'daki kol açıları ve taban yarıçapından kurulur.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import yaml

STL_DTYPE = np.dtype([("n", "<f4", (3,)), ("v", "<f4", (3, 3)), ("attr", "<u2")])


def read_stl(path: Path) -> np.ndarray:
    """İkili STL'i okur; (N, 3, 3) köşe dizisi döndürür (mm)."""
    data = path.read_bytes()
    n = int.from_bytes(data[80:84], "little")
    if 84 + 50 * n != len(data):
        raise ValueError(f"{path}: ikili STL değil ya da bozuk")
    return np.frombuffer(data[84:], dtype=STL_DTYPE, count=n)["v"].astype(np.float64)


def write_stl(path: Path, tris: np.ndarray) -> None:
    """(N, 3, 3) köşe dizisini ikili STL olarak yazar; normaller köşelerden hesaplanır."""
    rec = np.zeros(len(tris), dtype=STL_DTYPE)
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    length = np.linalg.norm(nrm, axis=1, keepdims=True)
    rec["n"] = np.divide(nrm, length, out=np.zeros_like(nrm), where=length > 0)
    rec["v"] = tris
    header = b"delta_description split_meshes".ljust(80, b" ")
    path.write_bytes(header + len(tris).to_bytes(4, "little") + rec.tobytes())


def components(tris: np.ndarray) -> np.ndarray:
    """Ortak köşe paylaşan üçgenleri bağlı bileşenlere ayırır; üçgen başına bileşen etiketi."""
    pts = np.round(tris.reshape(-1, 3), 3)
    _, inv = np.unique(pts, axis=0, return_inverse=True)
    inv = inv.reshape(-1, 3)
    parent = np.arange(inv.max() + 1)

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b, c in inv:
        ra = find(a)
        parent[find(b)] = ra
        parent[find(c)] = ra
    return np.array([find(t[0]) for t in inv])


def arm_frames(robot: dict) -> list[tuple[np.ndarray, np.ndarray]]:
    """Kol çerçeveleri: (dönme R, orijin A_i); robot = R·kol + A_i (mm)."""
    k = robot["kinematics"]
    out = []
    for a_deg in k["arm_angles"]:
        a = math.radians(a_deg)
        rot = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
        out.append(
            (rot, np.array([k["base_radius"] * math.cos(a), k["base_radius"] * math.sin(a), 0]))
        )
    return out


def in_box(p: np.ndarray, box: dict) -> np.ndarray:
    """Noktalar (…, 3) kutunun içinde mi."""
    lo, hi = np.array(box["min"], float), np.array(box["max"], float)
    return np.all((p >= lo) & (p <= hi), axis=-1)


def classify(tris: np.ndarray, spec: dict, frames: list) -> np.ndarray:
    """Her üçgene malzeme adı atar."""
    labels = np.full(len(tris), spec["default"], dtype=object)
    done = np.zeros(len(tris), dtype=bool)
    comp = None
    for rule in spec.get("rules", []):
        local = [(np.eye(3), np.zeros(3))] if rule["frame"] == "link" else frames
        hit = np.zeros(len(tris), dtype=bool)
        for rot, org in local:
            pts = (tris - org) @ rot  # robot -> kol çerçevesi (R ortonormal)
            if "box" in rule:
                hit |= in_box(pts.mean(axis=1), rule["box"])
            else:
                if comp is None:
                    comp = components(tris)
                for c in np.unique(comp):
                    m = comp == c
                    if np.all(in_box(pts[m].reshape(-1, 3), rule["component"])):
                        hit |= m
        new = hit & ~done
        labels[new] = rule["material"]
        done |= new
    return labels


def spec_for(link: str, rules: dict) -> dict:
    """Bağ adından kural kümesi: bicep_2 -> bicep, forearm_1_a -> forearm."""
    for key in rules["links"]:
        if link == key or link.startswith(key + "_"):
            return rules["links"][key]
    raise KeyError(f"{link}: visual_materials.yaml içinde kural yok")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--meshes", type=Path, required=True)
    ap.add_argument("--rules", type=Path, required=True)
    ap.add_argument("--robot", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    rules = yaml.safe_load(args.rules.read_text(encoding="utf-8"))
    frames = arm_frames(yaml.safe_load(args.robot.read_text(encoding="utf-8")))
    args.out.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, list[str]] = {}
    for stl in sorted(args.meshes.glob("*.stl")):
        link = stl.stem
        tris = read_stl(stl)
        labels = classify(tris, spec_for(link, rules), frames)
        manifest[link] = []
        for mat in sorted(set(labels)):
            if mat not in rules["colors"]:
                raise KeyError(f"{mat}: renk tanımı yok")
            write_stl(args.out / f"{link}__{mat}.stl", tris[labels == mat])
            manifest[link].append(mat)
        print(f"{link}: " + ", ".join(f"{m}={int((labels == m).sum())}" for m in manifest[link]))
    (args.out / "manifest.yaml").write_text(
        yaml.safe_dump({"colors": rules["colors"], "links": manifest}, sort_keys=True),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
