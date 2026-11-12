"""Sandbox giriş noktası: ilk stdin satırındaki kullanıcı kodunu bellekte çalıştırır.

Başlangıç satırı `{"code": "..."}`. Kod `/tmp`'ye yazılmaz; `<kullanici>` dosya adıyla derlenip
taze bir `__main__` ad alanında `exec` edilir. Sonraki stdin satırları istemcinin (`delta_robot`)
stdio taşımasına aittir. Çıkış kodu: 0 başarı, 1 yakalanmamış istisna, 2 geçersiz başlangıç
mesajı, `sys.exit(n)` ile n.
"""

from __future__ import annotations

import json
import os
import sys
import traceback

USER_FILENAME = "<kullanici>"


def _read_start() -> str | None:
    line = sys.stdin.readline()
    try:
        msg = json.loads(line)
    except ValueError:
        return None
    if not isinstance(msg, dict) or not isinstance(msg.get("code"), str):
        return None
    return msg["code"]


def _exit_code(exc: SystemExit) -> int:
    code = exc.code
    if code is None:
        return 0
    if isinstance(code, int) and not isinstance(code, bool):
        return code
    print(code, file=sys.stderr)
    return 1


def _print_user_traceback(exc: BaseException) -> None:
    # İlk çerçeve bootstrap'in kendisi; kullanıcıya yalnız kendi kodu gösterilir.
    tb = exc.__traceback__
    if tb is not None and tb.tb_frame.f_code.co_filename == __file__:
        tb = tb.tb_next
    traceback.print_exception(type(exc), exc, tb, file=sys.stderr)


def main() -> int:
    code = _read_start()
    if code is None:
        print("sandbox: geçersiz başlangıç mesajı", file=sys.stderr)
        return 2
    os.environ["DELTA_TRANSPORT"] = "stdio"
    try:
        compiled = compile(code, USER_FILENAME, "exec")
    except (SyntaxError, ValueError) as exc:
        traceback.print_exception(type(exc), exc, None, file=sys.stderr)
        return 1
    namespace = {"__name__": "__main__", "__builtins__": __builtins__}
    try:
        exec(compiled, namespace)
    except SystemExit as exc:
        return _exit_code(exc)
    except BaseException as exc:  # noqa: B036 - KeyboardInterrupt dahil her şey kullanıcıya gösterilir
        _print_user_traceback(exc)
        return 1
    return 0


if __name__ == "__main__":
    status = main()
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    finally:
        # os._exit: kullanıcı iş parçacıkları ya da atexit kancaları çıkışı geciktiremez.
        os._exit(status if 0 <= status <= 255 else 1)
