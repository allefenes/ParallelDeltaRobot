"""API sunucusunu başlatır (uvicorn + TLS).

Ortam değişkenleri:
  DELTA_API_TOKENS     ad:belirteç[,...] (robot modunda zorunlu; sim modunda isteğe bağlı)
  DELTA_BACKEND        ros (varsayılan) | fake (ROS'suz benzetim, yalnız geliştirme)
  DELTA_ROBOT_YAML     robot.yaml yolu (varsayılan /opt/delta/config/robot.yaml)
  DELTA_RUNNER_URL     sandbox koşucusu (varsayılan ws://runner:8100/run)
  DELTA_RUNNER_SECRET  koşucuyla paylaşılan gizli anahtar
  DELTA_WEB_DIR, DELTA_MESHES_DIR, DELTA_I18N_DIR  statik dosyalar
  DELTA_TLS_CERT, DELTA_TLS_KEY   boşsa düz HTTP (yalnız test)
  DELTA_API_HOST, DELTA_API_PORT  varsayılan 0.0.0.0:8000
  DELTA_API_MODE       robot (varsayılan; F4 tek robot) | sim (F6: kullanıcı başına simülasyon)
  DELTA_SIM_TIME_SCALE simülasyon oynatma hızı çarpanı (varsayılan 1 = gerçek zaman)
  DELTA_SIM_MAX_SESSIONS   eşzamanlı ziyaretçi oturumu üst sınırı (varsayılan 50)
  DELTA_SIM_IDLE_TIMEOUT_S boşta oturumun silinme süresi (varsayılan 600 s)
  DELTA_RUNNER_MAX_JOBS koşucunun eşzamanlı iş kapasitesi (koşucudaki değerle aynı)
"""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn
import yaml

from delta_api.app import create_app
from delta_api.auth import StaticAuth, Tokens
from delta_api.backend import FakeBackend
from delta_api.sessions import Limits, Sessions


def _path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default))


def build():
    env = os.environ
    spec_path = env.get("DELTA_ROBOT_YAML", "/opt/delta/config/robot.yaml")
    spec = yaml.safe_load(Path(spec_path).read_text(encoding="utf-8"))
    mode = env.get("DELTA_API_MODE", "robot")
    runner_url = env.get("DELTA_RUNNER_URL", "ws://runner:8100/run")
    runner_secret = env.get("DELTA_RUNNER_SECRET", "")
    # Statik belirteçler isteğe bağlı (pip istemcisi); simülasyon modunda ziyaretçiler anonim.
    tokens = Tokens.parse(env.get("DELTA_API_TOKENS", ""))
    auth = StaticAuth(tokens)
    slots = int(env.get("DELTA_RUNNER_MAX_JOBS", "1"))
    if mode == "sim":
        from delta_server.robot import Robot

        from delta_api.sim_backend import SimBackend

        robot = Robot.load(spec_path)  # kinematik salt okunur; oturumlar paylaşır
        scale = float(env.get("DELTA_SIM_TIME_SCALE", "1"))
        sessions = Sessions(
            runner_url,
            runner_secret,
            factory=lambda: SimBackend(robot, scale),
            runner_slots=slots,
            limits=Limits(
                max_sessions=int(env.get("DELTA_SIM_MAX_SESSIONS", "50")),
                idle_timeout_s=float(env.get("DELTA_SIM_IDLE_TIMEOUT_S", "600")),
            ),
        )
        backend = None
    elif env.get("DELTA_BACKEND", "ros") == "fake":
        backend, sessions = FakeBackend(spec), None
    else:
        import delta_core_py as dc

        from delta_api.ros_backend import RosBackend

        backend = RosBackend(spec, dc.DeltaKinematics(dc.load_params(spec_path)))
        sessions = None
    if sessions is None:
        sessions = Sessions(runner_url, runner_secret, shared=backend, runner_slots=slots)
    return create_app(
        backend,
        tokens,
        runner_url=runner_url,
        runner_secret=runner_secret,
        web_dir=_path("DELTA_WEB_DIR", "/opt/delta/web"),
        meshes_dir=_path("DELTA_MESHES_DIR", "/opt/delta/cad/out/meshes"),
        i18n_dir=_path("DELTA_I18N_DIR", "/opt/delta/i18n/locales"),
        sessions=sessions,
        auth=auth,
    )


def main() -> None:
    env = os.environ
    cert, key = env.get("DELTA_TLS_CERT", ""), env.get("DELTA_TLS_KEY", "")
    uvicorn.run(
        build(),
        host=env.get("DELTA_API_HOST", "0.0.0.0"),
        port=int(env.get("DELTA_API_PORT", "8000")),
        ssl_certfile=cert or None,
        ssl_keyfile=key or None,
        log_level="info",
    )


if __name__ == "__main__":
    main()
