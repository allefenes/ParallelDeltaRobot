"""stdio satır protokolü ayrıştırıcısı, çıktı bütçesi ve API mesaj doğrulaması."""

import json

import pytest
from delta_runner.protocol import (
    Output,
    OutputBudget,
    ProtocolError,
    RpcInvalid,
    RpcRequest,
    StdoutDemux,
    encode_rpc_reply,
    encode_start,
    exit_message,
    parse_api_message,
    parse_rpc,
    rpc_message,
)

P = b"\x1eDELTA "


def rpc_line(obj) -> bytes:
    return P + json.dumps(obj).encode() + b"\n"


def test_plain_lines_are_output():
    d = StdoutDemux()
    assert d.feed(b"merhaba\ndunya\n") == [Output("merhaba\ndunya\n")]


def test_rpc_line_is_split_from_output():
    d = StdoutDemux()
    evs = d.feed(b"a\n" + rpc_line({"id": 1, "method": "move", "params": {"x": 1}}) + b"b\n")
    assert evs == [Output("a\n"), RpcRequest(1, "move", {"x": 1}), Output("b\n")]


def test_partial_chunks_reassembled():
    d = StdoutDemux()
    line = rpc_line({"id": 7, "method": "state"})
    assert d.feed(line[:5]) == []
    assert d.feed(line[5:12]) == []
    assert d.feed(line[12:]) == [RpcRequest(7, "state", {})]


def test_prefix_mid_line_after_unterminated_print():
    d = StdoutDemux()
    evs = d.feed(b"puan: " + rpc_line({"id": 2, "method": "stop", "params": {}}))
    assert evs == [Output("puan: "), RpcRequest(2, "stop", {})]


def test_utf8_split_across_chunks():
    d = StdoutDemux()
    data = "çğüşöı\n".encode()
    out = d.feed(data[:1]) + d.feed(data[1:3]) + d.feed(data[3:])
    assert "".join(e.data for e in out) == "çğüşöı\n"


def test_invalid_utf8_replaced():
    d = StdoutDemux()
    assert d.feed(b"\xff\xfe\n") == [Output("��\n")]


def test_overlong_unterminated_line_flushed_as_output():
    d = StdoutDemux(max_line=16)
    assert d.feed(b"x" * 20) == [Output("x" * 20)]
    assert d.feed(b"\n") == [Output("\n")]


def test_overlong_rpc_line_is_not_rpc():
    d = StdoutDemux(max_line=16)
    evs = d.feed(P + b'{"id": 1, "method": "state", "params": {}}')
    assert evs and all(isinstance(e, Output) for e in evs)


def test_close_flushes_tail_as_output():
    d = StdoutDemux()
    assert d.feed(b"son") == []
    assert d.close() == [Output("son")]


def test_crlf_rpc_line():
    d = StdoutDemux()
    assert d.feed(P + b'{"id": 3, "method": "robot"}\r\n') == [RpcRequest(3, "robot", {})]


@pytest.mark.parametrize(
    "payload, expect_id",
    [
        (b"not json", None),
        (b"[1, 2]", None),
        (b'{"method": "move"}', None),
        (b'{"id": true, "method": "move"}', None),
        (b'{"id": "' + b"x" * 65 + b'", "method": "move"}', None),
        (b'{"id": 4, "method": "shell"}', 4),
        (b'{"id": 5, "method": "move", "params": [1]}', 5),
        (b'{"id": 6, "method": "move", "params": {"x": NaN}}', None),
        (b"[" * 100000 + b"]" * 100000, None),  # özyineleme bombası
    ],
)
def test_invalid_rpc(payload, expect_id):
    r = parse_rpc(payload)
    assert isinstance(r, RpcInvalid)
    assert r.id == expect_id


def test_all_contract_methods_accepted():
    for m in ("robot", "state", "move", "magnet", "torque", "stop"):
        assert parse_rpc(json.dumps({"id": "a", "method": m}).encode()) == RpcRequest("a", m, {})


def test_null_params_become_empty():
    assert parse_rpc(b'{"id": 1, "method": "stop", "params": null}').params == {}


def test_budget_accounting():
    b = OutputBudget(10)
    assert b.take(4) == 4 and not b.exceeded
    assert b.take(6) == 6 and not b.exceeded  # tam sınır aşım değil
    assert b.take(1) == 0 and b.exceeded
    assert b.used == 10
    assert b.take(5) == 0


def test_budget_partial_take():
    b = OutputBudget(10)
    assert b.take(15) == 10
    assert b.exceeded


def test_encode_start_is_single_line():
    line = encode_start("print('a')\nprint('b')\n")
    assert line.endswith(b"\n") and line.count(b"\n") == 1
    assert json.loads(line) == {"code": "print('a')\nprint('b')\n"}


def test_encode_rpc_reply():
    assert json.loads(encode_rpc_reply(1, result={"ok": True})) == {"id": 1, "result": {"ok": True}}
    err = {"code": "busy", "message": "m"}
    assert json.loads(encode_rpc_reply("a", error=err)) == {"id": "a", "error": err}
    assert encode_rpc_reply(1, result={"s": "a\nb"}).count(b"\n") == 1


def test_parse_api_messages():
    start = {"type": "start", "job_id": "j", "code": "", "secret": "s"}
    assert parse_api_message(json.dumps(start)) == start
    assert parse_api_message('{"type": "cancel"}') == {"type": "cancel"}
    r = {"type": "rpc_result", "id": 1, "result": {}}
    assert parse_api_message(json.dumps(r)) == r
    e = {"type": "rpc_result", "id": 1, "error": {"code": "busy", "message": "m"}}
    assert parse_api_message(json.dumps(e)) == e


@pytest.mark.parametrize(
    "msg",
    [
        "x",
        "[]",
        '{"type": "exec"}',
        '{"type": "start", "job_id": "j", "code": "c"}',
        '{"type": "start", "job_id": "", "code": "c", "secret": "s"}',
        '{"type": "start", "job_id": "j", "code": 1, "secret": "s"}',
        '{"type": "rpc_result", "id": 1}',
        '{"type": "rpc_result", "id": 1, "result": {}, "error": {}}',
        '{"type": "rpc_result", "id": 1, "error": "x"}',
        '{"type": "rpc_result", "id": null, "result": {}}',
    ],
)
def test_parse_api_rejects(msg):
    with pytest.raises(ProtocolError):
        parse_api_message(msg)


def test_outgoing_messages():
    assert rpc_message(RpcRequest(1, "move", {"x": 1})) == {
        "type": "rpc",
        "id": 1,
        "method": "move",
        "params": {"x": 1},
    }
    assert exit_message(0, "ok") == {"type": "exit", "exit_code": 0, "reason": "ok"}
    with pytest.raises(ValueError):
        exit_message(0, "bilinmeyen")
