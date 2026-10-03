from sweagent.tools.tools import ToolHandler


def test_probe_001():
    """Verify command names with regex metacharacters are treated as literals when searching for the first multiline command.

    We build a minimal config-like object with a command named 'a.b' and include it in
    multi_line_command_endings so ToolHandler exposes a compiled pattern for it. If
    the implementation escapes command names correctly, an action 'axb' should NOT
    match the literal command name 'a.b' and _get_first_multiline_cmd should return None.
    """

    class DummyCommand:
        def __init__(self, name, end_name=None):
            self.name = name
            self.end_name = end_name

    class DummyConfig:
        def __init__(self):
            # Command name intentionally contains a regex metacharacter '.'
            self.commands = [DummyCommand("a.b", end_name=None)]
            # submit_command values must exist because ToolHandler._get_command_patterns builds a submit pattern
            self.submit_command = "__submit__"
            self.submit_command_end_name = "__submit_end__"
            # Ensure the command name is considered by _get_first_multiline_cmd
            self.multi_line_command_endings = {"a.b"}

        def model_copy(self, deep=True):
            # Return self deterministically for simplicity
            return self

    cfg = DummyConfig()
    th = ToolHandler(cfg)

    # Action 'axb' should NOT match the literal command name 'a.b'. If the implementation
    # interpolates the command name into a regex without escaping, '.' will match 'x' and
    # produce a false positive. The correct behavior for a literal-name match is to return None.
    assert th._get_first_multiline_cmd("axb") is None
