import pytest
from pathlib import Path
from types import SimpleNamespace

from aider.coders import editblock_coder as ebc


class FakeIO:
    def __init__(self, mapping=None):
        self.mapping = mapping or {}
        self.written = {}

    def read_text(self, path):
        # Return stored content (deterministic)
        return self.mapping.get(path, "")

    def write_text(self, path, content):
        # Record writes for assertions
        self.written[path] = content


def _make_dummy_io_setup():
    # Prepare mapping for paths used by tests
    mapping = {
        # abs_root_path('/b.txt') will be '/root/b.txt' below
        "/root/b.txt": "line1\nsome updatedb inside content\nline3",
        # alt file where the first edit will match via do_replace
        "/other/alt1.txt": "original content in alt1",
    }
    return FakeIO(mapping)


def test_apply_edits_failure_round_030(monkeypatch):
    """Test non-dry run where one edit succeeds by searching other files and
    one edit ultimately fails, producing a ValueError whose message includes
    hints produced by find_similar_lines and the 'already in file' check.
    """
    # Arrange: dummy "self" with required attributes
    dummy = SimpleNamespace()
    dummy.abs_root_path = lambda p: f"/root/{p}"
    dummy.abs_fnames = ["/other/alt1.txt", "/other/alt2.txt"]
    dummy.get_rel_fname = lambda full_path: f"rel/{full_path.split('/')[-1]}"
    dummy.fence = ("```", "```")

    fake_io = _make_dummy_io_setup()
    dummy.io = fake_io

    # Ensure Path.exists() is False to force the code to try alternative files
    monkeypatch.setattr(Path, "exists", lambda self: False)

    # Monkeypatch do_replace to succeed only for the alt1 file on the first edit
    def fake_do_replace(full_path, content, original, updated, fence):
        # Successful replacement when searching alt1 for first edit
        if "alt1.txt" in full_path and original == "old":
            return "replaced-content-for-alt1"
        # Otherwise, no match
        return ""

    monkeypatch.setattr(ebc, "do_replace", fake_do_replace)

    # Monkeypatch find_similar_lines to return a suggestion for the failing edit
    def fake_find_similar_lines(original, content):
        if original == "origb":
            return "possible similar line suggestion"
        return ""

    monkeypatch.setattr(ebc, "find_similar_lines", fake_find_similar_lines)

    # Prepare edits: first will be found in alt1, second will fail
    edit1 = ("a.txt", "old", "new1")
    edit2 = ("b.txt", "origb", "updatedb")
    edits = [edit1, edit2]

    # Act & Assert: non-dry-run should raise ValueError because one edit fails
    with pytest.raises(ValueError) as excinfo:
        ebc.EditBlockCoder.apply_edits(dummy, edits, dry_run=False)

    msg = str(excinfo.value)

    # Oracle: check message contains expected diagnostic pieces
    assert "SEARCH/REPLACE" in msg
    # single failed block grammar and count
    assert "# 1 SEARCH/REPLACE block failed to match!" in msg
    # suggestion from find_similar_lines must appear
    assert "Did you mean to match" in msg or "possible similar line suggestion" in msg
    # the 'Are you sure' note should appear because updatedb is present in content
    # the code adds this block only when updated in content and updated is truthy
    assert "Are you sure you need this SEARCH/REPLACE block?" in msg
    # the general guidance should be present
    assert "The SEARCH section must exactly match" in msg
    # since one edit passed, confirm the message about other applied blocks is present
    assert "# The other 1 SEARCH/REPLACE block" in msg

    # Confirm that the successful replacement wrote the expected content
    # write_text should have been called for the alt1 full_path
    assert "/other/alt1.txt" in fake_io.written
    assert fake_io.written["/other/alt1.txt"] == "replaced-content-for-alt1"


def test_apply_edits_dry_run_round_030(monkeypatch):
    """When dry_run=True the method should return updated_edits and not write files."""
    dummy = SimpleNamespace()
    dummy.abs_root_path = lambda p: f"/root/{p}"
    dummy.abs_fnames = ["/other/alt1.txt"]
    dummy.get_rel_fname = lambda full_path: f"rel/{full_path.split('/')[-1]}"
    dummy.fence = ("```", "```")

    fake_io = _make_dummy_io_setup()
    dummy.io = fake_io

    monkeypatch.setattr(Path, "exists", lambda self: False)

    # Same do_replace: succeed only for alt1 and only for the first edit
    def fake_do_replace(full_path, content, original, updated, fence):
        if "alt1.txt" in full_path and original == "old":
            return "replaced-content-for-alt1"
        return ""

    monkeypatch.setattr(ebc, "do_replace", fake_do_replace)
    monkeypatch.setattr(ebc, "find_similar_lines", lambda o, c: "")

    edit1 = ("a.txt", "old", "new1")
    edit2 = ("b.txt", "origb", "updatedb")
    edits = [edit1, edit2]

    # Dry run should return updated_edits without performing writes
    result = ebc.EditBlockCoder.apply_edits(dummy, edits, dry_run=True)

    # The first edit should have its path updated to the rel name because it matched alt1
    assert ("rel/alt1.txt", "old", "new1") in result
    # No writes should have occurred during dry_run
    assert fake_io.written == {}
