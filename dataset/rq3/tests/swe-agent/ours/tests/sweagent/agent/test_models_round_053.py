import types
import sweagent.agent.models as models


class FakePath:
    def __init__(self, path: str, exists: bool):
        self._p = path
        self._exists = exists

    def is_file(self) -> bool:
        return self._exists

    def __str__(self) -> str:
        return self._p


class FakeLogger:
    def __init__(self):
        self.msgs = []

    def debug(self, msg: str) -> None:
        self.msgs.append(msg)


class FakeReadline:
    def __init__(self):
        self.called_with = None

    def read_history_file(self, path):
        # record the exact object passed in so tests can assert identity
        self.called_with = path


def test_readline_none_round_053(monkeypatch):
    """When the module-level `readline` is None, the method returns early and does nothing."""
    # Patch the symbol where the implementation resolves it
    monkeypatch.setattr(models, "readline", None)

    fake_self = types.SimpleNamespace()
    # Provide attributes that _load_readline_history would normally access if it proceeded
    fake_self._readline_histfile = FakePath("/should/not/be/used", True)
    fake_self.logger = FakeLogger()

    # Should return None and not raise
    result = models.HumanModel._load_readline_history(fake_self)
    assert result is None
    # logger.debug must not be called because function returns early
    assert fake_self.logger.msgs == []


def test_readline_no_file_round_053(monkeypatch):
    """When readline exists but the histfile does not, read_history_file is not called."""
    fake_readline = FakeReadline()
    monkeypatch.setattr(models, "readline", fake_readline)

    fake_path = FakePath("/tmp/does_not_exist", False)
    fake_logger = FakeLogger()
    fake_self = types.SimpleNamespace(_readline_histfile=fake_path, logger=fake_logger)

    result = models.HumanModel._load_readline_history(fake_self)
    assert result is None
    # readline.read_history_file should not be called because is_file() is False
    assert fake_readline.called_with is None
    # logger.debug should not be called either
    assert fake_logger.msgs == []


def test_readline_loads_file_round_053(monkeypatch):
    """When readline exists and histfile exists, the history file is loaded and logger.debug is called."""
    fake_readline = FakeReadline()
    monkeypatch.setattr(models, "readline", fake_readline)

    fake_path = FakePath("/tmp/history_file", True)
    fake_logger = FakeLogger()
    fake_self = types.SimpleNamespace(_readline_histfile=fake_path, logger=fake_logger)

    models.HumanModel._load_readline_history(fake_self)

    # read_history_file must be called with the same object passed to the method
    assert fake_readline.called_with is fake_path
    # logger.debug must have been called once and include the path string
    assert len(fake_logger.msgs) == 1
    assert "/tmp/history_file" in fake_logger.msgs[0]
