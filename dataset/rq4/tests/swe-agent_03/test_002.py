from types import SimpleNamespace

from sweagent.tools.tools import ToolHandler


def test_probe_001():
    """Probe whether a command name containing regex metacharacters is treated literally.

    Invariant: command names are public identifiers and must be matched literally. A name
    containing '.' must not match the literal 'x' when the literal command is 'axb'.

    We construct a fake ToolConfig-like object that ToolHandler will accept (it needs
    a model_copy method and the attributes used by _get_command_patterns/_get_first_multiline_cmd).
    """

    class FakeConfig:
        def __init__(self):
            # Multiline command whose name contains a regex metacharacter '.'
            self.commands = [
                SimpleNamespace(name="a.b", end_name="END"),
                # A different literal command which would match if '.' were treated as wildcard
                SimpleNamespace(name="axb", end_name=None),
            ]
            # Ensure the handler considers the first command as multiline
            self.multi_line_command_endings = ["a.b"]
            # Values required by _get_command_patterns for the submit pattern
            self.submit_command = "__submit__"
            self.submit_command_end_name = "__SUBMIT_END__"

        def model_copy(self, deep: bool = False):
            # ToolHandler calls model_copy(deep=True); return self for simplicity
            return self

    cfg = FakeConfig()
    handler = ToolHandler(cfg)

    # Action begins with the literal command 'axb' and contains the end marker 'END'.
    # If command.name were (incorrectly) treated as a regex, the pattern for 'a.b'
    # would match 'axb' and _get_first_multiline_cmd would return a match object.
    action = """axb
some content
END"""

    match = handler._get_first_multiline_cmd(action)

    # Primary oracle: command names must be matched literally, so no multiline match
    # for the distinct literal 'axb' should be returned for the multiline 'a.b'.
    assert match is None, (
        "Expected no multiline match: the multiline command named 'a.b' must not "
        "match the literal invocation 'axb' if command names are treated literally."
    )
