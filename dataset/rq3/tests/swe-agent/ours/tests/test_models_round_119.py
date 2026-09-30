import importlib
from types import SimpleNamespace


def test_sleep_invokes_sleep_when_elapsed_less_than_delay_round_119():
    """When elapsed_time < config.delay, time.sleep should be called with the remaining time
    and GLOBAL_STATS.last_query_timestamp should be updated to the later time returned by time.time().
    """
    models = importlib.import_module("sweagent.agent.models")

    # Create a LiteLLMModel instance without running __init__ and attach a simple config
    inst = object.__new__(models.LiteLLMModel)
    inst.config = SimpleNamespace(delay=2.0)

    # Set up GLOBAL_STATS with a known last_query_timestamp so elapsed_time = 1.0 (< delay)
    models.GLOBAL_STATS.last_query_timestamp = 100.0

    # Make time.time deterministic: first call -> 101.0 (elapsed 1.0), second call -> 103.0 (new timestamp)
    times = [101.0, 103.0]

    def fake_time():
        return times.pop(0)

    sleep_calls = []

    def fake_sleep(arg):
        sleep_calls.append(arg)
        # do not actually sleep

    # Replace real time and sleep and the lock with controlled fakes
    orig_time = models.time.time
    orig_sleep = models.time.sleep
    orig_lock = models.GLOBAL_STATS_LOCK

    class DummyLock:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    models.time.time = fake_time
    models.time.sleep = fake_sleep
    models.GLOBAL_STATS_LOCK = DummyLock()

    try:
        inst._sleep()
    finally:
        # restore
        models.time.time = orig_time
        models.time.sleep = orig_sleep
        models.GLOBAL_STATS_LOCK = orig_lock

    # Expect sleep called with delay - elapsed = 1.0 and last_query_timestamp updated to second fake_time
    assert sleep_calls == [1.0]
    assert models.GLOBAL_STATS.last_query_timestamp == 103.0


def test_sleep_skips_sleep_when_elapsed_ge_delay_round_119():
    """When elapsed_time >= config.delay, time.sleep should NOT be called and the timestamp still updates.
    """
    models = importlib.import_module("sweagent.agent.models")

    inst = object.__new__(models.LiteLLMModel)
    inst.config = SimpleNamespace(delay=2.0)

    # Set last_query_timestamp so elapsed will be 3.0 (>= delay)
    models.GLOBAL_STATS.last_query_timestamp = 100.0

    # time.time first -> 103.0 (elapsed 3.0), second -> 104.0 (new timestamp)
    times = [103.0, 104.0]

    def fake_time():
        return times.pop(0)

    sleep_calls = []

    def fake_sleep(arg):
        sleep_calls.append(arg)

    orig_time = models.time.time
    orig_sleep = models.time.sleep
    orig_lock = models.GLOBAL_STATS_LOCK

    class DummyLock:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    models.time.time = fake_time
    models.time.sleep = fake_sleep
    models.GLOBAL_STATS_LOCK = DummyLock()

    try:
        inst._sleep()
    finally:
        models.time.time = orig_time
        models.time.sleep = orig_sleep
        models.GLOBAL_STATS_LOCK = orig_lock

    # No sleep should have been invoked and timestamp should be updated to the second fake_time value
    assert sleep_calls == []
    assert models.GLOBAL_STATS.last_query_timestamp == 104.0
