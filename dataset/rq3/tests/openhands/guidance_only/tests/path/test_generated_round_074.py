import importlib
import types
import pytest

# Import the module under test
pl_mod = importlib.import_module('openhands.runtime.utils.port_lock')

# Helpers to create deterministic time sequences
def make_time_seq(values):
    it = iter(values)
    def _time():
        try:
            return next(it)
        except StopIteration:
            return values[-1]
    return _time

class DummyFcntl:
    LOCK_EX = 1
    LOCK_NB = 2
    def __init__(self, should_raise=False):
        self.should_raise = should_raise
    def flock(self, fd, flags):
        if self.should_raise:
            raise OSError('locked')
        return None

# Test: fcntl path, immediate success
def test_acquire_fcntl_success_round_074(tmp_path, monkeypatch):
    monkeypatch.setattr(pl_mod, 'HAS_FCNTL', True)

    wrote = {}
    calls = {'open': 0}

    def fake_open(path, flags):
        calls['open'] += 1
        # return a fake file descriptor
        return 3

    def fake_write(fd, data):
        wrote['data'] = data
        return len(data)

    def fake_fsync(fd):
        wrote['fsync'] = True

    # time: start_time = 0, subsequent time returns 0 so loop iterates and succeeds immediately
    monkeypatch.setattr(pl_mod.time, 'time', make_time_seq([0, 0]))
    monkeypatch.setattr(pl_mod.time, 'sleep', lambda s: None)

    # Provide dummy fcntl that does not raise
    dummy = DummyFcntl(should_raise=False)
    monkeypatch.setattr(pl_mod, 'fcntl', dummy)

    monkeypatch.setattr(pl_mod.os, 'open', fake_open)
    monkeypatch.setattr(pl_mod.os, 'write', fake_write)
    monkeypatch.setattr(pl_mod.os, 'fsync', fake_fsync)

    lock = pl_mod.PortLock(12345, str(tmp_path))
    result = lock.acquire(timeout=1.0)

    assert result is True
    assert lock._locked is True
    assert lock.lock_fd == 3
    # written payload includes the port and newline
    assert wrote['data'] == b'12345\n'
    assert wrote.get('fsync') is True
    assert calls['open'] == 1


# Test: fcntl path, flock always fails -> timeout path, ensures fd is closed and returns False
def test_acquire_fcntl_timeout_closes_fd_round_074(tmp_path, monkeypatch):
    monkeypatch.setattr(pl_mod, 'HAS_FCNTL', True)

    closed = {'called': False}
    calls = {'open': 0}

    def fake_open(path, flags):
        calls['open'] += 1
        # return a fake file descriptor
        return 4

    def fake_close(fd):
        closed['called'] = True

    # fcntl that always raises to simulate another process holding lock
    dummy = DummyFcntl(should_raise=True)
    monkeypatch.setattr(pl_mod, 'fcntl', dummy)

    # time sequence: start_time = 0 (first call), while loop check uses 0 (second call) -> attempt1
    # After one failed attempt, next time() returns 2 so loop ends due to timeout
    monkeypatch.setattr(pl_mod.time, 'time', make_time_seq([0, 0, 2]))
    monkeypatch.setattr(pl_mod.time, 'sleep', lambda s: None)

    monkeypatch.setattr(pl_mod.os, 'open', fake_open)
    monkeypatch.setattr(pl_mod.os, 'close', fake_close)

    lock = pl_mod.PortLock(23456, str(tmp_path))
    result = lock.acquire(timeout=1.0)

    assert result is False
    # lock_fd should have been cleaned up (set to None)
    assert lock.lock_fd is None
    assert closed['called'] is True
    assert calls['open'] == 1


# Test: non-fcntl (Windows fallback) immediate success
def test_acquire_no_fcntl_success_round_074(tmp_path, monkeypatch):
    monkeypatch.setattr(pl_mod, 'HAS_FCNTL', False)

    wrote = {}
    calls = {'open': 0}

    def fake_open(path, flags):
        calls['open'] += 1
        return 5

    def fake_write(fd, data):
        wrote['data'] = data
        return len(data)

    def fake_fsync(fd):
        wrote['fsync'] = True

    # time sequence to allow immediate success
    monkeypatch.setattr(pl_mod.time, 'time', make_time_seq([0, 0]))
    monkeypatch.setattr(pl_mod.time, 'sleep', lambda s: None)

    monkeypatch.setattr(pl_mod.os, 'open', fake_open)
    monkeypatch.setattr(pl_mod.os, 'write', fake_write)
    monkeypatch.setattr(pl_mod.os, 'fsync', fake_fsync)

    lock = pl_mod.PortLock(34567, str(tmp_path))
    result = lock.acquire(timeout=1.0)

    assert result is True
    assert lock._locked is True
    assert lock.lock_fd == 5
    assert wrote['data'] == b'34567\n'
    assert wrote.get('fsync') is True
    assert calls['open'] == 1


# Test: non-fcntl timeout path when os.open always raises OSError
def test_acquire_no_fcntl_timeout_round_074(tmp_path, monkeypatch):
    monkeypatch.setattr(pl_mod, 'HAS_FCNTL', False)

    calls = {'open': 0}

    def fake_open_raise(path, flags):
        calls['open'] += 1
        raise OSError('exists')

    monkeypatch.setattr(pl_mod.os, 'open', fake_open_raise)

    # time seq: start_time=0, first loop check uses 0 -> attempt and fail, next returns 2 -> timeout
    monkeypatch.setattr(pl_mod.time, 'time', make_time_seq([0, 0, 2]))
    monkeypatch.setattr(pl_mod.time, 'sleep', lambda s: None)

    lock = pl_mod.PortLock(45678, str(tmp_path))
    result = lock.acquire(timeout=1.0)

    assert result is False
    # since we never successfully opened, lock_fd remains None
    assert lock.lock_fd is None
    assert calls['open'] >= 1


# Test: outer exception path and cleanup attempts to close existing fd; simulate os.close raising OSError
def test_acquire_exception_cleanup_close_raises_round_074(tmp_path, monkeypatch):
    monkeypatch.setattr(pl_mod, 'HAS_FCNTL', True)

    close_calls = {'called': 0}

    def fake_open_raise(path, flags):
        # Simulate an exception thrown while trying to open (not an OSError specifically)
        raise Exception('boom')

    def fake_close_raise(fd):
        close_calls['called'] += 1
        raise OSError('close failed')

    # Prepare a PortLock with an existing fd to be cleaned up in the exception handler
    lock = pl_mod.PortLock(56789, str(tmp_path))
    lock.lock_fd = 99  # existing fd that should be closed in exception handler

    monkeypatch.setattr(pl_mod.os, 'open', fake_open_raise)
    monkeypatch.setattr(pl_mod.os, 'close', fake_close_raise)

    # time functions aren't used meaningfully here
    monkeypatch.setattr(pl_mod.time, 'time', make_time_seq([0]))
    monkeypatch.setattr(pl_mod.time, 'sleep', lambda s: None)

    # Now call acquire; it should catch the Exception, attempt to close, handle OSError, and return False
    result = lock.acquire(timeout=1.0)

    assert result is False
    # lock_fd should have been nulled out by the exception handler
    assert lock.lock_fd is None
    # close was attempted once and raised OSError which should be swallowed
    assert close_calls['called'] == 1
