import builtins
import random
import time
import types
import pytest

import openhands.runtime.utils.port_lock as port_lock

# Tests for find_available_port_with_lock, deterministic by monkeypatching

class _FakeRng:
    def __init__(self, seq):
        # copy sequence so multiple calls are deterministic
        self._seq = list(seq)
        self._idx = 0

    def randint(self, a, b):
        # ignore a/b bounds to allow exercising wrap branches deterministically
        if self._idx >= len(self._seq):
            # if exhausted, return a stable fallback within bounds
            return a
        v = self._seq[self._idx]
        self._idx += 1
        return v


def test_find_available_port_random_success_round_034(monkeypatch):
    """Random-attempt path: first acquired lock and port is available -> return.

    This covers the branch where lock.acquire() is True and _check_port_available() is True
    during the random attempts loop.
    """
    # deterministic sequence: one random attempt value, then start_port if needed (won't be used)
    seq = [30001, 30001]
    # Monkeypatch random.SystemRandom to return our deterministic rng
    monkeypatch.setattr(random, 'SystemRandom', lambda: _FakeRng(seq))

    # Prepare fake PortLock that reports acquire True for the chosen port
    acquire_map = {30001: True}
    available_map = {30001: True}

    class FakePortLock:
        def __init__(self, port, lock_dir=None):
            self.port = port
            self.released = False
            self.acquired = False

        def acquire(self, timeout=None):
            rv = acquire_map.get(self.port, False)
            self.acquired = rv
            return rv

        def release(self):
            self.released = True

    monkeypatch.setattr(port_lock, 'PortLock', FakePortLock)
    monkeypatch.setattr(port_lock, '_check_port_available', lambda port, addr: available_map.get(port, False))
    # avoid sleeping during tests
    monkeypatch.setattr(time, 'sleep', lambda s: None)

    res = port_lock.find_available_port_with_lock(min_port=30000, max_port=30005, max_attempts=4, bind_address='127.0.0.1', lock_timeout=0.1)

    assert res is not None, "Expected to find and lock a port"
    port, lock = res
    assert port == 30001
    assert isinstance(lock, FakePortLock)
    assert lock.acquired is True
    assert lock.released is False


def test_find_available_port_random_lock_but_unavailable_then_sequential_wrap_round_034(monkeypatch):
    """Exercise branch where random attempts acquire lock but port unavailable (release called),
    then sequential search wraps (by using an out-of-bounds start_port from RNG) and eventually finds a port.

    This test forces the code path where lock.acquire() True but _check_port_available() False (-> release()),
    then uses a start_port larger than max_port so the wrap branch (port > max_port -> wrap to min_port + ...) is taken
    during sequential attempts, and finally finds an available port.
    """
    # Sequence for RNG:
    # - First values: two random attempts values used in the random loop (we'll return a port that will be locked but unavailable)
    # - Next value: start_port for sequential search — purposely set outside the normal bound to force wrapping behavior
    seq = [31000, 31001, 99999]
    monkeypatch.setattr(random, 'SystemRandom', lambda: _FakeRng(seq))

    # Configure behavior per port for acquire() and availability
    # For random attempts 31000 and 31001: acquire True but available False -> release should be called
    # For sequential attempts: start_port will be large (99999) to exercise the wrap branch; we then simulate a few ports
    # and make one of them available
    acquire_map = {}
    available_map = {}

    # Random phase ports (will be passed to PortLock during the random attempts loop)
    acquire_map[31000] = True
    available_map[31000] = False
    acquire_map[31001] = True
    available_map[31001] = False

    # For sequential phase, since start_port will be an out-of-range large number, the loop will compute
    # port values > max_port and trigger the wrap branch. We'll simulate that the wrapped-to port 30002 is available.
    # We can't predict exact wrapped value easily here without duplicating internal math, so implement FakePortLock
    # to consult a fallback mapping for which sequential attempt should succeed. We'll choose port 30002 as the
    # ultimate available port.
    available_map[30002] = True
    # For other ports in sequential phase, make acquire False initially so the loop continues
    acquire_map[30002] = True

    # Track releases to assert release was called for the random-phase ports
    release_calls = []

    class FakePortLock:
        def __init__(self, port, lock_dir=None):
            self.port = port
            self.released = False
            self.acquired = False

        def acquire(self, timeout=None):
            rv = acquire_map.get(self.port, False)
            self.acquired = rv
            return rv

        def release(self):
            self.released = True
            release_calls.append(self.port)

    monkeypatch.setattr(port_lock, 'PortLock', FakePortLock)
    monkeypatch.setattr(port_lock, '_check_port_available', lambda port, addr: available_map.get(port, False))
    monkeypatch.setattr(time, 'sleep', lambda s: None)

    # Use a narrow port range so wrapping behavior is observable in a deterministic manner
    min_p = 30000
    max_p = 30005
    result = port_lock.find_available_port_with_lock(min_port=min_p, max_port=max_p, max_attempts=6, bind_address='127.0.0.1', lock_timeout=0.1)

    # We expect the function to succeed (return a tuple)
    assert result is not None, "Expected to find a port after sequential attempts"
    found_port, found_lock = result
    # Ensure the returned lock is our FakePortLock and reports acquired
    assert isinstance(found_lock, FakePortLock)
    assert found_lock.acquired is True
    # Assert that at least one of the random-phase ports had release() called because they were locked but unavailable
    assert 31000 in release_calls or 31001 in release_calls
    # Assert that the found port is the one we marked available (30002)
    assert found_port == 30002
