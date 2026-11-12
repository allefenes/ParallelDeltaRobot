"""F4 uçtan uca senaryoları: gerçek istemci (delta_robot) -> API -> ROS2 yığını -> sanal Pi.

tools/e2e_f4.sh çalıştırır; istemci API ile aynı ağ ad alanında (https://localhost:8000, yerel CA).
Her senaryo "[ad] GEÇTİ/KALDI: ayrıntı" satırı yazar; çıkış kodu başarısız senaryo sayısıdır.
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

from delta_robot import AuthError, CommandRejected, Robot, RobotBusy

URL = os.environ.get("DELTA_URL", "https://localhost:8000")
TOKEN = os.environ["DELTA_TOKEN"]
CA = os.environ.get("DELTA_CA_FILE", "/certs/ca.crt")
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str) -> bool:
    results.append((name, ok, detail))
    print(f"[{name}] {'GEÇTİ' if ok else 'KALDI'}: {detail}", flush=True)
    return ok


def http(method: str, path: str, body: dict | None = None, token: str = TOKEN):
    ctx = ssl.create_default_context(cafile=CA)
    req = urllib.request.Request(
        f"{URL}{path}",
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def wait_state(robot: Robot, cond, timeout: float = 15.0):
    end = time.monotonic() + timeout
    s = robot.state()
    while time.monotonic() < end:
        s = robot.state()
        if cond(s):
            return s
        time.sleep(0.1)
    return s


def run_job(code: str, timeout: float = 90.0) -> dict:
    st, j = http("POST", "/api/v1/jobs", {"code": code, "name": "e2e"})
    assert st == 202, (st, j)
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        _, job = http("GET", f"/api/v1/jobs/{j['job_id']}")
        if job["status"] in ("done", "failed", "timeout", "cancelled"):
            return job
        time.sleep(0.2)
    return job


def wait_api(timeout: float = 120.0) -> bool:
    """API ayağa kalkana kadar /health yoklanır (uvicorn + ROS düğümü birkaç saniye sürer)."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            if http("GET", "/api/v1/health")[0] == 200:
                return True
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(1.0)
    return False


def scenario_tictactoe(robot: Robot, max_moves: int = 12) -> None:
    """F4.5 senaryo regresyonu: iki minimaks oyuncu gerçek yığında (ROS + sanal Pi) oynar.

    Metrikler SCENARIO_METRICS satırıyla basılır; e2e_f4.sh datasheet için dosyaya yazar.
    """
    from delta_server.board_game import apply_move, best_move, initial_cells, winner

    robot.torque(True)
    robot.move_to(0, 0, -185)
    robot.reset_board()
    cells, turn, moves, t0 = initial_cells(), "X", 0, time.monotonic()
    consistent = True
    cycle_s: list[float] = []
    while winner(cells) is None and moves < max_moves:
        m = best_move(cells, turn, depth=4)
        if m is None:
            break
        t_move = time.monotonic()
        robot.pick_place(*m)
        cycle_s.append(time.monotonic() - t_move)
        cells = apply_move(cells, m)
        if robot.board()["cells"] != cells:
            consistent = False
            break
        turn, moves = ("O" if turn == "X" else "X"), moves + 1
    board = robot.board()
    met = board["metrics"]
    check("F4.5 oyun: ikiz kurallarla uyumlu", consistent, f"{moves} hamle, tabla {board['cells']}")
    check(
        "F4.5 al/bırak hatasız",
        met["dropped"] == met["missed_picks"] == met["off_board"] == 0
        and met["picks"] == met["places"] == moves,
        f"{met}",
    )
    err = met["placement_error_max_mm"]
    check("F4.5 yerleştirme hatası < 1 mm", err is not None and err < 1.0, f"en çok {err} mm")
    summary = {
        "moves": moves,
        "winner": board["winner"],
        "total_s": round(time.monotonic() - t0, 2),
        "cycle_mean_s": round(sum(cycle_s) / len(cycle_s), 2) if cycle_s else None,
        "cycle_max_s": round(max(cycle_s), 2) if cycle_s else None,
        **met,
    }
    print("SCENARIO_METRICS " + json.dumps(summary), flush=True)


def main() -> int:
    if not check("API ayakta (TLS)", wait_api(), URL):
        return 1
    robot = Robot(URL, token=TOKEN, verify=CA)

    # Bağlantı ve kimlik
    s = wait_state(robot, lambda s: s.state == "IDLE" and s.edge_connected, 60.0)
    check("Hazır (TLS, kenar bağlı)", s.state == "IDLE", f"durum {s.state}")
    try:
        Robot(URL, token="yanlis-belirtec-0000000000", verify=CA).state()
        check("Belirteç denetimi", False, "yanlış belirteç kabul edildi")
    except AuthError:
        check("Belirteç denetimi", True, "yanlış belirteç 401")
    info = robot.info()
    check(
        "Robot tanımı",
        info["workspace"]["z_bottom_mm"] == -221.0,
        f"çalışma alanı {info['workspace']}",
    )

    # Hareket ve kapılar
    r = robot.move_to(20, 10, -200)
    p = r.position_mm or [0, 0, 0]
    ok = r.done and all(abs(a - b) < 0.5 for a, b in zip(p, (20, 10, -200), strict=True))
    check("Hareket (istemci -> API -> ROS -> Pi)", ok, f"{r}")
    for name, target, req in (
        ("G3 erişilemez hedef reddi", (0, 0, -320), "G3"),
        ("G2 rot başı limiti reddi", (60, 0, -140), "G2"),
        ("G14 mıknatıs ucu tabla altına reddi", (0, 0, -228), "G14"),
    ):
        try:
            robot.move_to(*target)
            check(name, False, "kabul edildi")
        except CommandRejected as e:
            check(name, e.requirement == req, f"{e.requirement}: {e.reason}")
    st, body = http("POST", "/api/v1/move", {"x": 0, "y": 0, "z": -200, "duration_s": -1})
    check("G4 biçim reddi (API)", st == 400, f"{st} {body}")

    # Mıknatıs: durum kenar telemetrisinden gelir
    robot.magnet(True)
    s = wait_state(robot, lambda s: s.magnet)
    check("Mıknatıs açık (kenar telemetrisi)", s.magnet, f"magnet={s.magnet}")
    robot.magnet(False)
    s = wait_state(robot, lambda s: not s.magnet)
    check("Mıknatıs kapalı", not s.magnet, f"magnet={s.magnet}")

    # Dur -> HOLDING, tork aç -> IDLE
    robot.move_to(0, 0, -180, duration=3.0, wait=False)
    wait_state(robot, lambda s: s.state == "RUNNING", 5.0)
    robot.stop()
    s = wait_state(robot, lambda s: s.state == "HOLDING", 5.0)
    check("Dur komutu hareketi keser (HOLDING)", s.state == "HOLDING", f"durum {s.state}")
    robot.torque(True)
    s = wait_state(robot, lambda s: s.state == "IDLE", 5.0)
    check("Tork aç ile IDLE", s.state == "IDLE", f"durum {s.state}")

    # Sandbox işi: istemcinin stdio taşıması üzerinden aynı komutlar
    job = run_job(
        "from delta_robot import Robot\n"
        "r = Robot()\n"
        "print('baslangic', r.state().state)\n"
        "r.move_to(-15, 15, -205)\n"
        "print('konum', [round(v) for v in r.state().position_mm])\n"
    )
    check(
        "Sandbox işi robotu sürer",
        job["status"] == "done" and "konum [-15, 15, -205]" in job["output"],
        f"{job['status']}: {job['output'][-200:]!r} {job.get('reason')}",
    )

    # Kontrol kilidi: iş sürerken doğrudan komut 409, dur her zaman kabul
    st, j = http("POST", "/api/v1/jobs", {"code": "import time\ntime.sleep(4)\n"})
    time.sleep(1.5)
    try:
        robot.move_to(0, 0, -200)
        check("Kontrol kilidi (409)", False, "iş sürerken komut kabul edildi")
    except RobotBusy as e:
        check("Kontrol kilidi (409)", e.job_id == j["job_id"], f"meşgul: {e.job_id}")
    run_job("pass")  # kuyruktaki iş bitince kilit kalkar

    # G11: sandbox ağa çıkamaz (API'ye, kenara, dışarıya)
    job = run_job(
        "import socket\n"
        "for h, p in (('localhost', 8000), ('server', 8443), ('1.1.1.1', 443)):\n"
        "    try:\n"
        "        socket.create_connection((h, p), timeout=2); print('ACIK', h)\n"
        "    except OSError as e:\n"
        "        print('kapali', h, type(e).__name__)\n"
    )
    check(
        "G11 sandbox ağsız (uçtan uca)",
        job["status"] == "done"
        and "ACIK" not in job["output"]
        and job["output"].count("kapali") == 3,
        job["output"].strip(),
    )
    job = run_job("while True:\n    pass\n", timeout=200)
    check("G11 sonsuz döngü zaman aşımı", job["status"] == "timeout", f"{job['status']}")
    s = wait_state(robot, lambda s: s.state in ("HOLDING", "IDLE"), 5.0)
    robot.torque(True)

    # Telemetri akışı (WS)
    n = 0
    t0 = time.monotonic()
    for _s in robot.telemetry():
        n += 1
        if time.monotonic() - t0 > 1.0:
            break
    check("Telemetri akışı (WS)", n >= 10, f"1 s'de {n} durum")

    scenario_tictactoe(robot)

    failed = [r for r in results if not r[1]]
    print(f"\n== Sonuç: {len(results) - len(failed)} geçti, {len(failed)} başarısız ==")
    return len(failed)


if __name__ == "__main__":
    sys.exit(main())
