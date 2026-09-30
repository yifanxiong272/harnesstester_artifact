import types
import pytest

import aider.main as m


class FakeIO:
    def __init__(self):
        self.tool_output_calls = []
        self.tool_error_calls = []
        self.offer_url_calls = []
        self.tool_warning_calls = []
        # for test that raises first time
        self._first_output_call = True

    def tool_output(self, msg):
        # default behaviour: record
        self.tool_output_calls.append(msg)

    def tool_error(self, msg):
        self.tool_error_calls.append(msg)

    def offer_url(self, url, msg):
        self.offer_url_calls.append((url, msg))

    def tool_warning(self, msg):
        self.tool_warning_calls.append(msg)


def test_first_run_load_raises_round_135(monkeypatch):
    """
    Simulate load_slow_imports raising during the first-run synchronous import path.
    Expect: io.tool_error called with the exception message, io.tool_output contains the
    error guidance message, io.offer_url invoked with urls.install_properly, and sys.exit
    invoked with code 1 (we patch sys.exit to raise SystemExit so the test can assert).
    """
    io = FakeIO()

    # make load_slow_imports raise
    def fake_load(swallow=False):
        raise Exception("boom")

    # Replace the function in the module under test
    monkeypatch.setattr(m, "load_slow_imports", fake_load)

    # Ensure urls.install_properly is a predictable value in module namespace
    monkeypatch.setattr(m, "urls", types.SimpleNamespace(install_properly="http://install-docs"))

    # Patch sys.exit to raise SystemExit so we can catch and assert it
    monkeypatch.setattr(m.sys, "exit", lambda code: (_ for _ in ()).throw(SystemExit(code)))

    with pytest.raises(SystemExit) as se:
        m.check_and_load_imports(io, is_first_run=True, verbose=True)

    # verify exit code propagated
    assert se.value.code == 1

    # verify io observed the error and guidance output and the offer_url call
    assert io.tool_error_calls and io.tool_error_calls[0] == "boom"
    # one of the outputs should be the guidance text about installing
    assert any("Error loading required imports" in t for t in io.tool_output_calls)
    assert io.offer_url_calls == [("http://install-docs", "Open documentation url for more info?")]


def test_not_first_run_verbose_thread_starts_round_135(monkeypatch):
    """
    When not first run and verbose=True, check_and_load_imports should start a background thread
    which targets load_slow_imports. Patch threading.Thread in module to a factory that records
    the created thread and ensures start() is called deterministically.
    """
    io = FakeIO()

    # Provide a sentinel target function
    def sentinel_load():
        # should not actually run in test
        raise AssertionError("background target should not be executed in this test")

    monkeypatch.setattr(m, "load_slow_imports", sentinel_load)

    # Capture the created thread instance
    created = {}

    class FakeThread:
        def __init__(self, target=None, **kwargs):
            self.target = target
            self.daemon = False
            self.started = False

        def start(self):
            # mark as started but do not call the target
            self.started = True

    def fake_thread_constructor(target=None, **kwargs):
        t = FakeThread(target=target, **kwargs)
        created['t'] = t
        return t

    # Patch threading.Thread used in the module under test
    monkeypatch.setattr(m.threading, "Thread", fake_thread_constructor)

    # Call the function under test
    m.check_and_load_imports(io, is_first_run=False, verbose=True)

    # Assert the verbose message was output
    assert any("Not first run, loading imports in background thread" in t for t in io.tool_output_calls)

    # Assert a thread was created and started, targeting our sentinel function
    assert 't' in created
    thread = created['t']
    assert isinstance(thread, FakeThread)
    assert thread.started is True
    assert thread.target is sentinel_load


def test_outer_exception_triggers_warning_and_full_trace_round_135(monkeypatch):
    """
    Force an exception during the try block (by having io.tool_output raise on first call).
    Expect: the outer except block to call io.tool_warning with an error message and, when
    verbose=True, call io.tool_output again with the formatted traceback. Patch traceback.format_exc
    to a deterministic string to assert output.
    """
    class FlakyIO(FakeIO):
        def __init__(self):
            super().__init__()
            self._first = True

        def tool_output(self, msg):
            # raise only on first invocation to simulate failure inside try-block,
            # allow subsequent invocations so the except handler can call it.
            if self._first:
                self._first = False
                raise RuntimeError("boom")
            self.tool_output_calls.append(msg)

    io = FlakyIO()

    # make sure load_slow_imports exists (not used here because exception happens early)
    monkeypatch.setattr(m, "load_slow_imports", lambda *a, **k: None)

    # Patch traceback.format_exc in the module to a stable value
    monkeypatch.setattr(m.traceback, "format_exc", lambda: "FAKETRACE")

    # Call: this should not raise because outer except handles the error
    m.check_and_load_imports(io, is_first_run=False, verbose=True)

    # io.tool_warning should have been called with the error message that includes the original exception
    assert io.tool_warning_calls, "expected a tool_warning to be called"
    assert any("Error in loading imports" in w and "boom" in w for w in io.tool_warning_calls)

    # The verbose path should cause a call to tool_output with the formatted traceback
    assert any("Full exception details: FAKETRACE" in t for t in io.tool_output_calls)
