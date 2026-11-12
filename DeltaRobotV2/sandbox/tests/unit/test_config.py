"""Ayarlar: varsayılanlar api.md, ortam değişkeni geçersiz kılma ve doğrulama."""

import pytest
from delta_runner.config import Config, Limits, config_from_env


def test_defaults_match_api_md():
    lim = config_from_env({}).limits
    assert (lim.memory, lim.cpus, lim.pids, lim.tmpfs_size) == ("256m", "0.5", 64, "16m")
    assert lim.timeout_s == 120.0
    assert lim.output_bytes == 1024 * 1024
    assert config_from_env({}).image == "deltarobotv2-sandbox:latest"


def test_env_overrides():
    cfg = config_from_env(
        {
            "DELTA_SANDBOX_TIMEOUT_S": "5",
            "DELTA_SANDBOX_OUTPUT_LIMIT": "4096",
            "DELTA_SANDBOX_MEMORY": "128m",
            "DELTA_SANDBOX_CPUS": "0.25",
            "DELTA_SANDBOX_PIDS": "32",
            "DELTA_SANDBOX_TMPFS_SIZE": "8m",
            "DELTA_SANDBOX_IMAGE": "deltarobotv2-sandbox:test",
        }
    )
    assert cfg.limits == Limits("128m", "0.25", 32, "8m", 5.0, 4096)
    assert cfg.image == "deltarobotv2-sandbox:test"


def test_blank_env_keeps_default():
    assert config_from_env({"DELTA_SANDBOX_TIMEOUT_S": "  "}).limits.timeout_s == 120.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"memory": "256m --privileged"},
        {"memory": "0m"},
        {"tmpfs_size": "16m,exec"},
        {"cpus": "0.5;"},
        {"cpus": "-1"},
        {"pids": 0},
        {"pids": 100000},
        {"timeout_s": 0},
        {"timeout_s": float("nan")},
        {"output_bytes": 10},
    ],
)
def test_invalid_limits_rejected(kwargs):
    with pytest.raises(ValueError):
        Limits(**kwargs)


@pytest.mark.parametrize("image", ["--privileged", "a b", "Upper:tag", ""])
def test_invalid_image_rejected(image):
    with pytest.raises(ValueError):
        Config(image=image)


def test_max_jobs_default_env_and_bounds():
    assert Config().max_jobs == 1
    assert config_from_env({"DELTA_SANDBOX_MAX_JOBS": "4"}).max_jobs == 4
    for bad in (0, 33):
        with pytest.raises(ValueError):
            Config(max_jobs=bad)
