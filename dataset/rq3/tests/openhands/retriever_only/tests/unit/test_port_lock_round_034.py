import importlib
import types
import pytest


def _make_fake_system_random_class(values):
    """Create a Fake SystemRandom class whose randint yields values from the provided list."""
    class FakeSystemRandom:
        _iter = iter(())

        @classmethod
        def set_values(cls, vals):
            cls._iter = iter(list(vals))

        def __init__(self):
            # instance uses class iterator
            pass

        def randint(self, a, b):
            try:
                return next(FakeSystemRandom._iter)
            except StopIteration:
                # If values exhausted, default to middle of range for determinism
                return (a + b) // 2

    return FakeSystemRandom


class FakePortLock:
    """A controllable fake PortLock used to simulate acquire/release behavior.

    Controls:
      - FakePortLock.acquire_map: dict port->bool or callable returning bool
      - FakePortLock.available_map: dict port->bool indicating _check_port_available
    """
    acquire_map = {}
    available_map = {}

    def __init__(self, port):
        self.port = port
        self.locked = False

    def acquire(self, timeout=None):
        v = FakePortLock.acquire_map.get(self.port, True)
        if callable(v):
            result = v()
        else:
            result = bool(v)
        self.locked = result
        return result

    def release(self):
        self.locked = False

    def is_locked(self):
        return self.locked


def _patch_module(monkeypatch, values_for_randint, acquire_map=None, available_map=None, module_name="openhands.runtime.utils.port_lock"):
    """Import the target module and apply monkeypatches for deterministic behavior."""
    pl = importlib.import_module(module_name)

    # Patch SystemRandom inside the module to a fake deterministic RNG
    FakeSystemRandom = _make_fake_system_random_class(values_for_randint)
    FakeSystemRandom.set_values(values_for_randint)
    monkeypatch.setattr(pl.random, "SystemRandom", FakeSystemRandom, raising=True)

    # Patch PortLock and _check_port_available
    FakePortLock.acquire_map = acquire_map or {}
    FakePortLock.available_map = available_map or {}
    monkeypatch.setattr(pl, "PortLock", FakePortLock, raising=True)

    def fake_check(port, bind_address):
        # default to True if not specified
        return FakePortLock.available_map.get(port, True)

    monkeypatch.setattr(pl, "_check_port_available", fake_check, raising=True)

    # Avoid real sleeps
    monkeypatch.setattr(pl.time, "sleep", lambda s: None, raising=False)

    return pl


def test_random_attempt_finds_and_locks_port_round_034(monkeypatch):
    """Simulate a successful random attempt: acquire -> True and port available -> True.

    Expect the function to return the chosen port and a lock that reports locked state.
    """
    # Choose values such that the first randint (random attempt) returns 30005
    pl = _patch_module(
        monkeypatch,
        values_for_randint=[30005],
        acquire_map={30005: True},
        available_map={30005: True},
    )

    result = pl.find_available_port_with_lock(min_port=30000, max_port=30010, max_attempts=4)
    assert result is not None, "Expected a (port, lock) tuple when a random attempt succeeds"
    port, lock = result
    assert port == 30005
    # The fake lock sets locked True when acquired
    assert isinstance(lock, FakePortLock)
    assert lock.is_locked() is True


def test_random_attempt_releases_then_sequential_succeeds_round_034(monkeypatch):
    """Simulate a random attempt that acquires but port not available (release), then sequential search finds one.

    Sequence of randint calls:
      - first: random attempt port (30001)
      - second: start_port for sequential (30002)
    """
    # Setup: first random port 30001 will be acquired but not available -> should release
    # Then sequential start_port=30002 which should be acquired and available
    acquire_map = {30001: True, 30002: True}
    available_map = {30001: False, 30002: True}

    pl = _patch_module(
        monkeypatch,
        values_for_randint=[30001, 30002],
        acquire_map=acquire_map,
        available_map=available_map,
    )

    # Use a small max_attempts so random_attempts=1 and remaining_attempts=2 (sequential)
    result = pl.find_available_port_with_lock(min_port=30000, max_port=30010, max_attempts=3)
    assert result is not None, "Expected sequential search to find a port after random attempt released"
    port, lock = result
    assert port == 30002
    assert isinstance(lock, FakePortLock)
    assert lock.is_locked() is True


def test_all_attempts_fail_and_return_none_round_034(monkeypatch):
    """Simulate scenario where no acquire succeeds; function should return None after logging error."""
    # Configure RNG values for random and start_port; both acquire_map entries are False
    acquire_map = {30003: False, 30004: False}
    available_map = {30003: False, 30004: False}

    pl = _patch_module(
        monkeypatch,
        values_for_randint=[30003, 30004],
        acquire_map=acquire_map,
        available_map=available_map,
    )

    result = pl.find_available_port_with_lock(min_port=30000, max_port=30010, max_attempts=2)
    assert result is None
