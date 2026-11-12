"""bootstrap.py: başlangıç satırı, bellekte exec, çıkış kodları ve kullanıcıya gösterilen iz."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

BOOTSTRAP = Path(__file__).resolve().parents[2] / "bootstrap.py"


def run(start, extra_stdin: str = "") -> subprocess.CompletedProcess:
    line = start if isinstance(start, str) else json.dumps(start)
    return subprocess.run(
        [sys.executable, "-I", "-u", "-B", str(BOOTSTRAP)],
        input=line + "\n" + extra_stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


def test_runs_code_and_sets_transport():
    r = run({"code": "import os\nprint(os.environ['DELTA_TRANSPORT'], __name__)"})
    assert r.returncode == 0
    assert r.stdout == "stdio __main__\n"


def test_following_stdin_lines_belong_to_user_code():
    r = run({"code": "import sys\nprint(sys.stdin.readline().strip())"}, "ikinci satır\n")
    assert r.stdout == "ikinci satır\n"


def test_exception_traceback_shows_only_user_frames():
    r = run({"code": "x = 1\n\ndef f():\n    raise ValueError('kötü')\nf()\n"})
    assert r.returncode == 1
    assert 'File "<kullanici>", line 5' in r.stderr
    assert 'File "<kullanici>", line 4, in f' in r.stderr
    assert "ValueError: kötü" in r.stderr
    assert "bootstrap" not in r.stderr


def test_syntax_error():
    r = run({"code": "def (:\n"})
    assert r.returncode == 1
    assert "SyntaxError" in r.stderr and "<kullanici>" in r.stderr


@pytest.mark.parametrize(
    "code, status", [("raise SystemExit", 0), ("import sys; sys.exit(3)", 3), ("exit('x')", 1)]
)
def test_system_exit(code, status):
    assert run({"code": code}).returncode == status


@pytest.mark.parametrize("start", ["", "not json", "[]", '{"code": 1}', '{"kod": "x"}'])
def test_invalid_start_line(start):
    r = run(start)
    assert r.returncode == 2
    assert "geçersiz başlangıç" in r.stderr


def test_null_byte_code_is_reported_not_crash():
    assert run({"code": "print(1)\x00"}).returncode == 1


def test_lingering_thread_does_not_block_exit():
    code = "import threading, time\nthreading.Thread(target=time.sleep, args=(60,)).start()"
    assert run({"code": code}).returncode == 0
