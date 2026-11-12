"""docker run argüman üreticisi: api.md'deki bayraklarla birebir aynı olmalı."""

import re
from pathlib import Path

import pytest
from delta_runner import dockerargs
from delta_runner.config import Config, Limits

API_MD = Path(__file__).resolve().parents[3] / "docs" / "api.md"


def api_md_flags() -> list[str]:
    text = API_MD.read_text(encoding="utf-8")
    m = re.search(r"`docker run` bayrakları[^`]*`([^`]+)`", text)
    assert m, "api.md'de docker run bayrakları bulunamadı"
    return m.group(1).split()


def test_security_flags_match_api_md_exactly():
    assert dockerargs.security_flags(Limits()) == api_md_flags()


def test_run_argv_layout():
    cfg = Config()
    argv = dockerargs.build_run_argv(
        cfg, "job-0001-ab12", "deltarobotv2-job-job-0001-ab12-deadbeef"
    )
    assert argv[:2] == ["docker", "run"]
    flags = api_md_flags()
    assert argv[2 : 2 + len(flags)] == flags
    rest = argv[2 + len(flags) :]
    assert rest == [
        "--name",
        "deltarobotv2-job-job-0001-ab12-deadbeef",
        "--label",
        "deltarobotv2.sandbox=job",
        "--label",
        "deltarobotv2.job_id=job-0001-ab12",
        "deltarobotv2-sandbox:latest",
    ]


def test_run_argv_has_no_env_mounts_or_privileges():
    argv = dockerargs.build_run_argv(Config(), "j", "deltarobotv2-job-j-0000")
    for bad in ("-e", "--env", "-v", "--volume", "--mount", "--privileged", "--cap-add", "-p"):
        assert bad not in argv
    assert not any(a.startswith(("--env", "--volume", "--device", "--network=")) for a in argv)


def test_limits_override_flows_into_flags():
    lim = Limits(memory="128m", cpus="0.25", pids=32, tmpfs_size="8m")
    flags = dockerargs.security_flags(lim)
    assert flags[flags.index("--memory") + 1] == "128m"
    assert flags[flags.index("--memory-swap") + 1] == "128m"  # takas yok
    assert flags[flags.index("--cpus") + 1] == "0.25"
    assert flags[flags.index("--pids-limit") + 1] == "32"
    assert "/tmp:rw,size=8m,noexec" in flags


@pytest.mark.parametrize(
    "job_id, expected",
    [
        ("job-0001-ab12", "job-0001-ab12"),
        ("a b/c;rm -rf", "a-b-c-rm--rf"),
        ("--privileged", "privileged"),
        ("", "job"),
        ("x" * 100, "x" * 40),
    ],
)
def test_safe_job_id(job_id, expected):
    assert dockerargs.safe_job_id(job_id) == expected


def test_container_name_is_prefixed_and_unique_suffix_validated():
    assert dockerargs.container_name("j1", "00ff") == "deltarobotv2-job-j1-00ff"
    with pytest.raises(ValueError):
        dockerargs.container_name("j1", "../x")


def test_rm_and_list_argv():
    cfg = Config()
    assert dockerargs.build_rm_argv(cfg, "n") == ["docker", "rm", "-f", "n"]
    assert dockerargs.build_list_jobs_argv(cfg) == [
        "docker",
        "ps",
        "-aq",
        "--filter",
        "label=deltarobotv2.sandbox=job",
    ]
