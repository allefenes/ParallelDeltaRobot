import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import check_i18n  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def write(dir_: Path, lang: str, data: dict) -> None:
    (dir_ / f"{lang}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_repo_catalogs_are_valid():
    errors, _ = check_i18n.check(ROOT / "i18n" / "locales")
    assert errors == []


def test_missing_translation_is_warning(tmp_path):
    write(tmp_path, "tr", {"a.b": "x", "a.c": "y"})
    write(tmp_path, "en", {"a.b": "x"})
    errors, warnings = check_i18n.check(tmp_path)
    assert errors == []
    assert any("a.c" in w for w in warnings)


def test_unknown_key_is_error(tmp_path):
    write(tmp_path, "tr", {"a.b": "x"})
    write(tmp_path, "en", {"a.b": "x", "a.z": "z"})
    errors, _ = check_i18n.check(tmp_path)
    assert any("a.z" in e for e in errors)


def test_placeholder_mismatch_is_error(tmp_path):
    write(tmp_path, "tr", {"m": "{motor}. motor"})
    write(tmp_path, "en", {"m": "motor {id}"})
    errors, _ = check_i18n.check(tmp_path)
    assert len(errors) == 1


def test_bad_key_format_is_error(tmp_path):
    write(tmp_path, "tr", {"Bad Key": "x"})
    errors, _ = check_i18n.check(tmp_path)
    assert errors
