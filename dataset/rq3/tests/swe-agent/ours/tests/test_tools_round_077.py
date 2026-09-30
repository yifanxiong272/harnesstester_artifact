import importlib
from pathlib import Path
import pytest

# Import the module under test
tools = importlib.import_module('sweagent.tools.tools')
# Access the original function object wrapped by cached_property to call it on simple dummies
orig_commands_func = tools.ToolConfig.__dict__['commands'].func


class FakeCommand:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"FakeCommand({self.name!r})"


class FakeBundle:
    def __init__(self, commands, path):
        # commands: iterable of objects with .name
        self.commands = list(commands)
        # path should be Path-like in the code under test
        self.path = Path(path)


class DummySelf:
    def __init__(self, enable_bash_tool, bundles):
        self.enable_bash_tool = enable_bash_tool
        self.bundles = list(bundles)


def test_commands_includes_bash_round_077(monkeypatch):
    """
    When enable_bash_tool is True and there are no bundles, the returned
    commands list should include the BASH_COMMAND (patched) as the first element.
    This covers the branch that adds the builtin bash command (lines ~157-162).
    """
    fake_bash = FakeCommand('bash-tool')
    monkeypatch.setattr(tools, 'BASH_COMMAND', fake_bash)

    dummy = DummySelf(enable_bash_tool=True, bundles=[])
    res = orig_commands_func(dummy)

    assert isinstance(res, list)
    # The patched BASH_COMMAND object should be appended first
    assert res[0] is fake_bash
    assert len(res) == 1


def test_duplicate_detection_with_bash_collision_round_077(monkeypatch):
    """
    If a bundle defines a command with the same name as the builtin
    BASH_COMMAND, the code should detect the duplicate and raise a ValueError
    including both the first and duplicate declaration locations. This hits
    the branch that raises on duplicate definitions (lines ~164-171).
    """
    # Make the builtin name collide with a bundle-provided command
    fake_bash = FakeCommand('dupname')
    monkeypatch.setattr(tools, 'BASH_COMMAND', fake_bash)

    # Bundle that defines a command with the same name
    colliding_bundle = FakeBundle([FakeCommand('dupname')], 'duplicate_bundle_path')
    dummy = DummySelf(enable_bash_tool=True, bundles=[colliding_bundle])

    with pytest.raises(ValueError) as excinfo:
        orig_commands_func(dummy)

    msg = str(excinfo.value)
    # Message should mention the first definition (the builtin) and the duplicate bundle path
    assert 'First definition' in msg
    assert '<builtin>' in msg  # existing_source is Path('<builtin>') in the implementation
    assert 'duplicate_bundle_path' in msg


def test_bundle_command_appended_round_077(monkeypatch):
    """
    When enable_bash_tool is False and a single bundle defines a unique
    command name, the command should be appended to the resulting list.
    This exercises the non-duplicate append path (covering the branch that
    does not raise at 164->165).
    """
    # Patch BASH_COMMAND to avoid depending on real constant shape (not used because disabled)
    monkeypatch.setattr(tools, 'BASH_COMMAND', FakeCommand('irrelevant'))

    cmd = FakeCommand('unique')
    bundle = FakeBundle([cmd], 'bundle_one')
    dummy = DummySelf(enable_bash_tool=False, bundles=[bundle])

    res = orig_commands_func(dummy)
    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0] is cmd
    assert res[0].name == 'unique'
