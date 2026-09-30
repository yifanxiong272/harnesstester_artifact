import importlib
from pathlib import Path


def _make_recorder():
    called = {"debug": []}
    class Logger:
        def debug(self, msg):
            called["debug"].append(msg)
    return Logger(), called


def test_load_readline_history_no_readline_round_055():
    """If module-level readline is None, the method should return early and not call logger.debug."""
    models = importlib.import_module("sweagent.agent.models")
    orig_readline = getattr(models, "readline", None)
    try:
        # Simulate missing readline module
        models.readline = None

        # Create a minimal 'self' with the attributes used by the method
        dummy = type("D", (), {})()
        dummy._readline_histfile = Path("/this/path/should/not/be/checked")
        dummy.logger, rec = _make_recorder()

        # Call the unbound function directly with our dummy self
        result = models.HumanModel._load_readline_history(dummy)

        # When readline is None, method returns None and does not log
        assert result is None
        assert rec["debug"] == []
    finally:
        # restore module state
        models.readline = orig_readline


def test_load_readline_history_with_readline_and_file_round_055(tmp_path):
    """When readline exists and the histfile exists, read_history_file should be called and logger.debug invoked."""
    models = importlib.import_module("sweagent.agent.models")
    orig_readline = getattr(models, "readline", None)
    try:
        # Create a fake readline object that records calls
        class FakeReadline:
            def __init__(self):
                self.calls = []
            def read_history_file(self, path):
                # record the exact Path passed in
                self.calls.append(path)

        fake = FakeReadline()
        models.readline = fake

        # Create a real temporary file so Path.is_file() returns True
        hist = tmp_path / "history_file"
        hist.write_text("some-history")

        # Create a logger that records debug messages
        recorded = {"debug": []}
        class RecLogger:
            def debug(self, msg):
                recorded["debug"].append(str(msg))

        dummy = type("D", (), {})()
        dummy._readline_histfile = hist
        dummy.logger = RecLogger()

        # Call the method
        models.HumanModel._load_readline_history(dummy)

        # Assert that read_history_file was called with our path
        assert fake.calls == [hist]

        # And that the logger.debug was called with a message containing the path
        assert any(str(hist) in m for m in recorded["debug"]) , "logger.debug should mention the histfile path"
    finally:
        models.readline = orig_readline
