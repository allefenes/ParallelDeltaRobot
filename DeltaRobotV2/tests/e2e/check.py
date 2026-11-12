"""Uçtan uca senaryo denetimleri: sunucu konteynerinin İÇİNDE, ROS üzerinden çalışır.

Arızaları (konteyner öldürme, ağ gecikmesi/kaybı) tools/e2e.sh dışarıdan enjekte eder; bu betik
robotun her durumda güvenli kaldığını ROS konularından doğrular. Çıkış kodu 0 = geçti.

  python3 /e2e/check.py <senaryo> [seçenekler]

Senaryolar: connected, move, limit, edge_gate, hb_loss, after_server_restart, net_move,
            start_long_move, recover, final_state
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import time

import delta_core_py as dc
import rclpy
from delta_interfaces.msg import EdgeStatus, SupervisorEvent
from delta_interfaces.srv import MoveTo
from geometry_msgs.msg import Point
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool
from std_srvs.srv import SetBool
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

VALID = (20.0, 10.0, -200.0)
FAR = (-20.0, -15.0, -215.0)
OUT_OF_LIMIT = (60.0, 0.0, -140.0)


class Probe(Node):
    def __init__(self):
        super().__init__("e2e_probe")
        self.status: EdgeStatus | None = None
        self.states: list[tuple[float, str]] = []
        self.events: list[SupervisorEvent] = []
        self.connected = False
        self.create_subscription(EdgeStatus, "/edge/status", self._on_status, 50)
        self.create_subscription(SupervisorEvent, "/supervisor/events", self.events.append, 50)
        latched = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(Bool, "/edge/connected", self._on_conn, latched)
        self.move = self.create_client(MoveTo, "/move_to")
        self.pause = self.create_client(SetBool, "/edge_bridge/heartbeat_pause")
        self.torque = self.create_client(SetBool, "/edge_bridge/torque")
        self.traj_pub = self.create_publisher(JointTrajectory, "/edge/trajectory_out", 10)
        self.kin = dc.DeltaKinematics(dc.load_params(os.environ["DELTA_ROBOT_YAML"]))

    def _on_status(self, m: EdgeStatus) -> None:
        self.status = m
        if not self.states or self.states[-1][1] != m.state:
            self.states.append((time.monotonic(), m.state))

    def _on_conn(self, m: Bool) -> None:
        self.connected = m.data

    def spin_until(self, pred, timeout: float) -> bool:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.02)
            if pred():
                return True
        return False

    def call(self, client, req, timeout=10.0):
        if not client.wait_for_service(timeout_sec=timeout):
            raise RuntimeError(f"servis yok: {client.srv_name}")
        fut = client.call_async(req)
        self.spin_until(fut.done, timeout)
        return fut.result()

    def move_to(self, p, duration=1.0):
        req = MoveTo.Request()
        req.target = Point(x=p[0], y=p[1], z=p[2])
        req.duration_s = duration
        return self.call(self.move, req)

    def at(self, p, tol_deg=0.5) -> bool:
        if self.status is None:
            return False
        th = self.kin.inverse(p)
        return all(
            abs(math.degrees(a) - b) < tol_deg for a, b in zip(self.status.angles, th, strict=True)
        )


def fail(msg: str) -> None:
    print(f"BAŞARISIZ: {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"GEÇTİ: {msg}")


def wait_ready(n: Probe, timeout=30.0) -> None:
    """Kenar bağlı ve IDLE olana kadar bekler.

    Bekçi önceki bir kesintide robotu tuttuysa (HOLDING / TORQUE_OFF) kurtarma yalnız açık
    "torque on" ile olur (G6/G7); test bunu operatör adımı olarak yapar ve raporlar.
    """
    if not n.spin_until(lambda: n.connected and n.status is not None, timeout):
        fail(f"kenar bağlı değil (bağlı={n.connected})")
    n.spin_until(lambda: False, 0.3)
    if n.status.state in ("HOLDING", "TORQUE_OFF"):
        print(f"BİLGİ: kenar {n.status.state} durumundaydı; torque on ile yeniden kuruluyor")
        n.call(n.torque, SetBool.Request(data=True))
    if not n.spin_until(lambda: n.status.state == "IDLE", timeout):
        fail(f"kenar hazır değil (bağlı={n.connected}, durum={n.status.state})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario")
    ap.add_argument("--timeout", type=float, default=30.0)
    a = ap.parse_args()
    rclpy.init()
    n = Probe()
    s = a.scenario
    try:
        if s == "connected":
            wait_ready(n, a.timeout)
            ok("kenar bağlı ve IDLE")
        elif s in ("move", "net_move"):
            wait_ready(n)
            target = FAR if n.at(VALID) else VALID
            r = n.move_to(target, 1.0)
            if not r.accepted:
                fail(f"geçerli hedef reddedildi: {r.reason}")
            if not n.spin_until(lambda: n.at(target) and n.status.state == "IDLE", a.timeout):
                fail(f"hedefe ulaşılamadı (durum={n.status.state}, açılar={list(n.status.angles)})")
            ok(f"yörünge kenarda oynatıldı, hedefe ulaşıldı {target}")
        elif s == "limit":
            wait_ready(n)
            before = list(n.status.angles)
            r = n.move_to(OUT_OF_LIMIT, 1.0)
            if r.accepted:
                fail("limit dışı hedef kabul edildi")
            n.spin_until(lambda: any(not e.accepted for e in n.events), 3.0)
            n.spin_until(lambda: False, 0.5)
            if any(abs(a - b) > 1e-3 for a, b in zip(n.status.angles, before, strict=True)):
                fail("reddedilen komuttan sonra robot hareket etti")
            ok(f"1. kapı reddetti: {r.reason}")
        elif s == "edge_gate":
            # 1. kapıyı atlayıp doğrudan kenara limit dışı yörünge: son kapı reddetmeli (G1, G8)
            wait_ready(n)
            before = list(n.status.angles)
            jt = JointTrajectory()
            jt.header.frame_id = "e2e-bypass"
            jt.joint_names = ["motor_1", "motor_2", "motor_3"]
            for k in range(20):
                pt = JointTrajectoryPoint()
                pt.positions = [before[0], before[1], math.radians(160.0)]  # > +150° limit
                pt.time_from_start.nanosec = k * 10_000_000
                jt.points.append(pt)
            n.traj_pub.publish(jt)
            got = n.spin_until(lambda: any(e.requirement == "G1" for e in n.events), 5.0)
            if not got:
                fail("kenar limit dışı yörüngeyi reddetmedi (G1 olayı yok)")
            n.spin_until(lambda: False, 0.5)
            if any(abs(a - b) > 1e-3 for a, b in zip(n.status.angles, before, strict=True)):
                fail("son kapıdan sonra robot hareket etti")
            ok("son kapı (Pi) 1. kapıyı atlayan limit dışı yörüngeyi reddetti, robot hareketsiz")
        elif s == "hb_loss":
            # Hareket ortasında kalp atışı kesilir: T_stop içinde HOLD, T_off'ta tork kapanır
            wait_ready(n)
            target = FAR if n.at(VALID) else VALID
            if not n.move_to(target, 3.0).accepted:
                fail("hedef reddedildi")
            n.spin_until(lambda: n.status.state == "RUNNING", 3.0)
            n.spin_until(lambda: False, 0.5)
            t_cut = time.monotonic()
            n.call(n.pause, SetBool.Request(data=True))
            if not n.spin_until(lambda: n.status.state == "HOLDING", 2.0):
                fail(f"HOLD olmadı (durum={n.status.state})")
            t_hold = next(t for t, st in n.states if st == "HOLDING") - t_cut
            frozen = list(n.status.angles)
            if not n.spin_until(lambda: n.status.state == "TORQUE_OFF", 3.0):
                fail(f"tork kapanmadı (durum={n.status.state})")
            t_off = next(t for t, st in n.states if st == "TORQUE_OFF") - t_cut
            if n.at(target, 0.5):
                fail("kalp atışı kesildiği halde hedefe ulaşıldı")
            if any(
                abs(a - b) > math.radians(1.0) for a, b in zip(n.status.angles, frozen, strict=True)
            ):
                fail("HOLD sonrası robot hareket etmeye devam etti")
            n.call(n.pause, SetBool.Request(data=False))
            n.spin_until(lambda: False, 0.3)
            n.call(n.torque, SetBool.Request(data=True))
            if not n.spin_until(lambda: n.status.state == "IDLE", 5.0):
                fail("kurtarma (kalp atışı + torque on) sonrası IDLE olmadı")
            ok(
                f"kalp atışı kesildi: HOLD {t_hold * 1000:.0f} ms, "
                f"TORQUE_OFF {t_off * 1000:.0f} ms "
                "(gözlem, ±telemetri 50 ms); kurtarma çalıştı"
            )
        elif s == "start_long_move":
            wait_ready(n)
            target = FAR if n.at(VALID) else VALID
            if not n.move_to(target, 4.0).accepted:
                fail("hedef reddedildi")
            n.spin_until(lambda: n.status.state == "RUNNING", 3.0)
            ok("uzun hareket başladı")
        elif s == "after_server_restart":
            # Sunucu hareket ortasında öldü: kenar kopunca HOLD + TORQUE_OFF'a geçmiş olmalı
            if not n.spin_until(lambda: n.connected and n.status is not None, a.timeout):
                fail("kenar yeniden bağlanmadı")
            seen = [st for _, st in n.states]
            if seen[0] not in ("TORQUE_OFF", "IDLE"):
                fail(f"ilk durum güvenli değil: {seen}")
            ok(f"sunucu yeniden başladı, kenar yeniden bağlandı; ilk durumlar {seen[:3]}")
        elif s == "recover":
            # Bekçi torku kapattıysa kurtarma yalnız açık "torque on" ile olur (G7); operatör adımı
            if not n.spin_until(lambda: n.connected and n.status is not None, a.timeout):
                fail("kenar bağlı değil")
            first = n.status.state
            if first not in ("TORQUE_OFF", "HOLDING", "IDLE"):
                fail(f"güvenli olmayan durum: {first}")
            if first != "IDLE":
                n.call(n.torque, SetBool.Request(data=True))
            if not n.spin_until(lambda: n.status.state == "IDLE", 10.0):
                fail(f"kurtarma olmadı (durum={n.status.state})")
            ok(f"bağlantı kesintisinden sonra kenar {first} durumundaydı; torque on ile IDLE")
        elif s == "final_state":
            wait_ready(n, a.timeout)
            ok("sistem IDLE'a döndü")
        else:
            fail(f"bilinmeyen senaryo {s}")
    finally:
        n.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
