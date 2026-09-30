import builtins
import tempfile
from pathlib import Path
from aider.commands import Commands, SwitchCoder


class FakeIO:
    def __init__(self):
        self.encoding = "utf-8"
        self.tool_error_msgs = []
        self.tool_output_msgs = []

    def tool_error(self, msg):
        # capture error messages for assertions
        self.tool_error_msgs.append(msg)

    def tool_output(self, msg):
        # capture output messages for assertions
        self.tool_output_msgs.append(msg)


def make_commands_instance():
    # Create Commands instance without running its real __init__ and attach a fake io
    cmd_obj = object.__new__(Commands)
    cmd_obj.io = FakeIO()
    return cmd_obj


def test_cmd_load_empty_args_round_161():
    cmd_obj = make_commands_instance()

    # calling with only whitespace should trigger the early-tool-error branch
    cmd_obj.cmd_load("   ")

    assert len(cmd_obj.io.tool_error_msgs) == 1
    assert (
        "Please provide a filename containing commands to load." in cmd_obj.io.tool_error_msgs[0]
    )


def test_cmd_load_file_not_found_round_161():
    cmd_obj = make_commands_instance()

    # Provide a filename that very likely doesn't exist to trigger FileNotFoundError
    filename = "nonexistent-file-for-test-unique-12345.txt"
    # Use the raw filename (not stripped) to match the message formatting in the code
    cmd_obj.cmd_load(filename)

    assert len(cmd_obj.io.tool_error_msgs) == 1
    assert cmd_obj.io.tool_error_msgs[0] == f"File not found: {filename}"


def test_cmd_load_open_raises_generic_round_161(monkeypatch):
    cmd_obj = make_commands_instance()

    # Patch builtins.open to raise a generic exception to exercise the generic except branch
    def fake_open(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(builtins, "open", fake_open)

    cmd_obj.cmd_load("some-file.txt")

    assert len(cmd_obj.io.tool_error_msgs) == 1
    # The code reports the exception message using f"Error reading file: {e}"
    assert "Error reading file: boom" in cmd_obj.io.tool_error_msgs[0]


def test_cmd_load_execute_and_switchcoder_round_161(tmp_path):
    # Create a temporary commands file containing blank lines, comments, and two commands
    p = tmp_path / "commands.txt"
    contents = "\n# this is a comment\ndo-something\nother-command\n"
    p.write_text(contents, encoding="utf-8")

    cmd_obj = make_commands_instance()

    called = []

    def run_fn(command_str):
        # record each run invocation
        called.append(command_str)
        if command_str == "do-something":
            # Simulate an interactive-only command being invoked in non-interactive mode
            raise SwitchCoder()
        return "ok"

    cmd_obj.run = run_fn

    # Execute with the path to the temporary file
    cmd_obj.cmd_load(str(p))

    # The blank line and the comment should be skipped; only two commands executed
    assert called == ["do-something", "other-command"]

    # tool_output should have entries for executing the two non-skipped commands
    assert cmd_obj.io.tool_output_msgs == ["\nExecuting: do-something", "\nExecuting: other-command"]

    # When the SwitchCoder was raised for 'do-something', the code should have reported a tool_error
    assert any(
        "only supported in interactive mode" in m for m in cmd_obj.io.tool_error_msgs
    )
