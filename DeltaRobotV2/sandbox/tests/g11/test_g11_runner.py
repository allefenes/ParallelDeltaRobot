"""G11 koşucu yolu: RPC gidiş-dönüşü (sahte API), WebSocket sunucusu, kimlik doğrulama, tek iş."""

import asyncio
import json
import textwrap

import pytest
from delta_runner.server import Runner
from harness import fake_api, job_containers, make_config, probe, run_code
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed, InvalidStatus

SECRET = "test-gizli-anahtar"

RAW_RPC = r"""
import json, sys
sys.stdout.write("önce\n")
sys.stdout.write("\x1eDELTA " + json.dumps({"id": 1, "method": "state", "params": {}}) + "\n")
sys.stdout.flush()
reply = json.loads(sys.stdin.readline())
print("YANIT", reply["id"], reply["result"]["state"])
"""


def test_G11_rpc_roundtrip_raw_protocol():
    r = probe(RAW_RPC)
    assert [(m["id"], m["method"], m["params"]) for m in r.rpcs] == [(1, "state", {})]
    assert r.stdout == "önce\nYANIT 1 IDLE\n"
    assert "\x1e" not in r.stdout


def test_G11_rpc_roundtrip_client_library():
    r = probe(
        """
        from delta_robot import Robot
        robot = Robot()
        print(robot.transport_name, robot.info()["name"])
        res = robot.move_to(20, 10, -200)
        print("accepted", res.accepted)
        print("magnet", robot.magnet(True))
        print("state", robot.state().state)
        robot.stop()
        """
    )
    assert [m["method"] for m in r.rpcs] == ["robot", "move", "magnet", "state", "stop"]
    move = r.rpcs[1]["params"]
    assert (move["x"], move["y"], move["z"], move["wait"]) == (20, 10, -200, True)
    assert r.stdout.splitlines() == [
        "stdio Delta Robotics V2",
        "accepted True",
        "magnet True",
        "state IDLE",
    ]


def test_G11_rpc_error_reaches_user_code():
    def busy(msg):
        return {"error": {"code": "busy", "message": "başka iş çalışıyor"}}

    r = run_code(
        """
        from delta_robot import Robot
        try:
            Robot().move_to(0, 0, -200)
        except Exception as e:
            print("HATA", type(e).__name__)
        """,
        api=busy,
    )
    assert (r.exit_code, r.reason) == (0, "ok"), r.stderr
    assert r.stdout.startswith("HATA")


def test_G11_invalid_rpc_method_rejected_locally():
    # Sözleşme dışı yöntem API'ye hiç iletilmez; kullanıcıya bad_request döner.
    r = probe(
        r"""
        import json, sys
        req = json.dumps({"id": 9, "method": "shell", "params": {}})
        sys.stdout.write("\x1eDELTA " + req + "\n")
        print(json.loads(sys.stdin.readline())["error"]["code"])
        """
    )
    assert r.rpcs == []
    assert r.stdout.strip() == "bad_request"


def test_G11_user_exception_reported_with_exit_code():
    r = run_code("def f():\n    raise RuntimeError('kasıtlı')\nf()\n")
    assert (r.exit_code, r.reason) == (1, "error")
    assert 'File "<kullanici>", line 3' in r.stderr
    assert "RuntimeError: kasıtlı" in r.stderr


# WebSocket sunucusu (api.md: ws://runner:8100/run)


async def _serve(runner):
    return await serve(runner.handle, "127.0.0.1", 0, process_request=runner.process_request)


async def _drive(uri, start, answer=fake_api, cancel_after_s=None):
    """Sahte API istemcisi: başlatır, RPC'leri yanıtlar, exit'e kadar mesajları toplar."""
    msgs = []
    async with connect(uri) as ws:
        await ws.send(json.dumps(start))
        if cancel_after_s is not None:

            async def later():
                await asyncio.sleep(cancel_after_s)
                await ws.send(json.dumps({"type": "cancel"}))

            asyncio.create_task(later())
        async for raw in ws:
            msg = json.loads(raw)
            msgs.append(msg)
            if msg["type"] == "rpc":
                reply = {"type": "rpc_result", "id": msg["id"], **answer(msg)}
                await ws.send(json.dumps(reply))
            if msg["type"] == "exit":
                break
    return msgs


def _start(code, secret=SECRET, job_id="job-ws"):
    return {"type": "start", "job_id": job_id, "code": textwrap.dedent(code), "secret": secret}


def _ws_test(coro_fn, **limits):
    async def main():
        runner = Runner(make_config(**limits), SECRET)
        server = await _serve(runner)
        port = server.sockets[0].getsockname()[1]
        try:
            return await coro_fn(f"ws://127.0.0.1:{port}")
        finally:
            server.close()
            await server.wait_closed()

    return asyncio.run(main())


def test_G11_ws_rpc_roundtrip():
    msgs = _ws_test(lambda base: _drive(base + "/run", _start(RAW_RPC)))
    kinds = [m["type"] for m in msgs]
    assert kinds[-1] == "exit" and msgs[-1] == {"type": "exit", "exit_code": 0, "reason": "ok"}
    assert {"type": "rpc", "id": 1, "method": "state", "params": {}} in msgs
    out = "".join(m["data"] for m in msgs if m["type"] == "stdout")
    assert out == "önce\nYANIT 1 IDLE\n"


def test_G11_ws_wrong_secret_rejected_without_container():
    async def go(base):
        async with connect(base + "/run") as ws:
            await ws.send(json.dumps(_start("print(1)", secret="yanlis")))
            with pytest.raises(ConnectionClosed) as exc:
                await ws.recv()
            return exc.value.rcvd.code

    assert _ws_test(go) == 1008
    assert job_containers() == []


def test_G11_ws_wrong_path_404():
    async def go(base):
        with pytest.raises(InvalidStatus) as exc:
            async with connect(base + "/baska"):
                pass
        return exc.value.response.status_code

    assert _ws_test(go) == 404


def test_G11_ws_one_job_at_a_time():
    async def go(base):
        first = asyncio.create_task(_drive(base + "/run", _start("import time; time.sleep(3)")))
        await asyncio.sleep(1)
        second = await _drive(base + "/run", _start("print('ikinci')", job_id="job-2"))
        return await first, second

    first, second = _ws_test(go)
    assert first[-1]["reason"] == "ok"
    assert second[-1] == {"type": "exit", "exit_code": -1, "reason": "error"}


def test_G11_ws_cancel():
    msgs = _ws_test(
        lambda base: _drive(base + "/run", _start("import time; time.sleep(60)"), cancel_after_s=2)
    )
    assert msgs[-1]["reason"] == "cancelled"


def test_G11_ws_api_disconnect_kills_container():
    async def go(base):
        async with connect(base + "/run") as ws:
            await ws.send(json.dumps(_start("import time; time.sleep(60)")))
            await asyncio.sleep(2)
        # Bağlantı koptu: koşucu işi iptal edip konteyneri silmeli.
        for _ in range(40):
            await asyncio.sleep(0.5)
            if not job_containers():
                return True
        return False

    assert _ws_test(go)


def test_G11_ws_timeout_override():
    msgs = _ws_test(
        lambda base: _drive(base + "/run", _start("while True:\n    pass\n")), timeout_s=3
    )
    assert msgs[-1]["reason"] == "timeout"
