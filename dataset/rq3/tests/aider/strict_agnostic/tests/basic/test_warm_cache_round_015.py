import os
from types import SimpleNamespace
import time
import aider.coders.base_coder as base_coder

# Minimal fakes
class FakeTimer:
    def __init__(self, interval, fn, *a, **kw):
        self.interval = interval
        self.fn = fn
        self.args = a
        self.kwargs = kw
        self.daemon = False
        self.started = False

    def start(self):
        # record start but do not spawn threads
        self.started = True


class _Usage:
    def __init__(self, prompt_cache_hit_tokens=None, cache_read_input_tokens=None):
        if prompt_cache_hit_tokens is not None:
            self.prompt_cache_hit_tokens = prompt_cache_hit_tokens
        if cache_read_input_tokens is not None:
            self.cache_read_input_tokens = cache_read_input_tokens


class _Completion:
    def __init__(self, usage):
        self.usage = usage


class FakeMainModel:
    def __init__(self, name="fake-model", extra_params=None):
        self.name = name
        self.extra_params = extra_params or {}


class FakeChunks:
    def __init__(self, msgs=None):
        self._msgs = msgs or []

    def cacheable_messages(self):
        return list(self._msgs)


class FakeIO:
    def __init__(self):
        self.warnings = []
        self.outputs = []

    def tool_warning(self, msg):
        self.warnings.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)


# Helper to create a bare Coder instance without running __init__ and populate attributes
def make_coder_instance():
    inst = base_coder.Coder.__new__(base_coder.Coder)
    return inst


def test_warm_cache_returns_early_if_add_cache_headers_false_round_015():
    inst = make_coder_instance()
    inst.add_cache_headers = False
    # Call bound method on a real Coder instance created via __new__
    result = inst.warm_cache(chunks=object())
    assert result is None


def test_warm_cache_returns_early_if_no_pings_round_015():
    inst = make_coder_instance()
    inst.add_cache_headers = True
    inst.num_cache_warming_pings = 0
    result = inst.warm_cache(chunks=object())
    assert result is None


def test_warm_cache_returns_early_if_not_ok_to_warm_round_015():
    inst = make_coder_instance()
    inst.add_cache_headers = True
    inst.num_cache_warming_pings = 2
    inst.ok_to_warm_cache = False
    result = inst.warm_cache(chunks=object())
    assert result is None


def test_warm_cache_returns_if_thread_already_exists_round_015():
    inst = make_coder_instance()
    inst.add_cache_headers = True
    inst.num_cache_warming_pings = 1
    inst.ok_to_warm_cache = True
    inst.cache_warming_thread = object()
    result = inst.warm_cache(chunks=object())
    assert result is None


def test_warm_cache_schedules_timer_and_worker_runs_once_round_015():
    # Prepare instance
    inst = make_coder_instance()
    inst.add_cache_headers = True
    inst.num_cache_warming_pings = 1
    inst.ok_to_warm_cache = True
    inst.verbose = True

    inst.io = FakeIO()
    inst.main_model = FakeMainModel(name="fake", extra_params={})
    chunks = FakeChunks(msgs=[{"role": "system", "content": "ping"}])
    inst.cache_warming_thread = None

    # Monkeypatch Timer and sleep inside module
    orig_timer = base_coder.threading.Timer
    base_coder.threading.Timer = FakeTimer

    orig_sleep = base_coder.time.sleep
    base_coder.time.sleep = lambda s: None

    # Ensure environment path for delay is exercised
    orig_env = os.environ.get("AIDER_CACHE_KEEPALIVE_DELAY")
    os.environ["AIDER_CACHE_KEEPALIVE_DELAY"] = "1.0"

    # Stub litellm.completion to return a completion with tokens and stop the loop
    orig_completion = None
    if hasattr(base_coder, "litellm") and hasattr(base_coder.litellm, "completion"):
        orig_completion = base_coder.litellm.completion

    def fake_completion(*args, **kwargs):
        # stop further warming iterations
        inst.ok_to_warm_cache = False
        return _Completion(_Usage(prompt_cache_hit_tokens=None, cache_read_input_tokens=5))

    if orig_completion is not None:
        base_coder.litellm.completion = fake_completion
    else:
        base_coder.litellm = SimpleNamespace(completion=fake_completion)

    try:
        # Call warm_cache on the instance: should create FakeTimer and return chunks
        ret = inst.warm_cache(chunks)
        assert ret is chunks

        timer = inst.cache_warming_thread
        assert isinstance(timer, FakeTimer)
        # Timer.start was called inside warm_cache
        assert timer.started is True

        # Execute the worker synchronously to exercise inner loop and exception-free path
        timer.fn()

        # After running the worker once, verbose path should have emitted an output
        assert any("Warmed" in o or "cached tokens" in o for o in inst.io.outputs), (
            f"Expected a warmed output message, got {inst.io.outputs}"
        )

    finally:
        # restore monkeypatches and env
        base_coder.threading.Timer = orig_timer
        base_coder.time.sleep = orig_sleep
        if orig_completion is not None:
            base_coder.litellm.completion = orig_completion
        if orig_env is None:
            del os.environ["AIDER_CACHE_KEEPALIVE_DELAY"]
        else:
            os.environ["AIDER_CACHE_KEEPALIVE_DELAY"] = orig_env
