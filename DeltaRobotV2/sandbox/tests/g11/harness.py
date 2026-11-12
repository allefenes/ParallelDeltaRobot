"""G11 test yardımcıları: kullanıcı kodu koşucunun kod yoluyla (`Job`) sandbox imajında koşar."""

from __future__ import annotations

import asyncio
import dataclasses
import subprocess
import textwrap
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from delta_runner import dockerargs
from delta_runner.config import Config, config_from_env
from delta_runner.job import Job

ROBOT_INFO = {
    "name": "Delta Robotics V2",
    "geometry": {"R": 65, "L1": 64, "L2": 201, "r": 35, "tool_offset_mm": 15},
    "limits": {
        "motor_min_deg": -70,
        "motor_max_deg": 150,
        "rod_tilt_max_deg": 13,
        "max_joint_velocity_deg_s": 300,
        "max_joint_acceleration_deg_s2": 3000,
    },
    "workspace": {"cylinder_diameter_mm": 82, "z_top_mm": -145, "z_bottom_mm": -250},
    "home_mm": [0, 0, -200],
}
STATE = {
    "state": "IDLE",
    "angles_deg": [0.0, 0.0, 0.0],
    "position_mm": [0.0, 0.0, -200.0],
    "magnet": False,
    "temps_c": [30, 30, 30],
    "loads": [0, 0, 0],
    "voltages": [12.0, 12.0, 12.0],
    "trajectory_id": "traj-0001-ab12cd",
    "edge_connected": True,
    "job_id": "job-test",
}


def fake_api(msg: dict[str, Any]) -> dict[str, Any]:
    """Sahte API: yöntem başına sözleşmedeki örnek yanıt."""
    method, params = msg["method"], msg["params"]
    if method == "robot":
        return {"result": ROBOT_INFO}
    if method == "state":
        return {"result": STATE}
    if method == "move":
        pos = [params.get("x"), params.get("y"), params.get("z")]
        return {
            "result": {
                "accepted": True,
                "trajectory_id": "traj-2",
                "done": True,
                "position_mm": pos,
            }
        }
    if method == "magnet":
        return {"result": {"ok": True, "magnet": bool(params.get("on"))}}
    return {"result": {"ok": True}}


@dataclass
class Result:
    exit_code: int
    reason: str
    stdout: str
    stderr: str
    rpcs: list[dict[str, Any]]
    messages: list[dict[str, Any]] = field(repr=False)
    elapsed_s: float


def docker_available() -> bool:
    try:
        r = subprocess.run(
            dockerargs.build_image_inspect_argv(Config()), capture_output=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0


def job_containers() -> list[str]:
    r = subprocess.run(
        dockerargs.build_list_jobs_argv(Config()), capture_output=True, text=True, timeout=30
    )
    return r.stdout.split()


def make_config(**limit_overrides: Any) -> Config:
    cfg = config_from_env()
    if limit_overrides:
        cfg = dataclasses.replace(cfg, limits=dataclasses.replace(cfg.limits, **limit_overrides))
    return cfg


async def run_job_async(
    code: str,
    config: Config,
    api: Callable[[dict[str, Any]], dict[str, Any] | None] = fake_api,
    cancel_after_s: float | None = None,
) -> Result:
    messages: list[dict[str, Any]] = []
    job: Job

    async def send(msg: dict[str, Any]) -> None:
        messages.append(msg)
        if msg["type"] == "rpc":
            reply = api(msg)
            if reply is not None:
                await job.rpc_result({"type": "rpc_result", "id": msg["id"], **reply})

    job = Job("job-g11", code, config, send)
    t0 = time.monotonic()
    if cancel_after_s is not None:
        asyncio.get_running_loop().call_later(cancel_after_s, job.cancel)
    exit_msg = await job.run()
    elapsed = time.monotonic() - t0
    return Result(
        exit_code=exit_msg["exit_code"],
        reason=exit_msg["reason"],
        stdout="".join(m["data"] for m in messages if m["type"] == "stdout"),
        stderr="".join(m["data"] for m in messages if m["type"] == "stderr"),
        rpcs=[m for m in messages if m["type"] == "rpc"],
        messages=messages,
        elapsed_s=elapsed,
    )


def run_code(code: str, *, api=fake_api, cancel_after_s=None, **limit_overrides: Any) -> Result:
    """Kodu sandbox'ta çalıştırır (girinti temizlenir) ve sonucu toplar."""
    cfg = make_config(**limit_overrides)
    return asyncio.run(
        run_job_async(textwrap.dedent(code), cfg, api=api, cancel_after_s=cancel_after_s)
    )


def probe(code: str, **kw: Any) -> Result:
    """Normal bitmesi beklenen yoklama: çıkış 0 olmalı, yoksa stderr gösterilir."""
    r = run_code(code, **kw)
    assert (r.exit_code, r.reason) == (0, "ok"), r.stderr
    return r
