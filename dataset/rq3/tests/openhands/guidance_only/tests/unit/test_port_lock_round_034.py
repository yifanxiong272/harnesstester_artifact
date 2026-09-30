import pytest

from types import SimpleNamespace

import openhands.runtime.utils.port_lock as port_lock_module
from openhands.runtime.utils.port_lock import find_available_port_with_lock


class FakeRandom:
    """Deterministic fake SystemRandom that returns a preset sequence of ints.

    The randint method ignores its a/b args and returns the next value from seq.
    If seq is exhausted, it raises IndexError to fail fast.
    """

    def __init__(self, seq):
        self._seq = list(seq)

    def randint(self, a, b):
        return self._seq.pop(0)


class MockLock:
    """Mock replacement for PortLock used by the tests.

    Behavior is controlled via class-level mapping _acquire_map which maps
    port -> bool for whether acquire() should succeed. Each instance records
    whether release() was called in self.released.
    """

    _acquire_map = {}

    def __init__(self, port, lock_dir=None):
        self.port = port
        self.released = False

    def acquire(self, timeout=None):
        # Return configured value (default False) for this port
        return MockLock._acquire_map.get(self.port, False)

    def release(self):
        self.released = True

    def is_locked(self):
        # Convenience used by tests if needed
        return MockLock._acquire_map.get(self.port, False) and not self.released


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    # Avoid real sleeping in the code under test
    monkeypatch.setattr(port_lock_module.time, "sleep", lambda s: None)
    yield


def test_random_lock_success_round_034(monkeypatch):
    """When a random attempt acquires the lock and the port is available,
    the function should return (port, lock) immediately.
    """
    # Choose a deterministic port value that will be returned by FakeRandom
    chosen_port = 34567

    # Fake SystemRandom so that the first (and only) random attempt picks chosen_port
    fake_rng = FakeRandom([chosen_port])
    monkeypatch.setattr(port_lock_module.random, "SystemRandom", lambda: fake_rng)

    # Patch PortLock with our MockLock and configure acquire to succeed for chosen_port
    monkeypatch.setattr(port_lock_module, "PortLock", MockLock)
    MockLock._acquire_map = {chosen_port: True}

    # Patch _check_port_available to report chosen_port as available (others not)
    monkeypatch.setattr(
        port_lock_module,
        "_check_port_available",
        lambda port, addr: port == chosen_port,
    )

    # Call with max_attempts small so there is only one random attempt
    result = find_available_port_with_lock(min_port=30000, max_port=40000, max_attempts=2, lock_timeout=0.1)

    assert result is not None, "Expected a (port, lock) tuple but got None"
    port, lock = result
    assert port == chosen_port
    assert isinstance(lock, MockLock)
    # Ensure the lock is still considered acquired according to our mock mapping
    assert lock.is_locked() is True


def test_sequential_release_and_none_round_034(monkeypatch):
    """Simulate failing random attempts and sequential attempts where locks
    are acquired but ports are not available (so release() is called), and
    finally the function returns None.
    """
    # Configure sequence of randint returns:
    # - Two random attempts (will pick p1 and p2), both should fail to acquire
    # - start_port for sequential search
    p1, p2 = 30010, 30011
    start_port = 30020
    fake_rng = FakeRandom([p1, p2, start_port])
    monkeypatch.setattr(port_lock_module.random, "SystemRandom", lambda: fake_rng)

    # Patch PortLock with MockLock. Configure acquire to return False for random ports
    # and True for sequential ports (so release() will be invoked when port not available).
    monkeypatch.setattr(port_lock_module, "PortLock", MockLock)
    MockLock._acquire_map = {
        p1: False,
        p2: False,
        start_port: True,
        start_port + 1: True,
    }

    # Patch _check_port_available: sequential ports are NOT available -> should trigger release()
    def fake_check(port, addr):
        # Random attempt ports: irrelevant (we never acquired them)
        # Sequential ports: return False to trigger release
        if port in (start_port, start_port + 1):
            return False
        return False

    monkeypatch.setattr(port_lock_module, "_check_port_available", fake_check)

    # Track if any release was called: each MockLock instance tracks it, but we want
    # to assert at least one sequential lock had release called.
    created_locks = []

    # Monkeypatch PortLock constructor to capture instances in created_locks list
    original_PortLock = MockLock

    def ctor_capture(port, lock_dir=None):
        inst = original_PortLock(port, lock_dir)
        created_locks.append(inst)
        return inst

    monkeypatch.setattr(port_lock_module, "PortLock", ctor_capture)

    # Run with max_attempts = 4 -> random_attempts = 2, remaining_attempts = 2
    result = find_available_port_with_lock(min_port=30000, max_port=30030, max_attempts=4, lock_timeout=0.01)

    # Expect None because sequential attempts found locks but ports were unavailable
    assert result is None

    # There should be created lock instances for the sequential attempts; ensure at least one release called
    releases = [getattr(lock, "released", False) for lock in created_locks]
    assert any(releases), f"Expected at least one lock.release() to be called, got releases={releases}"
