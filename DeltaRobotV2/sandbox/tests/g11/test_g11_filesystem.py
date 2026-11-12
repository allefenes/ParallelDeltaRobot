"""G11 dosya sistemi: kök salt okunur, /tmp 16 MB ve noexec, Docker soketi yok."""

import pytest
from harness import probe

WRITE_TEMPLATE = """
import errno
try:
    with open({path!r}, "w") as f:
        f.write("x")
    print("ALLOWED")
except OSError as e:
    print("BLOCKED", errno.errorcode.get(e.errno, e.errno))
"""


@pytest.mark.parametrize(
    "path",
    [
        "/pwn",
        "/home/pwn",
        "/usr/pwn",
        "/usr/local/lib/python3.12/site-packages/delta_robot/pwn.py",
        "/opt/sandbox/bootstrap.py",
        "/etc/passwd",
        "/root/pwn",
        "/var/tmp/pwn",
        "/nonexistent/pwn",
    ],
)
def test_G11_write_outside_tmp_blocked(path):
    r = probe(WRITE_TEMPLATE.format(path=path))
    assert r.stdout.startswith("BLOCKED"), r.stdout
    assert r.stdout.split()[1] in {"EROFS", "EACCES", "ENOENT"}


def test_G11_small_tmp_write_allowed():
    r = probe("open('/tmp/a', 'w').write('merhaba'); print(open('/tmp/a').read())")
    assert r.stdout.strip() == "merhaba"


def test_G11_tmp_size_limit_16m():
    r = probe(
        """
        import errno
        written = 0
        try:
            with open("/tmp/big", "wb") as f:
                for _ in range(64):
                    f.write(b"\\0" * 2**20)
                    f.flush()
                    written += 1
            print("ALLOWED", written)
        except OSError as e:
            print("BLOCKED", errno.errorcode[e.errno], written)
        """
    )
    word, err, mib = r.stdout.split()
    assert (word, err) == ("BLOCKED", "ENOSPC")
    assert int(mib) <= 16


@pytest.mark.parametrize("target", ["/tmp", "/dev/shm"])
def test_G11_exec_from_writable_mount_blocked(target):
    # Betik ve gerçek bir ELF ikilisi kopyalanıp çalıştırılmaya çalışılır.
    r = probe(
        f"""
        import os, shutil, subprocess
        results = []
        script = "{target}/x.sh"
        with open(script, "w") as f:
            f.write("#!/bin/sh\\necho calisti\\n")
        os.chmod(script, 0o755)
        shutil.copy("/bin/true", "{target}/true")
        os.chmod("{target}/true", 0o755)
        for path in (script, "{target}/true"):
            try:
                subprocess.run([path], check=True)
                results.append("ALLOWED")
            except PermissionError:
                results.append("BLOCKED")
        print(*results)
        """
    )
    assert r.stdout.strip() == "BLOCKED BLOCKED"


def test_G11_tmp_and_shm_mounted_noexec_nosuid():
    r = probe(
        """
        for line in open("/proc/mounts"):
            dev, mnt, fs, opts, *_ = line.split()
            if mnt in ("/tmp", "/dev/shm", "/"):
                print(mnt, opts)
        """
    )
    mounts = dict(line.split(" ", 1) for line in r.stdout.strip().splitlines())
    assert mounts["/"].startswith("ro,")
    for mnt in ("/tmp", "/dev/shm"):
        opts = mounts[mnt].split(",")
        assert {"noexec", "nosuid", "nodev"} <= set(opts), mounts[mnt]
    assert "size=16384k" in mounts["/tmp"]


def test_G11_docker_socket_absent():
    r = probe(
        """
        import os
        paths = ["/var/run/docker.sock", "/run/docker.sock", "/var/run/docker", "/run/containerd"]
        print([p for p in paths if os.path.exists(p)])
        print(sorted(k for k in os.environ if "DOCKER" in k or "SECRET" in k or "TOKEN" in k))
        """
    )
    assert r.stdout.split("\n")[:2] == ["[]", "[]"]


def test_G11_proc_and_sys_writes_blocked():
    r = probe(
        """
        import errno
        out = []
        for path in ("/proc/sysrq-trigger", "/proc/sys/kernel/hostname",
                     "/sys/kernel/uevent_helper",
                     "/sys/fs/cgroup/memory.max"):
            try:
                with open(path, "w") as f:
                    f.write("1")
                out.append("ALLOWED:" + path)
            except OSError as e:
                out.append("BLOCKED")
        print(*out)
        """
    )
    assert r.stdout.split() == ["BLOCKED"] * 4
