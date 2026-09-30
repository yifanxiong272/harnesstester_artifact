# file: sweagent/api/server.py:49-82
# asked: {"lines": [51, 52, 53, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 78, 79, 80, 81, 82], "branches": [[68, 69], [68, 70], [78, 79], [78, 81]]}
# gained: {"lines": [51, 52, 53, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 78, 79, 80, 81, 82], "branches": [[68, 69], [78, 79], [78, 81]]}

import io
import types
import traceback as _traceback
import time

import pytest


def _get_server_module():
    import importlib
    return importlib.import_module("sweagent.api.server")


class DummyWU:
    def __init__(self):
        self.log_stream = io.StringIO()
        self.up_log_calls = []
        self.up_agent_calls = []
        self.up_banner_calls = []
        self.finish_run_calls = 0

    def up_log(self, msg):
        self.up_log_calls.append(msg)

    def up_agent(self, msg):
        self.up_agent_calls.append(msg)

    def up_banner(self, msg):
        self.up_banner_calls.append(msg)

    def finish_run(self):
        self.finish_run_calls += 1


def test_run_success_adds_hooks_and_runs(monkeypatch):
    server = _get_server_module()

    # Fake hooks so instantiation is cheap and visible
    class FakeHook:
        def __init__(self, wu):
            self.wu = wu

    monkeypatch.setattr(server, "MainUpdateHook", FakeHook)
    monkeypatch.setattr(server, "AgentUpdateHook", FakeHook)
    monkeypatch.setattr(server, "EnvUpdateHook", FakeHook)

    # Fake RunSingle that records calls
    class FakeRunSingle:
        def __init__(self):
            self.hooks = []
            self.agent = types.SimpleNamespace(add_hook=lambda h: setattr(self, "agent_hook", h))
            self.env = types.SimpleNamespace(add_hook=lambda h: setattr(self, "env_hook", h))
            self.ran = False

        @classmethod
        def from_config(cls, config):
            # verify settings passed through (should just be forwarded)
            # allow config to be any object
            return cls()

        def add_hook(self, h):
            self.hooks.append(h)

        def run(self):
            self.ran = True
            # Write something to stdout/stderr so redirect is exercised
            print("stdout message")
            import sys
            print("stderr message", file=sys.stderr)

    monkeypatch.setattr(server, "RunSingle", FakeRunSingle)

    wu = DummyWU()
    settings = object()

    mt = server.MainThread(settings, wu)  # lines 51-53 executed here

    # Running should not raise and should call the fake run
    mt.run()

    # Assert RunSingle.run was executed
    # We can find the FakeRunSingle instance via hooking into module RunSingle (constructed inside run)
    # But we set it so run sets ran=True on the instance; since instance isn't returned, assert side-effects via expected hooks created
    # Check that MainUpdateHook was added to main via add_hook
    # Our FakeRunSingle.add_hook appends to hooks, so we can assert that at least one hook was appended by verifying that print messages were captured
    # Instead, assert that log_stream captured redirected output
    log_contents = wu.log_stream.getvalue()
    assert "stdout message" in log_contents
    assert "stderr message" in log_contents

    # No error path should have been taken
    assert wu.up_log_calls == []
    assert wu.up_agent_calls == []
    assert wu.up_banner_calls == []
    assert wu.finish_run_calls == 0


def test_run_exception_truncates_and_reports_and_reraises(monkeypatch):
    server = _get_server_module()

    # Replace hooks with simple classes to avoid unexpected behavior
    class FakeHook:
        def __init__(self, wu):
            self.wu = wu

    monkeypatch.setattr(server, "MainUpdateHook", FakeHook)
    monkeypatch.setattr(server, "AgentUpdateHook", FakeHook)
    monkeypatch.setattr(server, "EnvUpdateHook", FakeHook)

    # Make a RunSingle whose run raises an exception with a long message to trigger truncation
    class FakeRunSingleErr:
        def __init__(self, msg):
            self._msg = msg
            self.agent = types.SimpleNamespace(add_hook=lambda h: None)
            self.env = types.SimpleNamespace(add_hook=lambda h: None)

        @classmethod
        def from_config(cls, config):
            return cls(config)

        def add_hook(self, h):
            pass

        def run(self):
            raise Exception(self._msg)

    # Create a long message > 350 chars
    long_msg = "X" * 400
    monkeypatch.setattr(server, "RunSingle", FakeRunSingleErr)

    wu = DummyWU()
    settings = long_msg  # pass the message through as config so FakeRunSingleErr.from_config receives it

    mt = server.MainThread(settings, wu)

    # Run should raise; check that it raises the original exception (propagated after handling)
    with pytest.raises(Exception) as excinfo:
        mt.run()

    assert long_msg in str(excinfo.value)

    # After exception, up_log should have been called with a traceback string
    assert len(wu.up_log_calls) == 1
    tb_str = wu.up_log_calls[0]
    assert "Traceback" in tb_str or "Exception" in tb_str

    # up_agent should have been called with truncated message
    assert len(wu.up_agent_calls) == 1
    agent_msg = wu.up_agent_calls[0]
    assert agent_msg.startswith("Error: ")
    short_msg = agent_msg[len("Error: "):]
    # It should be truncated to max_len (350) and contain the ellipsis note
    assert short_msg.endswith("... (see log for details)")
    assert len(short_msg) <= 350 + len("... (see log for details)")

    # up_banner should have been called with prefix
    assert len(wu.up_banner_calls) == 1
    assert wu.up_banner_calls[0].startswith("Critical error: ")

    # finish_run should have been called once
    assert wu.finish_run_calls == 1


def test_stop_calls_finish_and_up_agent(monkeypatch):
    server = _get_server_module()

    wu = DummyWU()
    mt = server.MainThread(object(), wu)

    # We will simulate is_alive returning True once then False
    states = {"calls": 0}

    def fake_is_alive():
        states["calls"] += 1
        # Return True on first call, False afterwards
        return states["calls"] == 1

    called = {"raised": 0}

    def fake_raise_exc(exc):
        # Instead of raising into the thread, just record that it was called
        called["raised"] += 1

    monkeypatch.setattr(mt, "is_alive", fake_is_alive)
    monkeypatch.setattr(mt, "raise_exc", fake_raise_exc)
    # Speed up the loop by avoiding real sleep
    monkeypatch.setattr(time, "sleep", lambda s: None)

    # Call stop(), should exit the loop after one iteration and call finish_run and up_agent
    mt.stop()

    # raise_exc should have been called at least once
    assert called["raised"] >= 1

    # finish_run and up_agent should be called
    assert wu.finish_run_calls == 1
    assert wu.up_agent_calls == ["Run stopped by user"]
