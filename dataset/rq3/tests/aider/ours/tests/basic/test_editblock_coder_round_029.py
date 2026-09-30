import types
import pytest

from aider.coders import editblock_coder as ebc


class DummyIO:
    def __init__(self, mapping):
        # mapping: full_path -> content
        self.mapping = dict(mapping)
        self.writes = {}

    def read_text(self, full_path):
        return self.mapping.get(full_path, "")

    def write_text(self, full_path, content):
        # record writes for assertions
        self.writes[full_path] = content


def make_self(abs_root_prefix, mapping, abs_fnames, fence=("```", "```")):
    """Create a lightweight self-like object acceptable to apply_edits.

    It provides: abs_root_path, abs_fnames, io (with read_text/write_text), fence, get_rel_fname
    """
    io = DummyIO(mapping)

    def abs_root_path(path):
        return abs_root_prefix.rstrip("/") + "/" + path

    def get_rel_fname(full_path):
        # return a deterministic relative name
        return full_path.split("/", 1)[-1]

    return types.SimpleNamespace(
        abs_root_path=abs_root_path,
        abs_fnames=abs_fnames,
        io=io,
        fence=fence,
        get_rel_fname=get_rel_fname,
    )


def test_apply_edits_dry_run_round_029(monkeypatch):
    """Dry run should return updated_edits without calling write_text.

    This covers the branch where a do_replace returns new content and dry_run=True
    """
    # Patch Path.exists to always return True so code will read files
    monkeypatch.setattr(ebc.Path, "exists", lambda self: True)

    # Fake do_replace: succeed only for files named pass.py and when original present in content
    def fake_do_replace(full_path, content, original, updated, fence):
        if full_path.endswith("pass.py") and original in content:
            return content.replace(original, updated)
        return None

    monkeypatch.setattr(ebc, "do_replace", fake_do_replace)

    # Not used in this test but keep deterministic
    monkeypatch.setattr(ebc, "find_similar_lines", lambda orig, content: "")

    # Setup file contents
    abs_root = "/root"
    mapping = {
        "/root/pass.py": "lineA\norig_pass\nlineC",
    }
    self_obj = make_self(abs_root, mapping, abs_fnames=["/root/other.py"])  # other file unused

    edits = [("pass.py", "orig_pass", "replaced_pass")]

    # Call the method as an unbound function, passing our self_obj
    res = ebc.EditBlockCoder.apply_edits(self_obj, edits, dry_run=True)

    # Expect the updated_edits list to be returned and write_text not called
    assert res == edits
    assert self_obj.io.writes == {}


def test_apply_edits_failure_round_029(monkeypatch):
    """Test that failed edits produce a detailed ValueError message.

    This test exercises the branches that append did_you_mean suggestions and
    the branch that reports the REPLACE lines already present in the target file.
    Also ensures a passed edit is reported in the final message.
    """
    # Always treat files as existing so the code reads content
    monkeypatch.setattr(ebc.Path, "exists", lambda self: True)

    # do_replace: only succeed for the first (pass.py) edit
    def fake_do_replace(full_path, content, original, updated, fence):
        if full_path.endswith("pass.py") and original in content:
            return content.replace(original, updated)
        # for all other files/edits, simulate no exact match
        return None

    monkeypatch.setattr(ebc, "do_replace", fake_do_replace)

    # find_similar_lines should return a non-empty suggestion for the failing edit
    def fake_find_similar_lines(original, content):
        if original == "orig_fail":
            return "similar_line_suggestion"
        return ""

    monkeypatch.setattr(ebc, "find_similar_lines", fake_find_similar_lines)

    abs_root = "/root"
    # Prepare contents:
    # - pass.py contains the original so do_replace will make a replacement
    # - fail.py contains the updated text already (to trigger the "already in file" branch)
    mapping = {
        "/root/pass.py": "line1\norig_pass\nline3",
        "/root/fail.py": "some context\nrep_fail_already_here\nmore",
        # Also include any fallback files which will not match
        "/root/other1.py": "no match",
    }

    # Our fence markers used in the message construction
    fence = ("~~~FENCE_START~~~", "~~~FENCE_END~~~")

    self_obj = make_self(abs_root, mapping, abs_fnames=["/root/other1.py"], fence=fence)

    edits = [
        ("pass.py", "orig_pass", "replaced_pass"),
        ("fail.py", "orig_fail", "rep_fail_already_here"),
    ]

    # Run and expect a ValueError due to the failed edit(s)
    with pytest.raises(ValueError) as excinfo:
        ebc.EditBlockCoder.apply_edits(self_obj, edits, dry_run=False)

    msg = str(excinfo.value)

    # Assertions on the message content to ensure important branches executed
    # 1 failed block should be reported (singular "block")
    assert "1 SEARCH/REPLACE block failed" in msg

    # SearchReplaceNoExactMatch block header should be present and include the failing path
    assert "SearchReplaceNoExactMatch" in msg
    assert "fail.py" in msg

    # The original and updated strings from the failing edit should be present
    assert "orig_fail" in msg
    assert "rep_fail_already_here" in msg

    # Our fake_find_similar_lines returned a suggestion, which should appear
    assert "similar_line_suggestion" in msg

    # Because the updated text already exists in the file content, the message
    # should include the 'REPLACE lines are already in' hint
    assert "The REPLACE lines are already in fail.py" in msg or "REPLACE lines are already in" in msg

    # The message should also report that the other edit(s) were applied successfully
    assert "The other 1 SEARCH/REPLACE block were applied successfully" in msg
