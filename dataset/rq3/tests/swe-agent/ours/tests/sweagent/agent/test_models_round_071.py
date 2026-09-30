import threading
import sweagent.agent.models as models
import pytest


def _make_fake(api_keys, choose_by_thread):
    class Fake:
        pass

    f = Fake()
    f.choose_api_key_by_thread = choose_by_thread
    f.get_api_keys = lambda: api_keys
    return f


def test_choose_api_key_none_round_071():
    """When get_api_keys() returns an empty collection, choose_api_key should return None."""
    fake = _make_fake([], False)
    # Ensure global thread tracking is isolated for the test
    setattr(models, "_THREADS_THAT_USED_API_KEYS", [])

    func = models.GenericAPIModelConfig.choose_api_key
    res = func(fake)
    assert res is None


def test_choose_api_key_random_choice_round_071(monkeypatch):
    """When choose_api_key_by_thread is False, random.choice is used deterministically via monkeypatch."""
    fake = _make_fake(["a", "b", "c"], False)
    setattr(models, "_THREADS_THAT_USED_API_KEYS", [])

    # Patch random.choice to be deterministic
    monkeypatch.setattr(models.random, "choice", lambda lst: lst[1])

    func = models.GenericAPIModelConfig.choose_api_key
    res = func(fake)

    assert res == "b"
    # Thread tracking should not be modified when not choosing by thread
    assert getattr(models, "_THREADS_THAT_USED_API_KEYS") == []


def test_choose_api_key_threaded_round_071():
    """When choose_api_key_by_thread is True, the current thread name is registered and used to pick the key index."""
    fake = _make_fake(["k1", "k2", "k3"], True)
    # Reset global tracking list
    setattr(models, "_THREADS_THAT_USED_API_KEYS", [])

    func = models.GenericAPIModelConfig.choose_api_key

    # Temporarily set a deterministic thread name for the current thread
    current = threading.current_thread()
    original_name = current.name
    current.name = "DeterministicTestThread-071"
    try:
        res = func(fake)
        # After first use, the thread name should have been appended
        assert getattr(models, "_THREADS_THAT_USED_API_KEYS") == ["DeterministicTestThread-071"]
        # As this is the first thread appended, thread_idx == 0 -> selects api_keys[0]
        assert res == "k1"
    finally:
        # Restore thread name to avoid side effects on other tests
        current.name = original_name
