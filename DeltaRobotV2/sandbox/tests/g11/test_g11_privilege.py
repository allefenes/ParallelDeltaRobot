"""G11 yetki yükseltme ve kaçış: yetenek yok, no_new_privs, root'a geçiş ve ad alanı açma yok."""

from harness import probe


def test_G11_runs_as_nobody():
    r = probe("import os; print(os.getuid(), os.geteuid(), os.getgid(), os.getgroups())")
    # Docker birincil grubu ek grup olarak da ekleyebilir ([65534] = nogroup); başka grup olmamalı.
    assert r.stdout.strip() in ("65534 65534 65534 []", "65534 65534 65534 [65534]")


def test_G11_no_capabilities_and_no_new_privs():
    r = probe(
        """
        for line in open("/proc/self/status"):
            if line.startswith(("Cap", "NoNewPrivs", "Seccomp:")):
                print(line.strip().replace("\\t", " "))
        """
    )
    status = dict(line.split(":", 1) for line in r.stdout.strip().splitlines())
    status = {k: v.strip() for k, v in status.items()}
    for cap in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb"):
        assert status[cap] == "0000000000000000", (cap, status[cap])
    assert status["NoNewPrivs"] == "1"
    assert status["Seccomp"] == "2"  # Docker varsayılan seccomp profili etkin


def test_G11_setuid_root_fails():
    r = probe(
        """
        import os
        out = []
        for fn, arg in ((os.setuid, 0), (os.seteuid, 0), (os.setgid, 0), (os.setgroups, [0])):
            try:
                fn(arg)
                out.append("ALLOWED")
            except PermissionError:
                out.append("BLOCKED")
        print(*out, os.geteuid())
        """
    )
    assert r.stdout.split() == ["BLOCKED"] * 4 + ["65534"]


def test_G11_no_setuid_binaries_and_su_fails():
    r = probe(
        """
        import os, stat, subprocess
        found = []
        for root in ("/bin", "/sbin", "/usr/bin", "/usr/sbin", "/usr/local/bin"):
            for name in os.listdir(root):
                p = os.path.join(root, name)
                try:
                    st = os.lstat(p)
                except OSError:
                    continue
                if stat.S_ISREG(st.st_mode) and st.st_mode & (stat.S_ISUID | stat.S_ISGID):
                    found.append(p)
        print(found)
        su = subprocess.run(["su", "-c", "id -u"], stdin=subprocess.DEVNULL,
                            capture_output=True, text=True, timeout=10)
        print(su.returncode != 0 and "0" not in su.stdout.split())
        """
    )
    assert r.stdout.split("\n")[:2] == ["[]", "True"]


def test_G11_namespace_and_mount_escape_blocked():
    r = probe(
        """
        import ctypes, os
        libc = ctypes.CDLL(None, use_errno=True)
        out = []
        for flag in (os.CLONE_NEWUSER, os.CLONE_NEWNS, os.CLONE_NEWNET):
            try:
                os.unshare(flag)
                out.append("ALLOWED")
            except OSError:
                out.append("BLOCKED")
        rc = libc.mount(b"none", b"/tmp", b"tmpfs", 0, None)
        out.append("BLOCKED" if rc != 0 else "ALLOWED")
        try:
            os.chroot("/tmp")
            out.append("ALLOWED")
        except OSError:
            out.append("BLOCKED")
        print(*out)
        """
    )
    assert r.stdout.split() == ["BLOCKED"] * 5


def test_G11_kernel_interfaces_blocked():
    r = probe(
        """
        import ctypes, os
        libc = ctypes.CDLL(None, use_errno=True)
        out = []
        # Çekirdek modülü yükleme, ana makine adı değiştirme, aygıt düğümü oluşturma.
        out.append("BLOCKED" if libc.init_module(None, 0, b"") != 0 else "ALLOWED")
        out.append("BLOCKED" if libc.sethostname(b"x", 1) != 0 else "ALLOWED")
        try:
            os.mknod("/tmp/sda", 0o600 | 0o060000, os.makedev(8, 0))
            out.append("ALLOWED")
        except OSError:
            out.append("BLOCKED")
        print(*out)
        """
    )
    assert r.stdout.split() == ["BLOCKED"] * 3
