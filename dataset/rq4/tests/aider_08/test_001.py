def test_probe_001():
    import pytest
    import aider.coders.udiff_coder as udiff

    # Create an instance without invoking __init__ to avoid unknown ctor behavior
    coder = object.__new__(udiff.UnifiedDiffCoder)

    # Deterministic IO that records writes
    class DummyIO:
        def __init__(self):
            self.writes = {}
        def read_text(self, full_path):
            return "original content"
        def write_text(self, full_path, content):
            self.writes[full_path] = content

    dummy_io = DummyIO()
    coder.io = dummy_io

    # Keep path resolution deterministic
    coder.abs_root_path = lambda p: p

    # Monkeypatch module helpers to deterministic, narrow behaviors
    udiff.normalize_hunk = lambda h: h
    udiff.hunk_to_before_after = lambda h: ("".join([line for line in h if line.startswith("-")]), "".join([line for line in h if line.startswith("+")]))

    def do_replace(full_path, content, hunk):
        # Simulate success for one path and no-match for the other
        if full_path.endswith("success.txt"):
            return "modified content"
        return ""

    udiff.do_replace = do_replace

    # Two distinct edits: one will succeed, one will produce a no-match
    edits = [
        ("success.txt", ["-old\n", "+new\n"]),
        ("fail.txt", ["-old2\n", "+new2\n"]),
    ]

    # Primary oracle: when mixed success/failure occurs, a ValueError is raised
    # and its message must contain the other_hunks_applied marker
    with pytest.raises(ValueError) as exc:
        coder.apply_edits(edits)

    msg = str(exc.value)
    assert udiff.other_hunks_applied in msg

    # Observable supporting check: the successful path was written
    assert "success.txt" in dummy_io.writes
