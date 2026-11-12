"""F6 deneyim arayüzü uçtan uca testleri (Playwright, Chromium, başsız).

tests/ui/run.sh çalıştırır: varsayılan hedef sahte API (web/dev/mock_server.py), UI_BASE_URL ile
gerçek API. Her senaryo "[ad] GEÇTİ/KALDI: ayrıntı" satırı yazar; çıkış kodu başarısız senaryo
sayısıdır. Ekran görüntüleri UI_SCREENSHOT_DIR'e (varsayılan web/screenshots) 1280x800 yazılır.

Dosya adı test_ ile başlamaz: pytest (dev konteyneri) bu dosyayı toplamaz.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import sys
import time
import traceback
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

BASE = os.environ.get("UI_BASE_URL", "http://localhost:8765").rstrip("/")
ROOT = Path(__file__).resolve().parents[2]
SHOTS = Path(os.environ.get("UI_SCREENSHOT_DIR", ROOT / "web" / "screenshots"))
AUTO_TIMEOUT_S = float(os.environ.get("UI_AUTO_TIMEOUT_S", "240"))
TR = json.loads((ROOT / "i18n" / "locales" / "tr.json").read_text(encoding="utf-8"))
VIEW = {"width": 1280, "height": 800}
# Başsız Chromium'da WebGL yazılımla (SwiftShader) çizilir.
ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]

results: list[tuple[str, bool, str]] = []


def scenario(fn):
    fn.scenario = True
    return fn


# --- yardımcılar --------------------------------------------------------------------------------


def open_page(browser, hash_: str = "#otomatik", viewport=VIEW) -> Page:
    ctx = browser.new_context(viewport=viewport, ignore_https_errors=True, locale="tr-TR")
    page = ctx.new_page()
    page.on("pageerror", lambda e: print(f"  [sayfa hatası] {e}", flush=True))
    page.goto(f"{BASE}/{hash_}")
    ready(page)
    return page


def ready(page: Page) -> None:
    """Oturum açıldı, telemetri akıyor, ikiz kuruldu ve en az bir kez pozlandı."""
    page.wait_for_function(
        "() => window.__twinPose && window.__twinPose.updates > 0", timeout=30_000
    )
    expect(page.locator("#state-badge")).to_have_attribute("data-state", "IDLE", timeout=15_000)


def pose(page: Page) -> dict:
    return page.evaluate("() => window.__twinPose")


def wait_pose(page: Page, angles, tol: float = 0.6, timeout_s: float = 20) -> dict:
    """İkizin (sahne matrisleri) ve telemetrinin açıları hedefe gelene kadar bekler."""
    end = time.monotonic() + timeout_s
    p = pose(page)
    while time.monotonic() < end:
        p = pose(page)
        sa = p["state_angles_deg"]
        if sa and all(abs(a - b) <= tol for a, b in zip(p["angles_deg"], angles, strict=True)):
            if all(abs(a - b) <= tol for a, b in zip(sa, angles, strict=True)):
                return p
        time.sleep(0.1)
    raise AssertionError(f"ikiz hedef açılara gelmedi: {p} != {angles}")


def make_ready(page: Page) -> None:
    """Önceki senaryodan kalan HOLDING durumunu temizler."""
    btn = page.locator("#torque-on")
    if btn.is_enabled():
        btn.click()
    expect(page.locator("#state-badge")).to_have_attribute("data-state", "IDLE", timeout=10_000)


def set_cart(page: Page, x, y, z) -> None:
    for k, v in zip("xyz", (x, y, z), strict=True):
        page.fill(f"#cart-num-{k}", str(v))


def drag(page: Page, sel: str, value: float) -> None:
    """Kaydırıcıyı sürükleyip bırakmanın olayları: input (sürerken) ve change (bırakınca)."""
    page.eval_on_selector(
        sel,
        """(el, v) => { el.value = String(v);
          el.dispatchEvent(new Event("input", { bubbles: true }));
          el.dispatchEvent(new Event("change", { bubbles: true })); }""",
        value,
    )


def no_horizontal_scroll(page: Page) -> bool:
    return page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )


# --- senaryolar ---------------------------------------------------------------------------------


@scenario
def single_page_without_login(browser) -> str:
    page = open_page(browser)
    for sel in ("#token", "#login", "#editor", "#console", "#run", ".camera-placeholder"):
        assert page.locator(sel).count() == 0, f"sayfada olmamalı: {sel}"
    expect(page.locator(".live-note")).to_have_text(TR["web.exp.live_soon"])
    expect(page.locator("#tab-auto")).to_have_text(TR["web.exp.tab_auto"])
    expect(page.locator("#tab-manual")).to_have_text(TR["web.exp.tab_manual"])
    expect(page.locator("#board-diagram .cell")).to_have_count(9)
    p = pose(page)
    page.context.close()
    return f"belirteç arayüzü yok, ikiz pozlu (mesh {p['meshes']['loaded']}/{p['meshes']['total']})"


@scenario
def slider_moves_twin(browser) -> str:
    page = open_page(browser, "#manuel")
    make_ready(page)
    target = [40.0, 10.0, 25.0]
    drag(page, "#joint-range-0", target[0])  # kaydırıcı
    page.fill("#joint-num-1", str(target[1]))
    page.fill("#joint-num-2", str(target[2]))
    fk = page.locator("#fk-preview")
    expect(fk).to_have_attribute("data-kind", "ok", timeout=5_000)
    expect(fk).to_contain_text("P =")
    before = pose(page)["angles_deg"]
    page.click("#joints-go")
    expect(page.locator("#manual-result")).to_have_attribute("data-kind", "ok", timeout=20_000)
    p = wait_pose(page, target)
    # Eşitleme: hareketten sonra XYZ alanları gerçek pozu gösterir.
    page.wait_for_timeout(300)
    xyz = [float(page.input_value(f"#cart-num-{k}")) for k in "xyz"]
    assert all(abs(a - b) <= 0.2 for a, b in zip(xyz, p["position_mm"], strict=True)), (xyz, p)
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / "manuel.png"))
    page.context.close()
    return f"θ {before} -> {p['angles_deg']}, P {p['position_mm']}"


@scenario
def ik_preview_and_move(browser) -> str:
    page = open_page(browser, "#manuel")
    make_ready(page)
    set_cart(page, 12, -8, -205)
    ik = page.locator("#ik-preview")
    expect(ik).to_have_attribute("data-kind", "ok", timeout=5_000)
    text = ik.inner_text()
    angles = [float(v) for v in re.findall(r"-?\d+\.\d", text)[:3]]
    assert len(angles) == 3, text
    page.click("#cart-go")
    expect(page.locator("#manual-result")).to_have_attribute("data-kind", "ok", timeout=20_000)
    p = wait_pose(page, angles, tol=0.15)
    assert all(abs(a - b) <= 0.2 for a, b in zip(p["position_mm"], (12, -8, -205), strict=True))
    # Eklem kaydırıcıları da gerçek pozu izler.
    page.wait_for_timeout(300)
    th = [float(page.input_value(f"#joint-num-{i}")) for i in range(3)]
    assert all(abs(a - b) <= 0.15 for a, b in zip(th, angles, strict=True)), (th, angles)
    page.context.close()
    return f"IK {angles} ° -> P {p['position_mm']}"


@scenario
def limit_rejections(browser) -> str:
    page = open_page(browser, "#manuel")
    make_ready(page)
    ik = page.locator("#ik-preview")
    seen = []
    for xyz, req in (((0, 0, -228), "G14"), ((60, 0, -200), "G2"), ((0, 0, -100), "G3")):
        set_cart(page, *xyz)
        expect(ik).to_have_attribute("data-kind", "error", timeout=5_000)
        expect(ik).to_contain_text(req)
        expect(ik).to_contain_text(TR[f"web.req.{req.lower()}"])
        seen.append(req)
    # Git de reddedilir; robot yerinde kalır.
    set_cart(page, 0, 0, -228)
    before = pose(page)["position_mm"]
    page.click("#cart-go")
    res = page.locator("#manual-result")
    expect(res).to_have_attribute("data-kind", "error", timeout=10_000)
    expect(res).to_contain_text("G14")
    assert pose(page)["position_mm"] == before
    # FK: motor sınırı dışı açı
    page.fill("#joint-num-0", "-75")
    fk = page.locator("#fk-preview")
    expect(fk).to_have_attribute("data-kind", "error", timeout=5_000)
    expect(fk).to_contain_text("G1")
    seen.append("G1")
    page.context.close()
    return "reddedildi: " + ", ".join(seen) + " (+ Git G14)"


@scenario
def stop_holds_and_ready(browser) -> str:
    page = open_page(browser, "#manuel")
    make_ready(page)
    page.fill("#joint-num-0", "-40")
    page.fill("#joint-num-1", "-40")
    page.fill("#joint-num-2", "-40")
    expect(page.locator("#fk-preview")).to_have_attribute("data-kind", "ok", timeout=5_000)
    # Git ve 150 ms sonra DUR (hareket ortasında); gerçek API'de de hareket bundan uzun sürer.
    page.evaluate(
        """() => { document.getElementById("joints-go").click();
                   setTimeout(() => document.getElementById("stop-top").click(), 150); }"""
    )
    badge = page.locator("#state-badge")
    expect(badge).to_have_attribute("data-state", "HOLDING", timeout=5_000)
    expect(page.locator("#torque-on")).to_be_enabled()
    expect(page.locator("#stop-top")).to_be_enabled()
    page.click("#torque-on")
    expect(badge).to_have_attribute("data-state", "IDLE", timeout=5_000)
    page.context.close()
    return "DUR -> HOLDING, Hazırla -> IDLE"


@scenario
def auto_game_runs(browser) -> str:
    page = open_page(browser, "#otomatik")
    make_ready(page)
    if page.locator("#auto-reset").is_enabled():
        page.click("#auto-reset")
    page.click("#auto-start")
    status = page.locator("#auto-status")
    expect(status).to_have_attribute("data-status", "playing", timeout=10_000)
    expect(page.locator("#joints-go")).to_be_disabled()  # manuel kilitli
    expect(page.locator("#moves-body tr")).not_to_have_count(0, timeout=60_000)
    expect(status).to_have_attribute("data-status", "finished", timeout=AUTO_TIMEOUT_S * 1000)
    rows = page.locator("#moves-body tr").all_inner_texts()
    for r in rows:
        assert re.fullmatch(r"\d+\s+[XO]\s+[ABC][123]→[ABC][123]", r.strip()), r
    winner = page.locator("#auto-winner").inner_text()
    assert winner != "—", winner
    page.wait_for_timeout(500)
    page.screenshot(path=str(SHOTS / "otomatik.png"))
    page.context.close()
    return f"{len(rows)} hamle, sonuç: {winner}"


@scenario
def auto_stop_and_reset(browser) -> str:
    page = open_page(browser, "#otomatik")
    make_ready(page)
    page.click("#auto-reset")
    page.click("#auto-start")
    status = page.locator("#auto-status")
    expect(status).to_have_attribute("data-status", "playing", timeout=10_000)
    page.click("#auto-stop")
    expect(status).to_have_attribute("data-status", "stopped", timeout=10_000)
    expect(page.locator("#state-badge")).to_have_attribute("data-state", "IDLE", timeout=10_000)
    expect(page.locator("#auto-reset")).to_be_enabled()
    page.click("#auto-reset")
    cells = page.locator("#board-diagram .cell")
    expect(cells.nth(0)).to_have_text("X", timeout=5_000)
    expect(cells.nth(8)).to_have_text("O")
    expect(page.locator("#moves-body tr")).to_have_count(0)
    page.context.close()
    return "Durdur -> stopped/IDLE, Sıfırla -> başlangıç dizilişi"


@scenario
def session_renewed_on_401(browser) -> str:
    page = open_page(browser, "#otomatik")
    sessions = []
    page.on("request", lambda r: r.url.endswith("/api/v1/session") and sessions.append(r))
    hit = {"n": 0}

    def once_401(route):
        if hit["n"] == 0:
            hit["n"] += 1
            return route.fulfill(
                status=401, content_type="application/json", body='{"error":"unauthorized"}'
            )
        return route.continue_()

    page.route("**/api/v1/board", once_401)
    end = time.monotonic() + 10
    while not sessions and time.monotonic() < end:
        page.wait_for_timeout(100)
    assert sessions, "401'den sonra yeni oturum açılmadı"
    ready(page)
    page.context.close()
    return f"401 -> {len(sessions)} yeni oturum, ikiz yine pozlu"


def fake_session(status: int, code: str):
    body = json.dumps({"error": code})
    return lambda route: route.fulfill(status=status, content_type="application/json", body=body)


@scenario
def capacity_messages(browser) -> str:
    out = []
    for status, code, key in (
        (503, "capacity", "web.exp.capacity"),
        (429, "rate_limited", "web.exp.rate_limited"),
    ):
        ctx = browser.new_context(viewport=VIEW, ignore_https_errors=True)
        page = ctx.new_page()
        page.route("**/api/v1/session", fake_session(status, code))
        page.goto(f"{BASE}/")
        notice = page.locator("#notice")
        expect(notice).to_be_visible(timeout=10_000)
        expect(notice).to_contain_text(TR[key])
        out.append(str(status))
        ctx.close()
    return "uyarı gösterildi: " + ", ".join(out)


@scenario
def phone_width(browser) -> str:
    page = open_page(browser, "#otomatik", viewport={"width": 375, "height": 812})
    assert no_horizontal_scroll(page), "otomatik: yatay kaydırma var"
    page.click("#tab-manual")
    expect(page.locator("#panel-manual")).to_be_visible()
    assert no_horizontal_scroll(page), "manuel: yatay kaydırma var"
    expect(page.locator("#stop-top")).to_be_visible()
    page.context.close()
    return "375 px: yatay kaydırma yok"


@scenario
def keyboard_tabs(browser) -> str:
    page = open_page(browser, "#otomatik")
    page.focus("#tab-auto")
    page.keyboard.press("ArrowRight")
    expect(page.locator("#tab-manual")).to_have_attribute("aria-selected", "true")
    expect(page.locator("#tab-manual")).to_be_focused()
    expect(page.locator("#panel-auto")).to_be_hidden()
    page.context.close()
    return "ok tuşlarıyla sekme geçişi"


def wait_health(timeout_s: float = 60) -> None:
    ctx = ssl.create_default_context()
    ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE  # yerel, kendinden imzalı
    end = time.monotonic() + timeout_s
    while True:
        try:
            with urllib.request.urlopen(f"{BASE}/api/v1/health", context=ctx, timeout=3) as r:
                print(f"Hedef: {BASE} {r.read().decode()}", flush=True)
                return
        except OSError:
            if time.monotonic() > end:
                raise
            time.sleep(0.5)


def main() -> int:
    only = set(sys.argv[1:])
    fns = [f for f in globals().values() if getattr(f, "scenario", False)]
    wait_health()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=ARGS)
        for fn in fns:
            if only and fn.__name__ not in only:
                continue
            t0 = time.monotonic()
            try:
                detail = fn(browser)
                ok = True
            except Exception as e:  # noqa: BLE001 - her senaryo raporlanır
                ok, detail = False, f"{type(e).__name__}: {e}"
                traceback.print_exc()
            dt = time.monotonic() - t0
            results.append((fn.__name__, ok, detail))
            print(
                f"[{fn.__name__}] {'GEÇTİ' if ok else 'KALDI'} ({dt:.1f} s): {detail}", flush=True
            )
        browser.close()
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{len(results) - failed}/{len(results)} senaryo geçti", flush=True)
    return failed


if __name__ == "__main__":
    sys.exit(main())
