import os
import types
import builtins
import threading

import aider.coders.base_coder as base_coder


class DummyIO:
    def __init__(self):
        self.warnings = []
        self.outputs = []

    def tool_warning(self, msg):
        self.warnings.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)


class _CompletionUsage:
    def __init__(self, prompt_cache_hit_tokens=None, cache_read_input_tokens=None):
        if prompt_cache_hit_tokens is not None:
            self.prompt_cache_hit_tokens = prompt_cache_hit_tokens
        if cache_read_input_tokens is not None:
            self.cache_read_input_tokens = cache_read_input_tokens


class _Completion:
    def __init__(self, usage):
        self.usage = usage


def test_warm_cache_early_return_add_cache_headers_round_014():
    # If add_cache_headers is False, warm_cache should return immediately (cover lines ~1341-1342)
    self_obj = types.SimpleNamespace()
    self_obj.add_cache_headers = False

    # Call the function directly with a dummy chunks object
    chunks = object()
    result = base_coder.Coder.warm_cache(self_obj, chunks)

    assert result is None


def test_warm_cache_thread_exists_sets_attrs_then_returns_round_014():
    # When cache_warming_thread already exists, warm_cache should set timing attributes
    # (lines ~1348-1355) but then return before spawning a new timer.
    prev_env = dict(os.environ)
    try:
        os.environ["AIDER_CACHE_KEEPALIVE_DELAY"] = "0"

        io = DummyIO()
        main_model = types.SimpleNamespace(extra_params={}, name="m")
        chunks = types.SimpleNamespace(cacheable_messages=lambda: ["a"])

        self_obj = types.SimpleNamespace(
            add_cache_headers=True,
            num_cache_warming_pings=3,
            ok_to_warm_cache=True,
            cache_warming_thread=object(),  # already present -> should trigger early return at 1354
            main_model=main_model,
            io=io,
            verbose=False,
            warming_pings_left=None,
            next_cache_warm=None,
            cache_warming_chunks=None,
        )

        result = base_coder.Coder.warm_cache(self_obj, chunks)

        # Should return the chunks (function returns chunks at end) OR None because of early return.
        # The branch at 1354 returns before starting a new thread but after setting next_cache_warm/etc.
        # According to source, it returns (no explicit value), so Python returns None.
        assert result is None

        # But attributes set before the 1354 check must have been assigned
        assert isinstance(self_obj.next_cache_warm, float)
        assert self_obj.warming_pings_left == 3
        assert self_obj.cache_warming_chunks is chunks
    finally:
        os.environ.clear()
        os.environ.update(prev_env)


def test_warm_cache_worker_handles_exception_and_success_round_014():
    # Cover the worker loop including the exception branch (lines ~1372-1381)
    # and the successful completion and verbose output (lines ~1383-1388).
    prev_env = dict(os.environ)
    try:
        # Make delay 0 so next_cache_warm is immediately reachable in worker loop.
        os.environ["AIDER_CACHE_KEEPALIVE_DELAY"] = "0"

        io = DummyIO()
        # simple main_model with extra_params to be copied into kwargs in worker
        main_model = types.SimpleNamespace(extra_params={"foo": "bar"}, name="testmodel")
        chunks = types.SimpleNamespace(cacheable_messages=lambda: [{"role": "user", "content": "x"}])

        # The fake self object used as 'self' for the method
        self_obj = types.SimpleNamespace(
            add_cache_headers=True,
            num_cache_warming_pings=2,
            ok_to_warm_cache=True,
            cache_warming_thread=None,
            main_model=main_model,
            io=io,
            verbose=True,
            warming_pings_left=0,
            next_cache_warm=0.0,
            cache_warming_chunks=None,
        )

        # Patch module-level threading.Timer so that it runs the worker synchronously.
        class DummyTimer:
            def __init__(self, interval, target):
                self.interval = interval
                self.target = target
                self.daemon = False

            def start(self):
                # Run worker synchronously. The worker itself will exit when ok_to_warm_cache becomes False.
                self.target()

        orig_timer = base_coder.threading.Timer
        base_coder.threading.Timer = DummyTimer

        # Patch sleep to no-op so loop isn't delayed
        orig_sleep = base_coder.time.sleep
        base_coder.time.sleep = lambda s: None

        # Control time.time: we can use actual time; since delay was set to 0, equality works.
        # But to be deterministic, provide a fixed time function.
        fake_time = [1000.0]

        def fake_time_fn():
            # Return current time and increment slightly each call to simulate progression
            v = fake_time[0]
            fake_time[0] += 0.1
            return v

        orig_time = base_coder.time.time
        base_coder.time.time = fake_time_fn

        # Patch format_tokens to produce deterministic output
        orig_format_tokens = base_coder.format_tokens
        base_coder.format_tokens = lambda n: f"{n}"

        # litellm.completion should raise on first call (to hit exception branch) and succeed on second
        call_count = {"n": 0}

        def fake_completion(*, model, messages, stream=False, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise Exception("boom")
            # On second call, produce a completion object with usage.prompt_cache_hit_tokens
            usage = _CompletionUsage(prompt_cache_hit_tokens=3)
            # After producing a successful completion, stop the worker loop
            self_obj.ok_to_warm_cache = False
            return _Completion(usage=usage)

        orig_completion = base_coder.litellm.completion
        base_coder.litellm.completion = fake_completion

        # Now call the method under test. It should synchronously run the worker via DummyTimer.
        returned = base_coder.Coder.warm_cache(self_obj, chunks)

        # The method returns the chunks at normal completion (source ends with 'return chunks')
        assert returned is chunks

        # The exception path should have produced a warning message
        assert any("Cache warming error: boom" in w for w in io.warnings)

        # The successful path should have produced a verbose output mentioning warmed tokens
        assert any("Warmed 3 cached tokens." in o for o in io.outputs)

        # Ensure that completion was called at least twice (one failure, one success)
        assert call_count["n"] >= 2

    finally:
        # restore patched objects
        base_coder.threading.Timer = orig_timer
        base_coder.time.sleep = orig_sleep
        base_coder.time.time = orig_time
        base_coder.format_tokens = orig_format_tokens
        base_coder.litellm.completion = orig_completion
        os.environ.clear()
        os.environ.update(prev_env)
