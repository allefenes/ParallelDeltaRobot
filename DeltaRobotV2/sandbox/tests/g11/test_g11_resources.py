"""G11 kaynaklar: bellek, süreç sayısı, CPU payı, duvar saati ve çıktı sınırı."""

import subprocess

from harness import job_containers, probe, run_code


def test_G11_cgroup_limits_applied():
    r = probe(
        """
        def read(p):
            return open("/sys/fs/cgroup/" + p).read().strip()
        print(read("memory.max"), read("memory.swap.max"), read("pids.max"), read("cpu.max"))
        """
    )
    assert r.stdout.split() == [str(256 * 2**20), "0", "64", "50000", "100000"]


def test_G11_memory_blowup_killed():
    r = run_code(
        """
        chunks = []
        for i in range(64):          # 64 x 16 MiB = 1 GiB hedef
            chunks.append(bytearray(16 * 2**20))
            print("MiB", (i + 1) * 16, flush=True)
        print("ALLOWED")
        """
    )
    assert "ALLOWED" not in r.stdout
    assert r.exit_code == 137, (r.exit_code, r.stderr)  # SIGKILL (OOM)
    assert r.reason == "error"
    reached = max(int(line.split()[1]) for line in r.stdout.splitlines() if line.startswith("MiB"))
    assert reached <= 256


def test_G11_fork_bomb_contained():
    r = run_code(
        """
        import os, time
        n = 0
        try:
            while n < 10000:
                if os.fork() == 0:
                    time.sleep(30)
                    os._exit(0)
                n += 1
            print("ALLOWED", n)
        except OSError as e:
            print("BLOCKED", n, e.errno)
        """
    )
    word, n, _errno = r.stdout.split()
    assert word == "BLOCKED"
    assert int(n) < 64
    # PID 1 çıkınca çocuklar da ölür; iş hemen biter ve konteyner kalmaz.
    assert (r.exit_code, r.reason) == (0, "ok")
    assert r.elapsed_s < 30
    assert job_containers() == []
    # Ana makine (test konteyneri) hâlâ süreç başlatabiliyor.
    assert subprocess.run(["true"]).returncode == 0


def test_G11_thread_bomb_contained():
    r = probe(
        """
        import threading, time
        n = 0
        try:
            for _ in range(1000):
                threading.Thread(target=time.sleep, args=(5,), daemon=True).start()
                n += 1
            print("ALLOWED", n)
        except RuntimeError:
            print("BLOCKED", n)
        """
    )
    word, n = r.stdout.split()
    assert word == "BLOCKED" and int(n) < 64


def test_G11_cpu_share_throttled():
    r = probe(
        """
        import time
        t0, c0 = time.monotonic(), time.process_time()
        while time.monotonic() - t0 < 3:
            pass
        print(round((time.process_time() - c0) / (time.monotonic() - t0), 2))
        """
    )
    assert float(r.stdout) <= 0.6  # --cpus 0.5 (+ ölçüm payı)


def test_G11_cpu_spin_hits_wall_clock():
    r = run_code("while True:\n    pass\n", timeout_s=5)
    assert r.reason == "timeout"
    assert r.exit_code != 0
    assert 5 <= r.elapsed_s < 15, r.elapsed_s


def test_G11_blocked_read_hits_wall_clock():
    # RPC yanıtı hiç gelmezse kod sonsuza dek bekler; duvar saati keser.
    r = run_code(
        "from delta_robot import Robot\nRobot().state()\n", timeout_s=5, api=lambda msg: None
    )
    assert r.reason == "timeout"
    assert [m["method"] for m in r.rpcs] == ["state"]


def test_G11_output_flood_hits_cap():
    limit = 1024 * 1024
    r = run_code("import sys\nwhile True:\n    sys.stdout.write('x' * 999 + '\\n')\n")
    assert r.reason == "output_limit"
    assert len(r.stdout.encode()) <= limit
    assert len(r.stdout.encode()) > limit - 64 * 1024


def test_G11_stderr_flood_counts_toward_cap():
    r = run_code("import sys\nwhile True:\n    sys.stderr.write('e' * 999 + '\\n')\n")
    assert r.reason == "output_limit"
    assert len(r.stderr.encode()) <= 1024 * 1024


def test_G11_single_huge_line_hits_cap():
    r = run_code("import sys\nsys.stdout.write('y' * 5_000_000)\nimport time\ntime.sleep(60)\n")
    assert r.reason == "output_limit"
    assert len(r.stdout.encode()) <= 1024 * 1024
    assert r.elapsed_s < 30


def test_G11_rpc_flood_counts_toward_cap():
    # Yanıt beklemeden basılan RPC satırları da çıktı bütçesinden düşer; API'ye taşmaz.
    r = run_code(
        """
        import json, sys
        i = 0
        while True:
            i += 1
            sys.stdout.write("\\x1eDELTA " + json.dumps({"id": i, "method": "state"}) + "\\n")
        """,
        api=lambda msg: None,
    )
    assert r.reason == "output_limit"
    assert len(r.rpcs) <= 16  # bekleyen istek sınırı


def test_G11_cancel_stops_job():
    r = run_code("import time\ntime.sleep(60)\n", cancel_after_s=2)
    assert r.reason == "cancelled"
    assert r.elapsed_s < 15
