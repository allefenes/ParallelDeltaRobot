"""API sözleşme testleri (docs/api.md): sahte arka uç ve sahte sandbox koşucusuyla, ROS'suz."""

from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
from pathlib import Path

import pytest
import websockets
import yaml
from fastapi.testclient import TestClient

from delta_api.app import create_app
from delta_api.auth import Tokens
from delta_api.backend import FakeBackend, MoveOutcome, requirement_of

ROOT = Path(__file__).resolve().parents[2]
TOKEN = "test-belirteci-0123456789"
OTHER = "baska-belirtec-0123456789"
H = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def spec():
    return yaml.safe_load((ROOT / "config" / "robot.yaml").read_text(encoding="utf-8"))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class FakeRunner:
    """Koşucu taklidi: 'start' gelince betikteki adımları oynatır (rpc, stdout, exit)."""

    def __init__(self, script):
        self.script = script
        self.port = _free_port()
        self.received: list[dict] = []
        self.loop = asyncio.new_event_loop()
        self.ready = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()
        self.ready.wait(5)

    @property
    def url(self) -> str:
        return f"ws://127.0.0.1:{self.port}/run"

    def _run(self):
        asyncio.set_event_loop(self.loop)

        async def main():
            async with websockets.serve(self._handler, "127.0.0.1", self.port):
                self.ready.set()
                await asyncio.Future()

        self.loop.run_until_complete(main())

    async def _handler(self, ws, *_):
        start = json.loads(await ws.recv())
        self.received.append(start)
        for step in self.script:
            if step[0] == "rpc":
                await ws.send(json.dumps({"type": "rpc", "id": step[1], "method": step[2],
                                          "params": step[3]}))  # fmt: skip
                self.received.append(json.loads(await ws.recv()))
            elif step[0] == "out":
                await ws.send(json.dumps({"type": "stdout", "data": step[1]}))
            elif step[0] == "wait_cancel":
                self.received.append(json.loads(await ws.recv()))
                await ws.send(json.dumps({"type": "exit", "exit_code": -9, "reason": "cancelled"}))
                return
            elif step[0] == "sleep":
                await asyncio.sleep(step[1])
            elif step[0] == "exit":
                await ws.send(json.dumps({"type": "exit", "exit_code": step[1],
                                          "reason": step[2]}))  # fmt: skip
                return


def make_client(spec, runner_url="ws://127.0.0.1:1/run", tmp_path=None):
    backend = FakeBackend(spec, speed_mm_s=2000.0)
    tokens = Tokens({"enes": TOKEN, "misafir": OTHER})
    web = None
    if tmp_path is not None:
        web = tmp_path / "web"
        web.mkdir()
        (web / "index.html").write_text("<h1>Delta</h1>", encoding="utf-8")
    app = create_app(backend, tokens, runner_url=runner_url, runner_secret="s", web_dir=web,
                     i18n_dir=ROOT / "i18n" / "locales")  # fmt: skip
    return TestClient(app), backend


def wait_job(c, jid, timeout=5.0):
    t_end = time.monotonic() + timeout
    while time.monotonic() < t_end:
        j = c.get(f"/api/v1/jobs/{jid}", headers=H).json()
        if j["status"] in ("done", "failed", "timeout", "cancelled"):
            return j
        time.sleep(0.02)
    raise AssertionError(f"iş bitmedi: {j}")


# --- kimlik ve temel uç noktalar ---------------------------------------------------------------


def test_health_without_token(spec):
    c, _ = make_client(spec)
    with c:
        r = c.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "edge_connected": True, "version": "v1"}


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer yanlis"}, {"Authorization": TOKEN}]
)
def test_unauthorized(spec, headers):
    c, b = make_client(spec)
    with c:
        for method, path in (("get", "/state"), ("post", "/move"), ("post", "/stop")):
            r = c.request(method.upper(), f"/api/v1{path}", headers=headers, json={})
            assert r.status_code == 401
            assert r.json()["error"] == "unauthorized"
    assert b.commands == []


def test_robot_info_from_yaml(spec):
    c, _ = make_client(spec)
    with c:
        info = c.get("/api/v1/robot", headers=H).json()
    k = spec["kinematics"]
    assert info["geometry"]["L2"] == k["forearm_length"]
    assert info["limits"]["rod_tilt_max_deg"] == k["spherical_joint_limit"]
    assert info["limits"]["motor_min_deg"] == k["motor_limit_min"]
    assert info["workspace"]["cylinder_diameter_mm"] == 82.0
    # G14: P'nin alt sınırı tabla üstü + uç uzaklığı (-240 + 4 + 15 = -221)
    z_min = -k["base_to_floor"] + spec["task"]["board_thickness"] + k["ee_offset"]
    assert info["workspace"]["z_bottom_mm"] == z_min
    assert info["limits"]["min_tool_z_mm"] == z_min - k["ee_offset"]
    assert info["geometry"]["rod_spacing_mm"] == spec["joint_stack"]["rod_spacing"]
    assert info["home_mm"] == [0.0, 0.0, -200.0]


def test_state_shape(spec):
    c, _ = make_client(spec)
    with c:
        s = c.get("/api/v1/state", headers=H).json()
    assert set(s) == {"state", "angles_deg", "position_mm", "magnet", "temps_c", "loads",
                      "voltages", "trajectory_id", "edge_connected", "job_id"}  # fmt: skip
    assert s["state"] == "IDLE" and s["job_id"] is None


# --- hareket ve komutlar ------------------------------------------------------------------------


def test_move_accepted_and_done(spec):
    c, _ = make_client(spec)
    with c:
        r = c.post("/api/v1/move", headers=H, json={"x": 20, "y": 10, "z": -200})
    body = r.json()
    assert r.status_code == 200
    assert body["accepted"] and body["done"]
    assert body["position_mm"] == pytest.approx([20, 10, -200])
    assert body["trajectory_id"].startswith("traj-")


def test_move_rejected_is_200_with_requirement(spec):
    c, _ = make_client(spec)
    with c:
        r = c.post("/api/v1/move", headers=H, json={"x": 0, "y": 0, "z": -300})
    assert r.status_code == 200
    assert r.json()["accepted"] is False and r.json()["requirement"] == "G3"


def test_move_no_wait(spec):
    c, _ = make_client(spec)
    with c:
        r = c.post("/api/v1/move", headers=H, json={"x": 0, "y": 0, "z": -220, "wait": False})
    assert r.json()["accepted"] and r.json()["done"] is False


@pytest.mark.parametrize(
    "body",
    [
        {"x": 0, "y": 0},
        {"x": "1", "y": 0, "z": -200},
        {"x": True, "y": 0, "z": -200},
        {"x": 0, "y": 0, "z": -200, "duration_s": 0},
        {"x": 0, "y": 0, "z": -200, "duration_s": 61},
        {"x": 0, "y": 0, "z": -200, "wait": "evet"},
    ],
)
def test_move_bad_request(spec, body):
    c, b = make_client(spec)
    with c:
        r = c.post("/api/v1/move", headers=H, json=body)
    assert r.status_code == 400 and r.json()["error"] == "bad_request"
    assert b.commands == []


@pytest.mark.parametrize("raw", ["{bozuk", "[1,2]", '{"x": NaN, "y": 0, "z": -200}',
                                 '{"x": Infinity, "y": 0, "z": -200}'])  # fmt: skip
def test_move_non_finite_or_malformed_rejected_G4(spec, raw):
    c, b = make_client(spec)
    with c:
        r = c.post("/api/v1/move", headers={**H, "content-type": "application/json"}, content=raw)
    assert r.status_code == 400
    assert b.commands == []


def test_magnet_torque_stop(spec):
    c, b = make_client(spec)
    with c:
        assert c.post("/api/v1/magnet", headers=H, json={"on": True}).json() == {
            "ok": True,
            "magnet": True,
        }
        assert c.get("/api/v1/state", headers=H).json()["magnet"] is True
        assert c.post("/api/v1/magnet", headers=H, json={"on": 1}).status_code == 400
        assert c.post("/api/v1/stop", headers=H).json() == {"ok": True}
        assert c.post("/api/v1/torque", headers=H, json={"on": False}).json() == {"ok": True}
        s = c.get("/api/v1/state", headers=H).json()
        assert s["state"] == "TORQUE_OFF" and s["magnet"] is False
    assert ("stop",) in b.commands


def test_disconnected_robot_is_503(spec):
    c, b = make_client(spec)
    b.state().state = "DISCONNECTED"
    with c:
        r = c.post("/api/v1/move", headers=H, json={"x": 0, "y": 0, "z": -200})
    assert r.status_code == 503 and r.json()["error"] == "robot_unavailable"


def test_unknown_route_404(spec):
    c, _ = make_client(spec)
    with c:
        r = c.get("/api/v1/yok", headers=H)
    assert r.status_code == 404 and r.json()["error"] == "not_found"


def test_static_web_and_i18n(spec, tmp_path):
    c, _ = make_client(spec, tmp_path=tmp_path)
    with c:
        assert "Delta" in c.get("/").text
        assert c.get("/i18n/tr.json").json()["app.title"] == "Delta Robotics"


# --- telemetri ----------------------------------------------------------------------------------


def test_telemetry_ws_requires_token(spec):
    c, _ = make_client(spec)
    with c, pytest.raises(Exception):  # noqa: B017 - kapanış istemcide istisna olarak görülür
        with c.websocket_connect("/api/v1/ws/telemetry?token=yanlis") as ws:
            ws.receive_json()


def test_telemetry_ws_states_and_events(spec):
    c, _ = make_client(spec)
    with c, c.websocket_connect(f"/api/v1/ws/telemetry?token={TOKEN}") as ws:
        first = ws.receive_json()
        assert first["type"] == "state" and first["state"] == "IDLE"
        c.post("/api/v1/move", headers=H, json={"x": 0, "y": 0, "z": -300})  # G3 reddi
        for _ in range(50):
            m = ws.receive_json()
            if m["type"] == "event":
                break
        assert m == {"type": "event", "accepted": False, "requirement": "G3",
                     "reason": m["reason"], "trajectory_id": ""}  # fmt: skip


# --- işler (sandbox koşucusu ile) ---------------------------------------------------------------


def test_job_rpc_roundtrip_and_lock(spec):
    runner = FakeRunner(
        [
            ("out", "merhaba\n"),
            ("rpc", 1, "state", {}),
            ("rpc", 2, "move", {"x": 10, "y": 0, "z": -210}),
            ("rpc", 3, "move", {"x": 0, "y": 0, "z": -400}),
            ("rpc", 4, "magnet", {"on": "evet"}),
            ("rpc", 5, "sil", {}),
            ("sleep", 0.3),
            ("exit", 0, "ok"),
        ]
    )
    c, _ = make_client(spec, runner.url)
    with c:
        jid = c.post("/api/v1/jobs", headers=H, json={"code": "print('merhaba')"}).json()["job_id"]
        time.sleep(0.15)
        # Kontrol kilidi: iş çalışırken doğrudan komut 409, dur her zaman kabul.
        r = c.post("/api/v1/move", headers=H, json={"x": 0, "y": 0, "z": -200})
        assert r.status_code == 409 and r.json()["job_id"] == jid
        assert c.get("/api/v1/state", headers=H).json()["job_id"] == jid
        job = wait_job(c, jid)
    assert job["status"] == "done" and job["exit_code"] == 0
    assert "merhaba" in job["output"]
    start, *replies = runner.received
    assert start["type"] == "start" and start["secret"] == "s" and start["code"]
    assert replies[0]["result"]["job_id"] == jid
    assert replies[1]["result"]["accepted"] and replies[1]["result"]["done"]
    assert replies[2]["result"]["accepted"] is False
    assert replies[3]["error"]["code"] == "bad_request"
    assert replies[4]["error"]["code"] == "bad_request"


def test_job_stream_ws(spec):
    runner = FakeRunner([("sleep", 0.2), ("out", "a\n"), ("out", "b\n"), ("exit", 1, "ok")])
    c, _ = make_client(spec, runner.url)
    with c:
        jid = c.post("/api/v1/jobs", headers=H, json={"code": "x"}).json()["job_id"]
        msgs = []
        with c.websocket_connect(f"/api/v1/ws/jobs/{jid}?token={TOKEN}") as ws:
            while True:
                try:
                    msgs.append(ws.receive_json())
                except Exception:  # noqa: BLE001 - sunucu bitince kapatır
                    break
    data = "".join(m.get("data", "") for m in msgs if m["type"] == "stdout")
    assert "a\n" in data and "b\n" in data
    assert msgs[-1] == {"type": "status", "status": "failed", "exit_code": 1, "reason": "ok"}


def test_job_cancel(spec):
    runner = FakeRunner([("wait_cancel",)])
    c, b = make_client(spec, runner.url)
    with c:
        jid = c.post("/api/v1/jobs", headers=H, json={"code": "while True: pass"}).json()["job_id"]
        time.sleep(0.2)
        assert c.post(f"/api/v1/jobs/{jid}/cancel", headers=H).json() == {"ok": True}
        job = wait_job(c, jid)
    assert job["status"] == "cancelled"
    assert runner.received[-1] == {"type": "cancel"}
    assert ("stop",) in b.commands  # yarım kalan iş sonrası robot durdurulur


@pytest.mark.parametrize("reason,status", [("timeout", "timeout"), ("output_limit", "failed")])
def test_job_limits_map_to_status(spec, reason, status):
    runner = FakeRunner([("exit", -9, reason)])
    c, _ = make_client(spec, runner.url)
    with c:
        jid = c.post("/api/v1/jobs", headers=H, json={"code": "x"}).json()["job_id"]
        job = wait_job(c, jid)
    assert job["status"] == status and job["reason"] == reason


def test_job_runner_unreachable(spec):
    c, _ = make_client(spec, f"ws://127.0.0.1:{_free_port()}/run")
    with c:
        jid = c.post("/api/v1/jobs", headers=H, json={"code": "x"}).json()["job_id"]
        job = wait_job(c, jid)
    assert job["status"] == "failed" and "koşucu" in job["reason"]


@pytest.mark.parametrize("body", [{"code": ""}, {"code": 5}, {"code": "x" * (64 * 1024 + 1)},
                                  {"code": "x", "name": "n" * 101}])  # fmt: skip
def test_job_bad_request(spec, body):
    c, _ = make_client(spec)
    with c:
        r = c.post("/api/v1/jobs", headers=H, json=body)
    assert r.status_code == 400


def test_job_not_found(spec):
    c, _ = make_client(spec)
    with c:
        assert c.get("/api/v1/jobs/yok", headers=H).status_code == 404
        assert c.post("/api/v1/jobs/yok/cancel", headers=H).status_code == 404


def test_queued_job_cancelled_before_start(spec):
    runner = FakeRunner([("sleep", 0.5), ("exit", 0, "ok")])
    c, _ = make_client(spec, runner.url)
    with c:
        j1 = c.post("/api/v1/jobs", headers=H, json={"code": "a"}).json()["job_id"]
        j2 = c.post("/api/v1/jobs", headers=H, json={"code": "b"}).json()["job_id"]
        c.post(f"/api/v1/jobs/{j2}/cancel", headers=H)
        assert wait_job(c, j1)["status"] == "done"
        assert wait_job(c, j2)["status"] == "cancelled"


# --- yardımcılar --------------------------------------------------------------------------------


def test_tokens_parse_and_check():
    t = Tokens.parse("a:0123456789abcdef, b:fedcba9876543210")
    assert t.check("0123456789abcdef") == "a" and t.check("x") is None and t.check("") is None
    with pytest.raises(ValueError):
        Tokens.parse("kisa:123")
    with pytest.raises(ValueError):
        Tokens.parse("bicimsiz")


def test_requirement_of():
    assert requirement_of("G2: rot başı açı limiti") == "G2"
    assert requirement_of("süpervizör erişilemez") == "DURUM"


def test_move_outcome_dict():
    assert MoveOutcome(False, requirement="G1", reason="r").to_dict() == {
        "accepted": False,
        "requirement": "G1",
        "reason": "r",
    }
    d = MoveOutcome(True, "t", False, None, reason="yörünge tamamlanmadı").to_dict()
    assert d["reason"] == "yörünge tamamlanmadı" and d["done"] is False


# --- tic-tac-toe tablası (F4.5) -----------------------------------------------------------------


def _pick_place(c, src, dst, board):
    g = board["geometry"]
    cell = g["cell_mm"]

    def xy(i):
        row, col = divmod(i, 3)
        return ((col - 1) * cell, (1 - row) * cell)

    (sx, sy), (dx, dy) = xy(src), xy(dst)
    up, down = g["travel_P_mm"], g["pick_P_mm"]
    for x, y, z, mag in (
        (sx, sy, up, None),
        (sx, sy, down, True),
        (sx, sy, up, None),
        (dx, dy, up, None),
        (dx, dy, down, False),
        (dx, dy, up, None),
    ):
        r = c.post("/api/v1/move", headers=H, json={"x": x, "y": y, "z": z})
        assert r.json()["accepted"], r.json()
        if mag is not None:
            assert c.post("/api/v1/magnet", headers=H, json={"on": mag}).status_code == 200


def test_board_twin_via_api(spec):
    c, _ = make_client(spec)
    with c:
        b = c.get("/api/v1/board", headers=H).json()
        assert b["cells"] == "XXX...OOO" and b["winner"] is None
        assert b["geometry"]["pick_P_mm"] == -213.0
        _pick_place(c, 1, 4, b)
        b2 = c.get("/api/v1/board", headers=H).json()
        assert b2["cells"] == "X.X.X.OOO"
        assert b2["metrics"]["picks"] == 1 and b2["metrics"]["dropped"] == 0
        assert c.post("/api/v1/board/reset", headers=H).json() == {"ok": True}
        assert c.get("/api/v1/board", headers=H).json()["cells"] == "XXX...OOO"


def test_board_requires_token_and_twin(spec):
    c, b = make_client(spec)
    b.twin = None
    with c:
        assert c.get("/api/v1/board").status_code == 401
        assert c.get("/api/v1/board", headers=H).status_code == 503
        assert c.post("/api/v1/board/reset", headers=H).status_code == 503


def test_board_reset_refused_while_moving(spec):
    c, b = make_client(spec)
    with c:
        b.state().state = "RUNNING"
        r = c.post("/api/v1/board/reset", headers=H)
    assert r.status_code == 409


def test_job_board_rpc(spec):
    runner = FakeRunner([("rpc", 1, "board", {}), ("rpc", 2, "board_reset", {}), ("exit", 0, "ok")])
    c, _ = make_client(spec, runner.url)
    with c:
        jid = c.post("/api/v1/jobs", headers=H, json={"code": "x"}).json()["job_id"]
        assert wait_job(c, jid)["status"] == "done"
    assert runner.received[1]["result"]["cells"] == "XXX...OOO"
    assert runner.received[2]["result"] == {"ok": True}
