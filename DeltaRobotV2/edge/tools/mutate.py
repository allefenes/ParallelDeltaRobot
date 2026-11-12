#!/usr/bin/env python3
"""Kenar servisinin kritik modülleri için basit mutasyon testi (yalnız standart kütüphane).

Geliştirme konteynerinde DeltaRobotV2/ kökünden çalışır:

    python3 edge/tools/mutate.py                 # varsayılan: <=150 mutant, tohum 1
    python3 edge/tools/mutate.py --max-mutants 40 --files edge/src/watchdog.cpp
    python3 edge/tools/mutate.py --list          # yalnız mutantları listeler, derlemez

Her mutant tek tek uygulanır: kaynak dosya değiştirilir, `cmake --build build/edge-mut` artımlı
derler, `ctest --test-dir build/edge-mut` zaman aşımıyla çalışır, dosya HER durumda (try/finally)
özgün haline döndürülür. Sonda tüm dosyaların SHA-256 özeti başlangıçla karşılaştırılır.

Operatörler: ilişkisel (<,<=,>,>=,==,!=), mantıksal (&&,||), sayısal sabit ±1, true/false,
deyim/return silme (yorum, #include ve bildirim satırları atlanır).

Çıktılar: build/mutation/report.md ve build/mutation/summary.json.
Sonuç: killed (bir test düştü), survived (tüm testler geçti), build_failed (derlenmedi; skora
girmez), timeout. Skor = killed / (killed + survived).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Dosya -> mutasyon dışı tutulan fonksiyonlar (yalnız insan okunur hata metni üretirler) ve
# varsa yalnız belirli bir satır bölgesi (başlangıç ve bitiş düzenli ifadeleri).
TARGETS: dict[str, dict] = {
    "edge/src/gate.cpp": {"skip_functions": ["num", "joint", "step_name"]},
    "edge/src/watchdog.cpp": {},
    # protocol.cpp: yalnız doğrulama bölümü (only_keys .. parse_impl); yazıcılar hariç.
    "edge/src/protocol.cpp": {"region": (r"^bool only_keys\(", r"^std::string dump\(")},
}

REL_SWAP = {"<": "<=", "<=": "<", ">": ">=", ">=": ">", "==": "!=", "!=": "=="}
# İkili işleçler clang-format ile boşluklarla çevrili; şablon açıları (std::get<T>) boşluksuz.
REL_RE = re.compile(r"(?<=\s)(<=|>=|==|!=|<|>)(?=\s)")
LOGIC_RE = re.compile(r"(?<=\s)(&&|\|\|)(?=\s)")
NUM_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w.])")
BOOL_RE = re.compile(r"\b(true|false)\b")
# Silinebilir deyim: return, atama ya da çağrı. Bildirimler (tip + ad) eşleşmez.
STMT_RE = re.compile(
    r"^\s*(return\b.*|\*?[A-Za-z_][\w.\[\]]*(?:->\w+)*\s*(?:=|\+=|-=)\s.*"
    r"|[A-Za-z_][\w.\[\]]*(?:->\w+|\.\w+)*\(.*\)|\+\+\w+|\w+\+\+)\s*;\s*$"
)
IF_RETURN_RE = re.compile(r"^(\s*(?:if|else if) \(.*\)) return\b.*;\s*$")


@dataclass
class Mutant:
    mid: int
    file: str
    line: int  # 1 tabanlı
    col: int  # 0 tabanlı, değişen sütun
    op: str
    original: str
    mutated: str
    status: str = "pending"
    seconds: float = 0.0
    failed_tests: list[str] = field(default_factory=list)


def mask_line(line: str, in_block: bool) -> tuple[str, bool]:
    """Yorumları ve metin/karakter sabitlerini aynı uzunlukta boşlukla maskeler."""
    out = []
    i = 0
    n = len(line)
    while i < n:
        if in_block:
            end = line.find("*/", i)
            if end < 0:
                out.append(" " * (n - i))
                return "".join(out), True
            out.append(" " * (end + 2 - i))
            i = end + 2
            in_block = False
            continue
        c = line[i]
        if line.startswith("//", i):
            out.append(" " * (n - i))
            break
        if line.startswith("/*", i):
            in_block = True
            continue
        if c in "\"'":
            j = i + 1
            while j < n and line[j] != c:
                j += 2 if line[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(c + " " * (j - i - 2) + (c if j - i >= 2 else ""))
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out), in_block


def function_body_lines(lines: list[str], cfg: dict) -> dict[int, str]:
    """Fonksiyon gövdesi içindeki satırlar: indeks -> maskelenmiş metin."""
    result: dict[int, str] = {}
    stack: list[str] = []  # her açık parantez için 'ns', 'fn' ya da 'skip'
    in_block = False
    region = cfg.get("region")
    in_region = region is None
    skip_fn = set(cfg.get("skip_functions", []))
    pending_kind = "fn"
    for idx, raw in enumerate(lines):
        masked, in_block = mask_line(raw, in_block)
        if region is not None:
            if re.match(region[0], raw):
                in_region = True
            elif re.match(region[1], raw):
                in_region = False
        stripped = masked.strip()
        at_ns_level = all(k == "ns" for k in stack)
        if at_ns_level and stripped:
            if stripped.startswith("namespace"):
                pending_kind = "ns"
            else:
                m = re.search(r"\b(\w+)\s*\(", masked)
                if m and not raw.startswith(" "):
                    pending_kind = "skip" if m.group(1) in skip_fn or not in_region else "fn"
        inside_fn = bool(stack) and stack[-1] != "ns" and "skip" not in stack
        if inside_fn and stripped and not stripped.startswith("#"):
            result[idx] = masked
        for ch in masked:
            if ch == "{":
                if all(k == "ns" for k in stack):
                    stack.append(pending_kind)
                else:
                    stack.append(stack[-1] if stack[-1] != "ns" else "fn")
            elif ch == "}" and stack:
                stack.pop()
    return result


def generate(path: Path, rel: str, cfg: dict) -> list[Mutant]:
    lines = path.read_text(encoding="utf-8").split("\n")
    body = function_body_lines(lines, cfg)
    muts: list[Mutant] = []

    def add(idx: int, op: str, new_line: str, col: int = 0) -> None:
        if new_line != lines[idx]:
            muts.append(Mutant(0, rel, idx + 1, col, op, lines[idx], new_line))

    prev_code = ""
    for idx in sorted(body):
        raw, masked = lines[idx], body[idx]
        for m in REL_RE.finditer(masked):
            s, e = m.span()
            new = REL_SWAP[m.group(1)]
            add(idx, f"rel {m.group(1)}->{new}", raw[:s] + new + raw[e:], s)
        for m in LOGIC_RE.finditer(masked):
            s, e = m.span()
            new = "||" if m.group(1) == "&&" else "&&"
            add(idx, f"logic {m.group(1)}->{new}", raw[:s] + new + raw[e:], s)
        for m in NUM_RE.finditer(masked):
            s, e = m.span()
            tok = m.group(1)
            for delta in (1, -1):
                if "." in tok:
                    decimals = len(tok.split(".")[1])
                    val = f"{float(tok) + delta:.{decimals}f}"
                else:
                    val = str(int(tok) + delta)
                if val.startswith("-"):
                    continue  # negatif sabit ifadeyi bozabilir (a - -1); atlanır
                add(idx, f"num {tok}->{val}", raw[:s] + val + raw[e:], s)
        for m in BOOL_RE.finditer(masked):
            s, e = m.span()
            new = "false" if m.group(1) == "true" else "true"
            add(idx, f"bool {m.group(1)}->{new}", raw[:s] + new + raw[e:], s)
        # Deyim silme: tek satırlık, önceki satır deyim sonu ise (çok satırlı deyimin ortası değil).
        statement_start = prev_code.endswith((";", "{", "}", ")")) or prev_code == ""
        indent = raw[: len(raw) - len(raw.lstrip())]
        if statement_start and STMT_RE.match(masked) and masked.count("(") == masked.count(")"):
            add(idx, "delete statement", indent + "{}  // mutant: silindi")
        m = IF_RETURN_RE.match(masked)
        if m and m.group(1).count("(") == m.group(1).count(")"):
            add(idx, "delete if-return", raw[: m.end(1)] + " {}")
        prev_code = masked.strip()
    return muts


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list[str], timeout: float) -> tuple[int | None, str]:
    try:
        p = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout
        )
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        return None, out


def build(build_dir: str, timeout: float) -> tuple[int | None, str]:
    return run(["cmake", "--build", build_dir, "--target", "edge_core_tests"], timeout)


def ctest(build_dir: str, test_timeout: int, timeout: float, jobs: int) -> tuple[str, list[str]]:
    code, out = run(
        [
            "ctest",
            "--test-dir",
            build_dir,
            "--timeout",
            str(test_timeout),
            "-j",
            str(jobs),
            "--stop-on-failure",
        ],
        timeout,
    )
    failed = re.findall(r"^\s*\d+ - (\S+) \((\w+)\)", out, re.M)
    if code is None or any(kind == "Timeout" for _, kind in failed):
        return "timeout", [name for name, _ in failed]
    if code == 0:
        return "survived", []
    return "killed", [name for name, _ in failed]


def write_reports(out_dir: Path, muts: list[Mutant], meta: dict) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    per_file: dict[str, dict] = {}
    for m in muts:
        d = per_file.setdefault(
            m.file, {"killed": 0, "survived": 0, "build_failed": 0, "timeout": 0, "pending": 0}
        )
        d[m.status] += 1
    for d in per_file.values():
        denom = d["killed"] + d["survived"]
        d["score"] = round(d["killed"] / denom, 4) if denom else None
    kinds = ("killed", "survived", "build_failed", "timeout")
    tot = {k: sum(d[k] for d in per_file.values()) for k in kinds}
    denom = tot["killed"] + tot["survived"]
    tot["score"] = round(tot["killed"] / denom, 4) if denom else None
    summary = {**meta, "total": tot, "per_file": per_file, "mutants": [asdict(m) for m in muts]}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")

    def pct(x: float | None) -> str:
        return "-" if x is None else f"{100 * x:.1f}%"

    rows = [
        "# Mutasyon testi raporu",
        "",
        f"Tohum {meta['seed']}, aday {meta['candidates']}, çalıştırılan {len(muts)} mutant, "
        f"süre {meta['seconds']:.0f} s. Skor = killed / (killed + survived).",
        "",
        "| Dosya | killed | survived | build_failed | timeout | skor |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for f, d in sorted(per_file.items()):
        rows.append(
            f"| `{f}` | {d['killed']} | {d['survived']} | {d['build_failed']} | {d['timeout']} "
            f"| {pct(d['score'])} |"
        )
    rows.append(
        f"| **toplam** | {tot['killed']} | {tot['survived']} | {tot['build_failed']} "
        f"| {tot['timeout']} | {pct(tot['score'])} |"
    )
    rows += ["", "## Hayatta kalan mutantlar", ""]
    surv = [m for m in muts if m.status == "survived"]
    if not surv:
        rows.append("Yok.")
    for m in surv:
        rows += [
            f"- `{m.file}:{m.line}:{m.col}` {m.op}",
            f"  - önce: `{m.original.strip()}`",
            f"  - sonra: `{m.mutated.strip()}`",
        ]
    rows += ["", "## Zaman aşımı", ""]
    tmo = [m for m in muts if m.status == "timeout"]
    rows += [f"- `{m.file}:{m.line}` {m.op}" for m in tmo] or ["Yok."]
    (out_dir / "report.md").write_text("\n".join(rows) + "\n")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--files", nargs="*", default=list(TARGETS), help="mutasyon hedefleri")
    ap.add_argument("--max-mutants", type=int, default=150)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--build-dir", default="build/edge-mut")
    ap.add_argument("--out", default="build/mutation")
    ap.add_argument("--test-timeout", type=int, default=30, help="tek ctest testi için s")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--list", action="store_true", help="yalnız listele")
    args = ap.parse_args()

    root = Path.cwd()
    if not (root / "edge" / "CMakeLists.txt").exists():
        print("DeltaRobotV2/ kökünden çalıştırın", file=sys.stderr)
        return 2

    out_dir = root / args.out
    backup_dir = out_dir / "backup"
    lock = out_dir / "LOCK"
    # Önceki çalıştırma yarıda kaldıysa (ör. konteyner öldürüldü) önce özgün dosyaları geri yükle.
    if lock.exists():
        for rel, digest in json.loads(lock.read_text()).items():
            if sha256(root / rel) != digest:
                shutil.copyfile(backup_dir / Path(rel).name, root / rel)
                print(f"uyarı: {rel} önceki yarım çalıştırmadan geri yüklendi", file=sys.stderr)
        lock.unlink()

    files = [f for f in args.files if f in TARGETS]
    originals = {f: (root / f).read_bytes() for f in files}
    hashes = {f: sha256(root / f) for f in files}

    candidates: list[Mutant] = []
    for f in files:
        candidates += generate(root / f, f, TARGETS[f])
    rng = random.Random(args.seed)
    if len(candidates) > args.max_mutants:
        # Bütçe dosyalara eşit paylaştırılır; küçük dosya payını doldurmazsa artanı diğerlerine
        # kalır. Dosya içinde tohumlu rastgele örnekleme (aynı tohum = aynı mutantlar).
        pools = sorted(
            ([m for m in candidates if m.file == f] for f in files), key=lambda p: len(p)
        )
        chosen: list[Mutant] = []
        budget = args.max_mutants
        for i, pool in enumerate(pools):
            k = min(len(pool), budget // (len(pools) - i))
            chosen += rng.sample(pool, k)
            budget -= k
        mutants = sorted(chosen, key=lambda m: (m.file, m.line, m.col, m.op))
    else:
        mutants = candidates
    for i, m in enumerate(mutants, 1):
        m.mid = i

    if args.list:
        for m in mutants:
            print(f"{m.mid:4d} {m.file}:{m.line}:{m.col} {m.op}\n       {m.mutated.strip()}")
        print(f"{len(mutants)} / {len(candidates)} aday")
        return 0

    # _GLIBCXX_ASSERTIONS: std::array/vector operator[] sınır denetimi. Döngü sınırı mutantı
    # (j < 3 -> j < 4) sessiz bellek taşması yerine abort olur ve gerçekten yakalanır.
    code, out = run(
        [
            "cmake",
            "-S",
            "edge",
            "-B",
            args.build_dir,
            "-G",
            "Ninja",
            "-DDELTA_EDGE_BUILD_APP=OFF",
            "-DDELTA_EDGE_COVERAGE=OFF",
            "-DCMAKE_BUILD_TYPE=Debug",
            "-DCMAKE_CXX_FLAGS=-D_GLIBCXX_ASSERTIONS",
        ],
        600,
    )
    if code != 0:
        print(out)
        return 2
    code, out = build(args.build_dir, 1800)
    if code != 0:
        print(out)
        print("özgün kod derlenmedi", file=sys.stderr)
        return 2
    t0 = time.time()
    status, failed = ctest(args.build_dir, args.test_timeout, 1800, args.jobs)
    base_s = time.time() - t0
    if status != "survived":
        print(f"özgün kodda testler geçmiyor: {failed}", file=sys.stderr)
        return 2
    suite_timeout = max(60.0, 10 * base_s)
    print(f"temel test süresi {base_s:.1f} s; {len(mutants)} mutant / {len(candidates)} aday")

    # SIGTERM de finally bloklarını çalıştırsın.
    def on_term(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, on_term)
    out_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        (backup_dir / Path(f).name).write_bytes(originals[f])
    lock.write_text(json.dumps(hashes))

    start = time.time()
    interrupted = False
    try:
        for m in mutants:
            path = root / m.file
            lines = originals[m.file].decode("utf-8").split("\n")
            assert lines[m.line - 1] == m.original
            lines[m.line - 1] = m.mutated
            t = time.time()
            try:
                path.write_text("\n".join(lines), encoding="utf-8")
                code, _ = build(args.build_dir, 600)
                if code is None:
                    m.status = "timeout"
                elif code != 0:
                    m.status = "build_failed"
                else:
                    m.status, m.failed_tests = ctest(
                        args.build_dir, args.test_timeout, suite_timeout, args.jobs
                    )
            finally:
                path.write_bytes(originals[m.file])
            m.seconds = round(time.time() - t, 1)
            print(f"[{m.mid}/{len(mutants)}] {m.status:12s} {m.file}:{m.line} {m.op}", flush=True)
    except KeyboardInterrupt:
        interrupted = True
        print("kesildi; dosyalar geri yükleniyor", file=sys.stderr)
    finally:
        for f in files:
            (root / f).write_bytes(originals[f])
    bad = [f for f in files if sha256(root / f) != hashes[f]]
    if bad:
        print(f"HATA: geri yüklenemedi: {bad} (yedek: {backup_dir})", file=sys.stderr)
        return 3
    lock.unlink(missing_ok=True)
    print("tüm hedef dosyalar özgün SHA-256 ile doğrulandı")
    # Derleme dizini özgün kodla tutarlı kalsın.
    build(args.build_dir, 1800)

    meta = {
        "seed": args.seed,
        "candidates": len(candidates),
        "seconds": round(time.time() - start, 1),
        "interrupted": interrupted,
        "files_restored_sha256": hashes,
    }
    summary = write_reports(out_dir, mutants, meta)
    t = summary["total"]
    print(
        f"killed {t['killed']}, survived {t['survived']}, build_failed {t['build_failed']}, "
        f"timeout {t['timeout']}, skor {t['score']}"
    )
    print(f"rapor: {out_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
