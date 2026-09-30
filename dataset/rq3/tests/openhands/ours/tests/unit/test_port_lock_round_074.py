import types
import importlib
import os as real_os
import builtins
import pytest

# Import module under test
port_lock_mod = importlib.import_module("openhands.runtime.utils.port_lock")
PortLock = port_lock_mod.PortLock

def test_acquire_already_locked_round_074():
    # If the lock is already marked as locked, acquire should return True immediately
    pl = PortLock(port=11111, lock_dir="/tmp")
    pl._locked = True

    assert pl.acquire(timeout=0.1) is True
    # state should remain locked
    assert pl._locked is True


def test_acquire_unix_success_round_074(monkeypatch):
    # Simulate POSIX (HAS_FCNTL True) success path: flock succeeds, file write occurs
    monkeypatch.setattr(port_lock_mod, "HAS_FCNTL", True)

    recorded = {}

    def fake_open(path, flags):
        # return a fake file descriptor
        recorded['path'] = path
        return 3

    def fake_write(fd, data):
        # record what was written and return the number of bytes written
        recorded.setdefault('writes', []).append((fd, data))
        return len(data)

    def fake_fsync(fd):
        recorded['fsync'] = fd
        return None

    fake_fcntl = types.SimpleNamespace()
    def fake_flock(fd, flags):
        # succeed (do nothing)
        recorded['flock'] = (fd, flags)
        return None
    fake_fcntl.flock = fake_flock

    monkeypatch.setattr(port_lock_mod, 'fcntl', fake_fcntl)
    monkeypatch.setattr(port_lock_mod, 'os', types.SimpleNamespace(
        open=fake_open,
        write=fake_write,
        fsync=fake_fsync,
        close=lambda fd: None,
        O_CREAT=real_os.O_CREAT,
        O_WRONLY=real_os.O_WRONLY,
        O_TRUNC=real_os.O_TRUNC
    ))

    pl = PortLock(port=22222, lock_dir="/irrelevant")
    ok = pl.acquire(timeout=0.5)

    assert ok is True
    # port written to file descriptor as bytes with newline
    assert recorded.get('writes') is not None
    assert recorded['writes'][0][1] == b'22222\n'
    assert pl._locked is True


def test_acquire_unix_timeout_closes_round_074(monkeypatch):
    # Simulate POSIX timeout where os.open occurs but timeout is zero
    monkeypatch.setattr(port_lock_mod, "HAS_FCNTL", True)

    calls = {}

    def fake_open(path, flags):
        calls['open'] = True
        return 4

    # flock would never be called because timeout==0 (while loop skipped), but ensure it's present
    fake_fcntl = types.SimpleNamespace()
    def raising_flock(fd, flags):
        raise OSError("locked")
    fake_fcntl.flock = raising_flock

    closed = {'called': False}
    def fake_close(fd):
        closed['called'] = True

    monkeypatch.setattr(port_lock_mod, 'fcntl', fake_fcntl)
    monkeypatch.setattr(port_lock_mod, 'os', types.SimpleNamespace(
        open=fake_open,
        write=lambda fd, data: len(data),
        fsync=lambda fd: None,
        close=fake_close,
        O_CREAT=real_os.O_CREAT,
        O_WRONLY=real_os.O_WRONLY,
        O_TRUNC=real_os.O_TRUNC
    ))

    pl = PortLock(port=33333, lock_dir="/irrelevant")
    # timeout zero -> skip while loop -> direct timeout branch that should close the fd
    ok = pl.acquire(timeout=0)

    assert ok is False
    assert closed['called'] is True
    assert pl.lock_fd is None


def test_acquire_windows_success_round_074(monkeypatch):
    # Simulate Windows fallback (HAS_FCNTL False) success path: exclusive creation succeeds
    monkeypatch.setattr(port_lock_mod, "HAS_FCNTL", False)

    recorded = {}

    def fake_open(path, flags):
        recorded['open_path'] = path
        recorded['open_flags'] = flags
        return 7

    def fake_write(fd, data):
        recorded.setdefault('writes', []).append((fd, data))
        return len(data)

    def fake_fsync(fd):
        recorded['fsync'] = fd
        return None

    monkeypatch.setattr(port_lock_mod, 'os', types.SimpleNamespace(
        open=fake_open,
        write=fake_write,
        fsync=fake_fsync,
        close=lambda fd: None,
        O_CREAT=real_os.O_CREAT,
        O_EXCL=getattr(real_os, 'O_EXCL', 0x400),
        O_WRONLY=real_os.O_WRONLY
    ))

    pl = PortLock(port=44444, lock_dir="/irrelevant")
    ok = pl.acquire(timeout=0.5)

    assert ok is True
    assert recorded.get('writes') is not None
    assert recorded['writes'][0][1] == b'44444\n'
    assert pl._locked is True


def test_acquire_windows_timeout_round_074(monkeypatch):
    # Simulate Windows fallback but immediate timeout (timeout=0) -> should return False
    monkeypatch.setattr(port_lock_mod, "HAS_FCNTL", False)

    # Make sure os.open is not accidentally called by providing a function that would flag if called
    def fail_open(*args, **kwargs):
        raise AssertionError("os.open should not be called when timeout=0 and while is skipped")

    monkeypatch.setattr(port_lock_mod, 'os', types.SimpleNamespace(
        open=fail_open,
        write=lambda fd, data: len(data),
        fsync=lambda fd: None,
        close=lambda fd: None,
        O_CREAT=real_os.O_CREAT,
        O_EXCL=getattr(real_os, 'O_EXCL', 0x400),
        O_WRONLY=real_os.O_WRONLY
    ))

    pl = PortLock(port=55555, lock_dir="/irrelevant")
    ok = pl.acquire(timeout=0)

    assert ok is False


def test_acquire_outer_exception_cleanup_round_074(monkeypatch):
    # Simulate an unexpected exception inside the try block to exercise the outer except cleanup
    monkeypatch.setattr(port_lock_mod, "HAS_FCNTL", True)

    closed = {'attempted': False}

    def fake_open(path, flags):
        # return a fd so that outer except finds lock_fd truthy
        return 9

    def fake_flock(fd, flags):
        # raise RuntimeError (not OSError) so it is not caught by inner except and goes to outer except
        raise RuntimeError("boom")

    def fake_close(fd):
        closed['attempted'] = True
        # Simulate close raising OSError to exercise inner except in cleanup
        raise OSError("close failed")

    monkeypatch.setattr(port_lock_mod, 'fcntl', types.SimpleNamespace(flock=fake_flock))
    monkeypatch.setattr(port_lock_mod, 'os', types.SimpleNamespace(
        open=fake_open,
        write=lambda fd, data: len(data),
        fsync=lambda fd: None,
        close=fake_close,
        O_CREAT=real_os.O_CREAT,
        O_WRONLY=real_os.O_WRONLY,
        O_TRUNC=real_os.O_TRUNC
    ))

    pl = PortLock(port=66666, lock_dir="/irrelevant")
    ok = pl.acquire(timeout=0.5)

    # Should have returned False due to exception and attempted cleanup
    assert ok is False
    assert closed['attempted'] is True
    # lock_fd must be cleared after cleanup
    assert pl.lock_fd is None
