import builtins
import types
import importlib
import pytest

import aider.gui as gui

# Helper to get the underlying function in case of decorators
def _get_get_coder_fn():
    fn = gui.get_coder
    return getattr(fn, "__wrapped__", fn)

class FakeCommands:
    def __init__(self):
        self.io = None

class FakeIO:
    def __init__(self, dry_run=False, encoding="utf-8"):
        self.dry_run = dry_run
        self.encoding = encoding
        self.outputs = []

    def tool_output(self, msg, log_only=False):
        # Match CaptureIO.tool_output signature
        self.outputs.append((msg, log_only))

    def tool_error(self, msg):
        self.outputs.append(("ERROR:" + msg, True))

    def tool_warning(self, msg):
        self.outputs.append(("WARN:" + msg, True))

class FakeCaptureIO:
    def __init__(self, pretty=False, yes=False, dry_run=False, encoding=None):
        # Record constructor args for assertions
        self.pretty = pretty
        self.yes = yes
        self.dry_run = dry_run
        self.encoding = encoding

class FakeCoder:
    def __init__(self, repo=True, dry_run=False, encoding="utf-8", announcements=None):
        self.repo = repo
        # original io used by get_coder when calling coder.io.dry_run and tool_output
        self.io = FakeIO(dry_run=dry_run, encoding=encoding)
        # commands is an object whose io will be replaced by get_coder
        self.commands = FakeCommands()
        self._announcements = announcements or []

    def get_announcements(self):
        return list(self._announcements)


def test_non_coder_raises_round_098(monkeypatch):
    """If cli_main returns something that is not an instance of Coder, get_coder should raise ValueError with that object."""
    # Patch module-level collaborators
    monkeypatch.setattr(gui, "cli_main", lambda return_coder=True: "not-a-coder")
    # Ensure isinstance check uses our FakeCoder class (so str object is not instance)
    monkeypatch.setattr(gui, "Coder", FakeCoder)
    # Use underlying function to avoid cache_resource wrapper issues
    get_coder_fn = _get_get_coder_fn()

    with pytest.raises(ValueError) as excinfo:
        get_coder_fn()
    # ValueError was raised with the offending object; ensure its representation appears
    assert "not-a-coder" in str(excinfo.value)


def test_no_repo_raises_round_098(monkeypatch):
    """If cli_main returns a Coder without a repo, get_coder should raise the repo-related ValueError."""
    # Return a FakeCoder with repo=False
    monkeypatch.setattr(gui, "cli_main", lambda return_coder=True: FakeCoder(repo=False))
    monkeypatch.setattr(gui, "Coder", FakeCoder)
    get_coder_fn = _get_get_coder_fn()

    with pytest.raises(ValueError) as excinfo:
        get_coder_fn()
    assert str(excinfo.value) == "GUI can currently only be used inside a git repo"


def test_success_assigns_io_and_outputs_announcements_round_098(monkeypatch):
    """Normal successful path: CaptureIO is constructed with coder.io settings, assigned to coder.commands.io, and announcements are forwarded to coder.io.tool_output."""
    # Prepare a coder with announcements and known io settings
    announcements = ["first", "second"]
    fake_coder = FakeCoder(repo=True, dry_run=True, encoding="latin-1", announcements=announcements)

    # Patch cli_main to return our fake coder and ensure Coder type check passes
    monkeypatch.setattr(gui, "cli_main", lambda return_coder=True: fake_coder)
    monkeypatch.setattr(gui, "Coder", FakeCoder)
    # Patch CaptureIO so we can observe the constructed io assigned to coder.commands.io
    monkeypatch.setattr(gui, "CaptureIO", FakeCaptureIO)

    get_coder_fn = _get_get_coder_fn()
    returned = get_coder_fn()

    # Function should return the object returned by cli_main
    assert returned is fake_coder

    # The newly constructed CaptureIO should have been assigned to coder.commands.io
    assert isinstance(fake_coder.commands.io, FakeCaptureIO)
    # CaptureIO should have been constructed with the coder.io settings
    assert fake_coder.commands.io.dry_run == fake_coder.io.dry_run
    assert fake_coder.commands.io.encoding == fake_coder.io.encoding

    # Announcements should have been forwarded to the original coder.io.tool_output
    assert fake_coder.io.outputs == [("first", False), ("second", False)]
