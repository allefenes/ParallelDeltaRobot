#!/usr/bin/env python3
"""Malzeme listesini (BOM) üretir ve CAD ile senkronunu denetler.

Girdi : hardware/bom.yaml (elle tutulan alanlar) + cad/out/parts.json (CAD'den adet ve kütle)
Çıktı : hardware/bom.csv (makine okunur) + hardware/bom.md (okunur, Prettier biçiminde tablo)

    python3 tools/bom.py          dosyaları üretir
    python3 tools/bom.py --check  CAD'deki her parça BOM'da mı, BOM'daki her CAD etiketi CAD'de mi,
                                  üretilen dosyalar güncel mi; sorun varsa 1 ile çıkar (CI)
"""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BOM_YAML = ROOT / "hardware" / "bom.yaml"
PARTS_JSON = ROOT / "cad" / "out" / "parts.json"
BOM_CSV = ROOT / "hardware" / "bom.csv"
BOM_MD = ROOT / "hardware" / "bom.md"

CATEGORIES = {
    "govde": "Gövde",
    "baski": "3B baskı",
    "satin_alma": "Satın alma",
    "baglanti": "Bağlantı elemanı",
    "elektronik": "Elektronik",
    "sarf": "Sarf",
}
STATUS = {"v1": "V1 (olduğu gibi)", "varsayim": "Varsayım", "v2": "V2'de değişti"}
COLUMNS = [
    "No",
    "Ad",
    "Kategori",
    "Malzeme / özellik",
    "Adet",
    "Birim kütle (g)",
    "Toplam kütle (g)",
    "Üretim",
    "Tedarikçi",
    "Birim fiyat (TL)",
    "Durum",
    "Kaynak",
    "Not",
]


def fmt_mass(v) -> str:
    return "" if v in ("", None) else f"{float(v):.1f}"


def build_rows(bom: dict, parts: dict) -> tuple[list[list[str]], list[str]]:
    """(satırlar, hatalar). Adet/kütle CAD'den gelir; CAD'de olmayan kalemler elle."""
    errors: list[str] = []
    rows: list[list[str]] = []
    used: set[str] = set()
    for it in sorted(bom["items"], key=lambda x: x["id"]):
        if "cad" in it:
            labels = it["cad"]
            missing = [lb for lb in labels if lb not in parts]
            if missing:
                errors.append(f"{it['id']} {it['name']}: CAD'de olmayan etiket {missing}")
                continue
            counts = {parts[lb]["count"] for lb in labels}
            if len(counts) != 1:
                errors.append(f"{it['id']} {it['name']}: etiket adetleri farklı {counts}")
            qty = parts[labels[0]]["count"]
            unit = sum(parts[lb]["unit_mass_g"] for lb in labels)
            used.update(labels)
            source = "CAD"
        else:
            qty, unit, source = it["qty"], it.get("unit_mass_g", ""), "elle"
        total = "" if unit in ("", None) else float(unit) * qty
        rows.append(
            [
                str(it["id"]),
                it["name"],
                CATEGORIES[it["category"]],
                it.get("spec", ""),
                str(qty),
                fmt_mass(unit),
                fmt_mass(total),
                it.get("method", ""),
                it.get("supplier", "") or "TBD",
                str(it.get("price", "") or ""),
                STATUS[it["status"]],
                source,
                it.get("notes", ""),
            ]
        )
    for lb in sorted(set(parts) - used):
        errors.append(f"CAD parçası BOM'da yok: {lb}")
    return rows, errors


def render_csv(rows: list[list[str]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(COLUMNS)
    w.writerows(rows)
    return buf.getvalue()


def md_table(header: list[str], rows: list[list[str]]) -> list[str]:
    """Prettier'ın ürettiği hizalı Markdown tablosu (sola yaslı)."""
    cells = [header] + rows
    cells = [[c.replace("|", "\\|") for c in r] for r in cells]
    widths = [max(3, *(len(r[i]) for r in cells)) for i in range(len(header))]

    def line(r):
        return "| " + " | ".join(c.ljust(w) for c, w in zip(r, widths, strict=True)) + " |"

    sep = "| " + " | ".join("-" * w for w in widths) + " |"
    return [line(cells[0]), sep] + [line(r) for r in cells[1:]]


def render_md(rows: list[list[str]]) -> str:
    out = [
        "# Malzeme listesi (BOM)",
        "",
        "Bu dosya üretilir; elle düzenlemeyin. Kaynak: [bom.yaml](bom.yaml) "
        "(elle tutulan alanlar) ve CAD (`cad/out/parts.json`: adet ve kütle). "
        "Makine okunur sürüm: [bom.csv](bom.csv).",
        "",
        "Üretmek: `docker compose run --rm dev python3 tools/bom.py`",
        "",
        "**Durum: F5 askıda (2026-11-12).** Hiçbir kalem satın alınmadı ya da üretilmedi. "
        "Elektronik kalemler (donanım bekçisi, mıknatıs sürücüsü, acil stop, Pi beslemesi) ve "
        "kutu/kamera tasarımı kesinleşmedi; fiyat ve tedarikçi alanları boştur.",
        "",
    ]
    out += md_table(COLUMNS, rows)
    masses = {}
    for r in rows:
        if r[6]:
            masses[r[2]] = masses.get(r[2], 0.0) + float(r[6])
    out += ["", "## Kategori toplamları (kütlesi bilinen kalemler)", ""]
    sums = [[k, f"{v:.1f}"] for k, v in masses.items()]
    sums.append(["Toplam", f"{sum(masses.values()):.1f}"])
    out += md_table(["Kategori", "Kütle (g)"], sums)
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    bom = yaml.safe_load(BOM_YAML.read_text(encoding="utf-8"))
    parts = json.loads(PARTS_JSON.read_text(encoding="utf-8"))
    rows, errors = build_rows(bom, parts)
    csv_text, md_text = render_csv(rows), render_md(rows)
    if "--check" in argv:
        if BOM_CSV.read_text(encoding="utf-8") != csv_text:
            errors.append("hardware/bom.csv güncel değil")
        if BOM_MD.read_text(encoding="utf-8") != md_text:
            errors.append("hardware/bom.md güncel değil")
        for e in errors:
            print(f"HATA: {e}")
        if errors:
            print("Düzeltmek için: docker compose run --rm dev python3 tools/bom.py")
            return 1
        print(f"BOM tamam ({len(rows)} kalem, CAD ile senkron)")
        return 0
    for e in errors:
        print(f"HATA: {e}")
    if errors:
        return 1
    BOM_CSV.write_text(csv_text, encoding="utf-8", newline="\n")
    BOM_MD.write_text(md_text, encoding="utf-8", newline="\n")
    print(f"{len(rows)} kalem yazıldı")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
