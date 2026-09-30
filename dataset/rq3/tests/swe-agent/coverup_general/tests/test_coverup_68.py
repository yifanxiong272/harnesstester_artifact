# file: sweagent/tools/tools.py:151-175
# asked: {"lines": [165, 166, 167, 168, 169, 171], "branches": [[157, 162], [164, 165]]}
# gained: {"lines": [165, 166, 167, 168, 169, 171], "branches": [[164, 165]]}

import pytest
from pathlib import Path

from sweagent.tools.tools import ToolConfig
from sweagent.tools.commands import Command, BASH_COMMAND


class DummyBundle:
    def __init__(self, path: Path, commands: list[Command]):
        self.path = path
        self._commands = list(commands)

    @property
    def commands(self):
        return list(self._commands)


def test_commands_includes_bash_and_bundle_commands(monkeypatch):
    # Prevent model_post_init from running during construct
    monkeypatch.setattr(ToolConfig, "model_post_init", lambda self, __context: None)

    # Prepare a custom command that does not conflict with bash
    custom_cmd = Command(name="my_custom_tool", docstring="Do custom stuff")
    bundle = DummyBundle(Path("bundle_path"), [custom_cmd])

    cfg = ToolConfig.construct(bundles=[bundle], enable_bash_tool=True)

    cmds = cfg.commands  # triggers cached_property and actual logic

    # Validate that BASH_COMMAND is present and our custom command is present
    names = [c.name for c in cmds]
    assert BASH_COMMAND.name in names, "BASH_COMMAND should be included when enable_bash_tool is True"
    assert "my_custom_tool" in names, "Custom bundle command should be included"
    # Ensure ordering: BASH_COMMAND should be first (added before bundle commands)
    assert names[0] == BASH_COMMAND.name


def test_duplicate_command_definition_raises_value_error(monkeypatch):
    # Prevent model_post_init from running during construct so we can control when commands() runs
    monkeypatch.setattr(ToolConfig, "model_post_init", lambda self, __context: None)

    # Create two bundles that both define the same command name
    dup_name = "duplicate_tool"
    cmd1 = Command(name=dup_name, docstring="first")
    cmd2 = Command(name=dup_name, docstring="second")

    bundle1 = DummyBundle(Path("first_bundle_path"), [cmd1])
    bundle2 = DummyBundle(Path("second_bundle_path"), [cmd2])

    cfg = ToolConfig.construct(bundles=[bundle1, bundle2], enable_bash_tool=True)

    with pytest.raises(ValueError) as excinfo:
        _ = cfg.commands

    msg = str(excinfo.value)
    assert "defined multiple times" in msg
    # Message should reference both the first definition path and the duplicate bundle path
    assert "first_bundle_path" in msg
    assert "second_bundle_path" in msg
