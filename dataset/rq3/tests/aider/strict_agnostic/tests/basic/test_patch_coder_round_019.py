import pytest
from types import SimpleNamespace
from pathlib import Path
import aider.coders.patch_coder as pc


class DummyIO:
    def __init__(self):
        self.warnings = []
        self.read_calls = []
        # If set to an Exception instance, read_text will raise it.
        # If set to a callable, it will be called with the path.
        # Otherwise the value is returned directly.
        self.read_text_side_effect = None

    def tool_warning(self, msg: str):
        self.warnings.append(msg)

    def read_text(self, path):
        self.read_calls.append(path)
        if isinstance(self.read_text_side_effect, Exception):
            raise self.read_text_side_effect
        if callable(self.read_text_side_effect):
            return self.read_text_side_effect(path)
        return self.read_text_side_effect


def _make_coder():
    # Instantiate without running Coder.__init__ to control attributes directly
    coder = pc.PatchCoder.__new__(pc.PatchCoder)
    coder.io = DummyIO()
    # Default abs_root_path: join a fake root with the relative path
    coder.abs_root_path = lambda rel: Path("/fake_root") / rel
    return coder


def test_empty_content_round_019():
    """Empty or whitespace content should return an empty list (lines 225-227).
    """
    coder = _make_coder()
    coder.partial_response_content = ""  # empty

    res = coder.get_edits()
    assert res == []


def test_non_patch_like_round_019():
    """Content that does not look like a patch should warn and return [] (lines 231-246).
    """
    coder = _make_coder()
    # Two-line content but not patch-like
    coder.partial_response_content = "Just some text\nNothing to see here"

    # Ensure identify_files_needed is not invoked for this scenario (no side effects)
    # but keep deterministic behavior by monkeypatching it to a no-op
    orig_ident = pc.identify_files_needed
    try:
        pc.identify_files_needed = lambda text: []
        res = coder.get_edits()
    finally:
        pc.identify_files_needed = orig_ident

    assert res == []
    # Confirm the expected warning message was emitted
    assert coder.io.warnings == ["Response does not appear to be in patch format."]


def test_patch_like_without_sentinels_round_019():
    """Patch-like content lacking sentinels should warn and still be parsed (lines 249-256, 276-282).

    We monkeypatch identify_files_needed to return no files and stub _parse_patch_text to return
    an object with an actions dict so that get_edits returns the converted list.
    """
    coder = _make_coder()
    # Make content patch-like by including a line that starts with '@@'
    coder.partial_response_content = "@@ -1,0 +1 @@\n*** Update File: foo.txt\n+added line\n"

    # Ensure identify_files_needed returns an empty list (no file reads)
    orig_ident = pc.identify_files_needed
    try:
        pc.identify_files_needed = lambda text: []

        # Stub parser to return an object with an actions dict
        def fake_parse(lines, start_index, current_files):
            return SimpleNamespace(actions={"foo.txt": {"fake": "action"}})

        coder._parse_patch_text = fake_parse

        res = coder.get_edits()
    finally:
        pc.identify_files_needed = orig_ident

    # Expect the parser's actions converted to list of tuples
    assert res == [("foo.txt", {"fake": "action"})]
    # The missing-sentinels warning should have been emitted
    assert any("Missing '*** Begin Patch'/'*** End Patch' sentinels" in w or "Patch format warning" in w for w in coder.io.warnings)


def test_file_not_found_raises_diff_error_round_019():
    """When identify_files_needed references a file and read_text raises FileNotFoundError,
    get_edits should raise DiffError (lines 259-271).
    """
    coder = _make_coder()
    coder.partial_response_content = "@@ -1,0 +1 @@\n*** Update File: missing.txt\n+new\n"

    # Make identify_files_needed report that 'missing.txt' is required
    orig_ident = pc.identify_files_needed
    try:
        pc.identify_files_needed = lambda text: ["missing.txt"]

        # Simulate read_text raising FileNotFoundError
        coder.io.read_text_side_effect = FileNotFoundError()

        with pytest.raises(pc.DiffError) as exc:
            coder.get_edits()
    finally:
        pc.identify_files_needed = orig_ident

    # error message should mention the referenced relative path
    assert "missing.txt" in str(exc.value)


def test_read_text_returns_none_raises_diff_error_round_019():
    """If io.read_text returns None, code should raise DiffError indicating the file couldn't be read (lines 262-268).
    """
    coder = _make_coder()
    coder.partial_response_content = "@@ -1,0 +1 @@\n*** Update File: config.yaml\n+setting: true\n"

    orig_ident = pc.identify_files_needed
    try:
        pc.identify_files_needed = lambda text: ["config.yaml"]

        # Simulate read_text returning None (interpreted as unreadable)
        coder.io.read_text_side_effect = None

        with pytest.raises(pc.DiffError) as exc:
            coder.get_edits()
    finally:
        pc.identify_files_needed = orig_ident

    assert "config.yaml" in str(exc.value)
