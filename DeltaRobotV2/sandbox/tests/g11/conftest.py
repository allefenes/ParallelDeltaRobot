"""G11 fikstürleri. Docker soketi ve sandbox imajı gerekir (sandbox/run_tests.sh soket bağlı
konteynerde koşturur). `DELTA_REQUIRE_DOCKER=1` iken Docker yoksa testler atlanmaz, başarısız olur.
"""

import os

import pytest
from harness import docker_available, job_containers


@pytest.fixture(scope="session", autouse=True)
def _require_docker():
    if not docker_available():
        msg = "Docker soketi ya da deltarobotv2-sandbox:latest imajı yok"
        if os.environ.get("DELTA_REQUIRE_DOCKER") == "1":
            pytest.fail(msg)
        pytest.skip(msg)


@pytest.fixture(autouse=True)
def _no_leftover_containers():
    yield
    assert job_containers() == [], "iş konteyneri geride kaldı"
