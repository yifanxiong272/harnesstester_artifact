# file: aider/main.py:1226-1253
# asked: {"lines": [1235, 1236, 1237, 1238, 1239, 1245, 1250, 1251, 1252, 1253], "branches": [[1244, 1245], [1252, 0], [1252, 1253]]}
# gained: {"lines": [1235, 1236, 1237, 1238, 1239, 1245, 1250, 1251, 1252, 1253], "branches": [[1244, 1245], [1252, 1253]]}

import pytest
import types
import traceback as _traceback

from aider import urls
import aider.main as main_module


class DummyIO:
    def __init__(self):
        self.errors = []
        self.outputs = []
        self.warnings = []
        self.offers = []

    def tool_error(self, msg):
        self.errors.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)

    def offer_url(self, url, prompt):
        self.offers.append((url, prompt))

    def tool_warning(self, msg):
        self.warnings.append(msg)


def test_first_run_load_imports_failure_exits(monkeypatch):
    """Trigger the inner except: load_slow_imports raises -> tool_error, tool_output, offer_url, sys.exit(1)"""
    io = DummyIO()

    def fake_load_slow_imports(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(main_module, "load_slow_imports", fake_load_slow_imports)

    with pytest.raises(SystemExit) as excinfo:
        main_module.check_and_load_imports(io, is_first_run=True, verbose=False)

    # sys.exit(1) should have been called
    assert excinfo.value.code == 1

    # tool_error got the exception string
    assert any("boom" in e for e in io.errors), f"expected 'boom' in errors, got {io.errors}"

    # tool_output should include the install message
    assert any("Error loading required imports. Did you install aider properly?" in o for o in io.outputs), io.outputs

    # offer_url should have been called with urls.install_properly
    assert any(url == urls.install_properly for url, _ in io.offers), f"offers={io.offers}"


def test_not_first_run_starts_background_thread_and_runs_imports(monkeypatch):
    """Ensure the 'Not first run...' verbose message is emitted and the target function runs."""
    io = DummyIO()
    ran = {"flag": False}

    def fake_load_slow_imports():
        # mark that it ran
        ran["flag"] = True

    monkeypatch.setattr(main_module, "load_slow_imports", fake_load_slow_imports)

    # Replace threading.Thread with a dummy that calls the target synchronously on start()
    class DummyThread:
        def __init__(self, target=None):
            self._target = target
            self.daemon = False

        def start(self):
            if self._target:
                self._target()

    monkeypatch.setattr(main_module, "threading", types.SimpleNamespace(Thread=DummyThread))

    main_module.check_and_load_imports(io, is_first_run=False, verbose=True)

    # verbose output for not-first-run should be present
    assert any("Not first run, loading imports in background thread" in o for o in io.outputs), io.outputs

    # load_slow_imports should have been executed by our DummyThread.start()
    assert ran["flag"] is True


def test_outer_exception_caught_and_verbose_traceback_shown(monkeypatch):
    """Trigger an exception in creating the thread to hit the outer except block and verbose traceback output."""
    io = DummyIO()

    # Make threading.Thread raise during instantiation to cause an exception inside the try block
    class RaisingThread:
        def __init__(self, *args, **kwargs):
            raise ValueError("thread fail")

    monkeypatch.setattr(main_module, "threading", types.SimpleNamespace(Thread=RaisingThread))

    # Ensure load_slow_imports exists so import lookup doesn't fail elsewhere
    monkeypatch.setattr(main_module, "load_slow_imports", lambda: None)

    # Call with verbose True to cause tool_output of full traceback in outer except
    main_module.check_and_load_imports(io, is_first_run=False, verbose=True)

    # tool_warning should have been called with message containing the exception text
    assert any("thread fail" in w for w in io.warnings), f"warnings={io.warnings}"

    # When verbose, tool_output should have been called with full exception details (traceback text)
    # The message includes 'Full exception details:' per implementation
    assert any("Full exception details:" in o for o in io.outputs), f"outputs={io.outputs}"
    # And also should contain 'Traceback' content from format_exc
    assert any("Traceback" in o for o in io.outputs), f"outputs={io.outputs}"
