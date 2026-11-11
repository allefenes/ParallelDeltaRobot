#!/usr/bin/env python3
"""i18n kataloglarını denetler.

Kurallar (bkz. i18n/README.md):
- tr.json kaynak dildir.
- Diğer kataloglar tr.json'da olmayan anahtar içeremez (hata).
- Çevirideki yer tutucular kaynakla aynı olmalıdır (hata).
- Eksik çeviri uyarıdır; arayüz Türkçeye düşer.
- Anahtar biçimi: küçük harf, rakam, alt çizgi; nokta ile ayrılmış (hata).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SOURCE_LANG = "tr"
KEY_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$")
PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")


def placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER_RE.findall(text))


def load_catalog(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in data.items()
    ):
        raise ValueError(f"{path.name}: düz anahtar -> metin nesnesi olmalı")
    return data


def check(locales_dir: Path) -> tuple[list[str], list[str]]:
    """(hatalar, uyarılar) döndürür."""
    errors: list[str] = []
    warnings: list[str] = []

    source_path = locales_dir / f"{SOURCE_LANG}.json"
    if not source_path.exists():
        return [f"kaynak katalog yok: {source_path}"], []

    try:
        source = load_catalog(source_path)
    except (ValueError, json.JSONDecodeError) as e:
        return [str(e)], []

    for key in source:
        if not KEY_RE.match(key):
            errors.append(f"{SOURCE_LANG}: geçersiz anahtar biçimi: {key!r}")

    for path in sorted(locales_dir.glob("*.json")):
        lang = path.stem
        if lang == SOURCE_LANG:
            continue
        try:
            catalog = load_catalog(path)
        except (ValueError, json.JSONDecodeError) as e:
            errors.append(str(e))
            continue

        for key, text in catalog.items():
            if key not in source:
                errors.append(f"{lang}: kaynakta olmayan anahtar: {key}")
                continue
            if placeholders(text) != placeholders(source[key]):
                errors.append(
                    f"{lang}: {key}: yer tutucular uyuşmuyor "
                    f"({sorted(placeholders(text))} != {sorted(placeholders(source[key]))})"
                )

        missing = sorted(set(source) - set(catalog))
        for key in missing:
            warnings.append(f"{lang}: çeviri eksik (Türkçeye düşer): {key}")

    return errors, warnings


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    locales_dir = root / "i18n" / "locales"
    errors, warnings = check(locales_dir)
    for w in warnings:
        print(f"UYARI: {w}")
    for e in errors:
        print(f"HATA: {e}")
    if errors:
        return 1
    print(f"i18n tamam ({len(list(locales_dir.glob('*.json')))} katalog)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
