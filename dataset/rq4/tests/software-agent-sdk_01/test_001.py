def test_probe_001():
    from pathlib import Path
    from types import MethodType
    from openhands.tools.file_editor.editor import FileEditor, SNIPPET_CONTEXT_WINDOW

    # Activation setup: choose a known replacement line L and unique old_str
    L = 5  # 1-based line where old_str will appear
    old_str = "<<UNIQUE_TARGET>>"
    # new_str has a deterministic number of newlines to affect end_line
    new_str = "replacement\nline"

    # Build file content with exactly one occurrence of old_str on line L
    lines = [f"line-{i}" for i in range(1, L)] + [f"prefix {old_str} suffix"] + [f"line-{i}" for i in range(L + 1, 12)]
    file_content = "\n".join(lines)

    # Expected oracle values computed independently
    expected_start_line = max(1, L - SNIPPET_CONTEXT_WINDOW)
    expected_end_line = L + SNIPPET_CONTEXT_WINDOW + new_str.count("\n")

    # Create an instance without running its __init__ to avoid external deps
    inst = FileEditor.__new__(FileEditor)

    # Instrumentation storage
    inst._read_calls = []
    inst._written_content = None
    inst._history_calls = []

    # Deterministic validate_file: just record call
    def validate_file(self, path):
        self._validated = True

    # write_file: capture content so subsequent snippet reads can be realistic
    def write_file(self, path, content):
        self._written_content = content
        self._write_called = True

    # _history_manager with add_history
    class DummyHistory:
        def __init__(self, parent):
            self._parent = parent
        def add_history(self, path, content):
            # record prior content
            self._parent._history_calls.append((str(path), content))

    # _make_output: return a simple message including the snippet passed
    def _make_output(self, snippet, title, start_line_arg):
        return f"[{start_line_arg}] {title}:" + snippet

    # read_file: behave deterministically; first call (no start_line/end_line) => full file
    # second call with start_line/end_line => record arguments and return a snippet from the written content if available
    def read_file(self, path, start_line=None, end_line=None):
        # Normalize to explicit None -> treat as full-file read
        if start_line is None and end_line is None:
            return file_content
        # record the call arguments as provided to the method
        self._read_calls.append({
            "start_line": start_line,
            "end_line": end_line,
        })
        # Provide a deterministic snippet based on the possibly-updated written content
        src = self._written_content if self._written_content is not None else file_content
        src_lines = src.split("\n")
        # The implementation likely uses 1-based line indexes for read_file; slice accordingly defensively
        # If start_line/end_line are integers, clamp and slice to produce a returned snippet
        try:
            s = int(start_line) if start_line is not None else 1
            e = int(end_line) if end_line is not None else len(src_lines)
        except Exception:
            s, e = 1, len(src_lines)
        # Convert to 1-based inclusive slice => python indices s-1:e
        s_idx = max(0, s - 1)
        e_idx = min(len(src_lines), e)
        return "\n".join(src_lines[s_idx:e_idx])

    # Bind methods onto the instance
    inst.validate_file = MethodType(validate_file, inst)
    inst.write_file = MethodType(write_file, inst)
    inst.read_file = MethodType(read_file, inst)
    inst._make_output = MethodType(_make_output, inst)
    inst._history_manager = DummyHistory(inst)

    # Call the targeted entrypoint
    result = inst.str_replace(Path("/tmp/dummy.txt"), old_str, new_str)

    # There should be exactly one read_file call that included start_line/end_line for the snippet
    # The target implementation first calls read_file(path) for the full file, then later read_file(path, start_line=..., end_line=...)
    # Find the last read_file call that included kwargs
    assert inst._read_calls, "No snippet-range read_file call was recorded"
    last = inst._read_calls[-1]
    recorded_start = last.get("start_line")
    recorded_end = last.get("end_line")

    # Primary oracle: ensure the snippet read request used the independent expected bounds
    assert recorded_start == expected_start_line, (
        f"start_line mismatch: recorded {recorded_start} != expected {expected_start_line}"
    )
    assert recorded_end == expected_end_line, (
        f"end_line mismatch: recorded {recorded_end} != expected {expected_end_line}"
    )
