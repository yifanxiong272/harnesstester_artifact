from pathlib import Path

from openhands.tools.file_editor.editor import FileEditor, SNIPPET_CONTEXT_WINDOW


def test_probe_001():
    """Probe: ensure the snippet read request uses 1-based inclusive start/end lines matching the independent invariant.

    Invariant: when replacing a single unique occurrence located on source line L,
    the snippet read must request lines with 1-based inclusive start and end:
    start_line == max(1, L - SNIPPET_CONTEXT_WINDOW) and
    end_line == L + SNIPPET_CONTEXT_WINDOW + new_str.count('\n').
    """

    # Deterministic test parameters
    old_str = "UNIQUE_TOKEN_ABC"
    # include two newlines to exercise end_line adjustment
    new_str = "lineA\nlineB\n"

    # choose replacement line L strictly greater than SNIPPET_CONTEXT_WINDOW
    L = SNIPPET_CONTEXT_WINDOW + 2

    # Build file content: lines 1..(L-1) are filler, line L contains the unique token,
    # then include a few lines after
    pre_lines = [f"pre_line_{i}" for i in range(1, L)]
    target_line = f"prefix {old_str} suffix"
    post_lines = [f"post_line_{i}" for i in range(1, 6)]
    # join with newlines and ensure trailing newline for realistic file content
    file_lines = pre_lines + [target_line] + post_lines
    original_content = "\n".join(file_lines) + "\n"

    # Prepare an in-memory store to simulate file contents and capture snippet read args
    store = {
        "content": original_content,
        "captured_start_line": None,
        "captured_end_line": None,
        "read_call_count": 0,
    }

    # Create a bare FileEditor instance without running __init__ to avoid unrelated side effects
    editor = FileEditor.__new__(FileEditor)

    # Inject no-op validator
    def validate_file(path):
        return None

    # write_file should update the in-memory store
    def write_file(path, new_content):
        # deterministic update
        store["content"] = new_content

    # _history_manager.add_history no-op
    class DummyHistory:
        def add_history(self, path, prev_content):
            return None

    # _make_output should return a stable snippet description (not used for oracle)
    def make_output(snippet_text, title, start_line_arg):
        return f"SNIPPET[{start_line_arg}]:{snippet_text}"

    # read_file: on first call (no start_line/end_line) return full content; on snippet call capture args
    def read_file(path, start_line=None, end_line=None):
        store["read_call_count"] += 1
        # If no start/end provided, this is the full-file read
        if start_line is None and end_line is None:
            return store["content"]
        # Otherwise treat as 1-based inclusive lines and capture
        store["captured_start_line"] = start_line
        store["captured_end_line"] = end_line
        # Convert 1-based inclusive start/end to slice of lines
        lines = store["content"].splitlines()
        # clip to bounds
        s = max(1, int(start_line))
        e = min(len(lines), int(end_line))
        # convert to 0-based slice indices
        snippet_lines = lines[s - 1 : e]
        return "\n".join(snippet_lines) + ("\n" if snippet_lines else "")

    # Attach the deterministic stubs to the instance
    editor.validate_file = validate_file
    editor.read_file = read_file
    editor.write_file = write_file
    editor._history_manager = DummyHistory()
    editor._make_output = make_output

    # Call the target API: FileEditor.str_replace(path, old_str, new_str)
    path = Path("dummy.txt")

    # Run the replacement. This should perform one replacement and trigger the snippet read.
    obs = editor.str_replace(path, old_str, new_str)

    # Verify we observed a snippet read call
    assert store["read_call_count"] >= 2, "Expected at least two read_file calls (full read and snippet read)."

    captured_start = store["captured_start_line"]
    captured_end = store["captured_end_line"]

    assert captured_start is not None and captured_end is not None, "Snippet read call arguments were not captured."

    # Compute independent expected values per the invariant
    expected_start = max(1, L - SNIPPET_CONTEXT_WINDOW)
    expected_end = L + SNIPPET_CONTEXT_WINDOW + new_str.count("\n")

    # Primary oracle: ensure start/end match the conservative invariant
    assert (
        captured_start == expected_start and captured_end == expected_end
    ), (
        f"Snippet range mismatch: captured (start={captured_start}, end={captured_end}), "
        f"expected (start={expected_start}, end={expected_end})."
    )
