import pytest
from aider.commands import Commands


class FakeIO:
    def __init__(self):
        self.outputs = []

    def tool_output(self, text=None):
        # record the exact argument (None when called without args)
        self.outputs.append(text)


class FakeSelf:
    def __init__(self, commands):
        # store commands in unsorted order to ensure Commands.basic_help sorts them
        self._commands = commands
        self.io = FakeIO()

    def get_commands(self):
        return self._commands


# define a command method with a docstring to exercise the "has description" branch
def cmd_do_it():
    """Does it"""


def test_basic_help_mixed_commands_round_102():
    # Provide commands in unsorted order so sorting behavior is validated
    cmds = ["/do-it", "/a"]
    fake = FakeSelf(cmds)

    # attach the command handler that should be discovered by basic_help
    # name must match f"cmd_{command[1:]}".replace("-", "_") => 'cmd_do_it'
    setattr(fake, "cmd_do_it", cmd_do_it)

    # Call the function under test (unbound function, pass our fake self)
    Commands.basic_help(fake)

    # Reconstruct expected outputs deterministically using the same formatting semantics
    sorted_cmds = sorted(cmds)
    pad = max(len(c) for c in sorted_cmds)
    pad_fmt = "{cmd:" + str(pad) + "}"

    expected = []
    for c in sorted_cmds:
        method_name = f"cmd_{c[1:]}".replace("-", "_")
        if hasattr(fake, method_name):
            description = getattr(fake, method_name).__doc__
            expected.append(f"{pad_fmt.format(cmd=c)} {description}")
        else:
            expected.append(f"{pad_fmt.format(cmd=c)} No description available.")

    # After the loop, basic_help calls tool_output() with no args and then a help hint
    expected.append(None)
    expected.append("Use `/help <question>` to ask questions about how to use aider.")

    # Assert that the recorded io outputs match the expected sequence exactly
    assert fake.io.outputs == expected
