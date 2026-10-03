def test_probe_001():
    """When rendered lines are fewer-or-equal to live_window, live.update must receive the full rendered text, not a truncated suffix.

    This constructs a MarkdownStream, stubs its renderer to return 4 lines while live_window is 5
    (so num_lines becomes negative in the target implementation), and replaces the live object with
    a deterministic stub that records update(...) calls. The primary assertion checks that the
    live.update payload contains the full joined text of all rendered lines.
    """

    from types import SimpleNamespace

    # Import only the public entrypoint/class
    from aider.mdstream import MarkdownStream

    class LiveStub:
        def __init__(self):
            # records values passed to update()
            self.update_calls = []
            # emulate a console with a print method that records calls
            self.console = SimpleNamespace()
            self.console.print_calls = []
            def _console_print(arg):
                self.console.print_calls.append(arg)
            self.console.print = _console_print

        def update(self, value):
            self.update_calls.append(value)

    # Deterministic rendered lines with preserved line endings (matching _render_markdown_to_lines contract)
    rendered_lines = ["line1\n", "line2\n", "line3\n", "line4\n"]

    # Construct the stream and set up deterministic state
    stream = MarkdownStream()
    stream.live_window = 5
    stream.printed = []

    # Prevent the method from creating a real Live instance on first update
    stream._live_started = True
    stub = LiveStub()
    stream.live = stub

    # Replace rendering with a deterministic fixed output
    stream._render_markdown_to_lines = lambda text: list(rendered_lines)

    # Call the entrypoint under test
    stream.update("ignored text", final=False)

    # Primary observable: live.update must have been called exactly once
    assert len(stub.update_calls) == 1, f"expected one live.update call, got {len(stub.update_calls)}"

    # Extract the argument and obtain its textual content robustly
    arg = stub.update_calls[0]
    arg_text = getattr(arg, "plain", None) or str(arg)

    # The expected full rendered content is the concatenation of all returned lines
    expected = "".join(rendered_lines)

    # Assert the implementation updated the live area with the full rendered text (no truncation)
    assert arg_text == expected, (
        "live.update was given truncated content; expected full rendered text.\n"
        f"expected: {expected!r}\nactual:   {arg_text!r}"
    )
