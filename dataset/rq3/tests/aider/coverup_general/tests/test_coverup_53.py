# file: aider/gui.py:69-89
# asked: {"lines": [69, 70, 71, 72, 73, 74, 75, 77, 78, 79, 80, 81, 84, 86, 87, 89], "branches": [[72, 73], [72, 74], [74, 75], [74, 77], [86, 87], [86, 89]]}
# gained: {"lines": [69, 70, 71, 72, 73, 74, 75, 77, 78, 79, 80, 81, 84, 86, 87, 89], "branches": [[72, 73], [72, 74], [74, 75], [74, 77], [86, 87], [86, 89]]}

import importlib
import sys
import types
import pytest

# Ensure a minimal streamlit is available before importing aider.gui
if "streamlit" not in sys.modules:
    fake_st = types.ModuleType("streamlit")
    # simple identity decorator to avoid caching behavior in tests
    def cache_resource(func=None, **kwargs):
        if func is None:
            def _decorator(f):
                return f
            return _decorator
        return func
    fake_st.cache_resource = cache_resource
    sys.modules["streamlit"] = fake_st

def _reload_gui():
    # reload to ensure tests run with fresh state and our monkeypatches apply cleanly
    return importlib.reload(importlib.import_module("aider.gui"))

def test_get_coder_non_coder_raises(monkeypatch):
    mod = _reload_gui()
    # cli_main returns a non-Coder value
    monkeypatch.setattr(mod, "cli_main", lambda return_coder=True: "not-a-coder")
    with pytest.raises(ValueError) as excinfo:
        mod.get_coder()
    assert str(excinfo.value) == "not-a-coder"

def test_get_coder_not_repo_raises(monkeypatch):
    mod = _reload_gui()

    # Create a dummy Coder class and instance that fails the repo check
    class DummyCoder:
        def __init__(self):
            self.repo = False

    monkeypatch.setattr(mod, "Coder", DummyCoder)
    monkeypatch.setattr(mod, "cli_main", lambda return_coder=True: DummyCoder())

    with pytest.raises(ValueError) as excinfo:
        mod.get_coder()
    assert str(excinfo.value) == "GUI can currently only be used inside a git repo"

def test_get_coder_success_sets_io_and_outputs_announcements(monkeypatch):
    mod = _reload_gui()

    # Prepare a dummy coder that satisfies checks and records tool_output calls
    announcements = ["line one", "line two", "last line"]
    recorded_outputs = []

    class DummyIO:
        def __init__(self):
            self.dry_run = False
            self.encoding = "utf-8"
        def tool_output(self, line):
            recorded_outputs.append(line)

    class DummyCommands:
        def __init__(self):
            self.io = None

    class DummyCoder:
        def __init__(self):
            self.repo = True
            self.io = DummyIO()
            self.commands = DummyCommands()
            self._announcements = list(announcements)
        def get_announcements(self):
            # return an iterable of lines
            return list(self._announcements)

    # Ensure isinstance check passes against our DummyCoder
    monkeypatch.setattr(mod, "Coder", DummyCoder)

    # Return the same instance so we can test identity
    coder_instance = DummyCoder()
    monkeypatch.setattr(mod, "cli_main", lambda return_coder=True: coder_instance)

    coder = mod.get_coder()

    # Returned coder should be our dummy instance
    assert isinstance(coder, DummyCoder)
    # commands.io should have been replaced with a CaptureIO instance from the module
    assert hasattr(coder.commands, "io")
    assert type(coder.commands.io).__name__ == getattr(mod, "CaptureIO").__name__
    # The original coder.io.tool_output should have been called for each announcement
    assert recorded_outputs == announcements
    # The returned coder should be the same object that cli_main returned
    assert coder is coder_instance
