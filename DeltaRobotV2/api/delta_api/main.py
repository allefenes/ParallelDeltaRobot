"""API sunucusunu başlatır (uvicorn + TLS).

Ortam değişkenleri:
  DELTA_API_TOKENS     ad:belirteç[,...] (zorunlu)
  DELTA_BACKEND        ros (varsayılan) | fake (ROS'suz benzetim, yalnız geliştirme)
  DELTA_ROBOT_YAML     robot.yaml yolu (varsayılan /opt/delta/config/robot.yaml)
  DELTA_RUNNER_URL     sandbox koşucusu (varsayılan ws://runner:8100/run)
  DELTA_RUNNER_SECRET  koşucuyla paylaşılan gizli anahtar
  DELTA_WEB_DIR, DELTA_MESHES_DIR, DELTA_I18N_DIR  statik dosyalar
  DELTA_TLS_CERT, DELTA_TLS_KEY   boşsa düz HTTP (yalnız test)
  DELTA_API_HOST, DELTA_API_PORT  varsayılan 0.0.0.0:8000
"""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn
import yaml

from delta_api.app import create_app
from delta_api.auth import Tokens
from delta_api.backend import FakeBackend


def _path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default))


def build():
    env = os.environ
    spec_path = env.get("DELTA_ROBOT_YAML", "/opt/delta/config/robot.yaml")
    spec = yaml.safe_load(Path(spec_path).read_text(encoding="utf-8"))
    if env.get("DELTA_BACKEND", "ros") == "fake":
        backend = FakeBackend(spec)
    else:
        import delta_core_py as dc

        from delta_api.ros_backend import RosBackend

        backend = RosBackend(spec, dc.DeltaKinematics(dc.load_params(spec_path)))
    tokens = Tokens.parse(env.get("DELTA_API_TOKENS", ""))
    return create_app(
        backend,
        tokens,
        runner_url=env.get("DELTA_RUNNER_URL", "ws://runner:8100/run"),
        runner_secret=env.get("DELTA_RUNNER_SECRET", ""),
        web_dir=_path("DELTA_WEB_DIR", "/opt/delta/web"),
        meshes_dir=_path("DELTA_MESHES_DIR", "/opt/delta/cad/out/meshes"),
        i18n_dir=_path("DELTA_I18N_DIR", "/opt/delta/i18n/locales"),
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
