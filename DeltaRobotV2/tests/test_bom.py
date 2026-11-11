"""tools/bom.py testleri: CAD ile senkron denetimi ve üretilen tablo biçimi."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import bom  # noqa: E402

PARTS = {
    "a": {"count": 2, "unit_mass_g": 1.5, "material": "x"},
    "b": {"count": 2, "unit_mass_g": 0.5, "material": "x"},
}


def item(**kw):
    base = {"id": 1, "name": "A", "category": "govde", "status": "v1", "cad": ["a"]}
    base.update(kw)
    return base


def test_cad_quantities_and_masses():
    rows, errors = bom.build_rows({"items": [item(cad=["a", "b"])]}, PARTS)
    assert errors == []
    assert rows[0][4] == "2"  # adet
    assert rows[0][5] == "2.0"  # birim kütle a + b
    assert rows[0][6] == "4.0"
    assert rows[0][11] == "CAD"


def test_manual_item():
    manual = {"id": 2, "name": "M", "category": "sarf", "status": "varsayim", "qty": 3}
    rows, errors = bom.build_rows({"items": [item(cad=["a", "b"]), manual]}, PARTS)
    assert errors == []
    assert rows[1][4] == "3"
    assert rows[1][5] == "" and rows[1][6] == ""
    assert rows[1][11] == "elle"


def test_missing_and_unused_labels_are_errors():
    _, errors = bom.build_rows({"items": [item(cad=["zzz"])]}, PARTS)
    assert any("CAD'de olmayan" in e for e in errors)
    assert any("BOM'da yok: a" in e for e in errors)


def test_count_mismatch_is_error():
    parts = {"a": {"count": 2, "unit_mass_g": 1}, "b": {"count": 3, "unit_mass_g": 1}}
    _, errors = bom.build_rows({"items": [item(cad=["a", "b"])]}, parts)
    assert any("adetleri farklı" in e for e in errors)


def test_md_table_is_aligned_like_prettier():
    lines = bom.md_table(["A", "Uzun başlık"], [["x|y", "1"]])
    assert lines[0] == "| A    | Uzun başlık |"
    assert lines[1] == "| ---- | ----------- |"
    assert lines[2] == "| x\\|y | 1           |"


def test_render_outputs():
    rows, _ = bom.build_rows({"items": [item(cad=["a", "b"])]}, PARTS)
    assert bom.render_csv(rows).splitlines()[0].startswith("No,Ad,")
    md = bom.render_md(rows)
    assert "## Kategori toplamları" in md and "| Toplam" in md


def test_repo_bom_is_in_sync():
    assert bom.main(["--check"]) == 0


def test_main_generate_and_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(bom, "BOM_CSV", tmp_path / "bom.csv")
    monkeypatch.setattr(bom, "BOM_MD", tmp_path / "bom.md")
    assert bom.main([]) == 0
    assert (tmp_path / "bom.md").exists()
    assert bom.main(["--check"]) == 0
    (tmp_path / "bom.md").write_text("eski", encoding="utf-8")
    assert bom.main(["--check"]) == 1
    yml = tmp_path / "bom.yaml"
    yml.write_text("items:\n  - {id: 1, name: X, category: govde, status: v1, cad: [yok]}\n")
    monkeypatch.setattr(bom, "BOM_YAML", yml)
    assert bom.main([]) == 1
