"""Tarayıcı arayüzünün JS çalıştırmadan denetimi: i18n anahtarları, CDN sürümleri, yerel bağlar."""

import json
import re
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent
ROOT = WEB.parent
TR = json.loads((ROOT / "i18n" / "locales" / "tr.json").read_text(encoding="utf-8"))
JS_FILES = sorted((WEB / "js").glob("*.js"))
HTML = (WEB / "index.html").read_text(encoding="utf-8")

# Katalog anahtarına benzeyen tırnaklı dizgiler (ör. "web.jog.go")
KEY_LITERAL = re.compile(r"""["'`]((?:app|nav|robot|web|safety|session)(?:\.[a-z0-9_]+)+)["'`]""")
DATA_I18N = re.compile(r'data-i18n(?:-[a-z-]+)?="([^"]+)"')
URL = re.compile(r"""https?://[^\s"'<>)]+""")
PINNED = {
    "three": "0.160.0",
    "codemirror": "5.65.16",
}


def js_keys() -> set[str]:
    keys = set()
    for f in JS_FILES:
        keys |= set(KEY_LITERAL.findall(f.read_text(encoding="utf-8")))
    return keys


def test_js_and_html_reference_keys():
    assert len(js_keys()) > 20
    assert len(DATA_I18N.findall(HTML)) > 20


def test_every_used_key_exists_in_tr():
    used = js_keys() | set(DATA_I18N.findall(HTML))
    missing = sorted(k for k in used if k not in TR)
    assert missing == []


def test_only_pinned_jsdelivr_urls():
    urls = URL.findall(HTML)
    for f in JS_FILES:
        urls += URL.findall(f.read_text(encoding="utf-8"))
    assert urls, "index.html CDN bağı içermeli"
    for u in urls:
        m = re.match(r"https://cdn\.jsdelivr\.net/npm/([a-z0-9.-]+)@(\d+\.\d+\.\d+)/", u)
        assert m, f"sabitlenmemiş ya da izinsiz URL: {u}"
        pkg, ver = m.groups()
        assert PINNED.get(pkg) == ver, f"{pkg}@{ver} beklenen sürüm değil"


def test_import_map_maps_three_and_addons():
    m = re.search(r'<script type="importmap">(.*?)</script>', HTML, re.S)
    assert m
    imports = json.loads(m.group(1))["imports"]
    assert imports["three"].endswith("three@0.160.0/build/three.module.js")
    assert imports["three/addons/"].endswith("three@0.160.0/examples/jsm/")


def test_local_references_exist():
    refs = re.findall(r'(?:src|href)="(?!https?:|data:)([^"]+)"', HTML)
    assert "js/main.js" in refs and "css/style.css" in refs
    for r in refs:
        assert (WEB / r).is_file(), r
    for f in JS_FILES:
        for imp in re.findall(r"""(?:from|import\()\s*["'](\.[^"']+)["']""", f.read_text("utf-8")):
            assert (f.parent / imp).resolve().is_file(), f"{f.name}: {imp}"
    assert (WEB / "examples" / "baslangic.py").is_file()


def test_no_hardcoded_turkish_text_in_js():
    # Görünür metinler katalogdan gelir; yorumlar hariç Türkçe harfli dizgi olmamalı.
    turkish = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
    for f in JS_FILES:
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            code = re.sub(r"//.*$", "", line)
            assert not turkish.search(code), f"{f.name}:{n}: {line.strip()}"


def test_starter_example_uses_client():
    code = (WEB / "examples" / "baslangic.py").read_text(encoding="utf-8")
    assert "from delta_robot import" in code and "Robot()" in code
    compile(code, "baslangic.py", "exec")
