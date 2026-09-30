from aider.coders import editblock_coder as eb


def test_difflib_get_close_matches_is_delegated_and_forwarded(monkeypatch):
    """Ensure that when earlier checks fail the function delegates to difflib.get_close_matches and forwards the collaborator's single result."""
    fence = ("```", "```")

    # Arrange lines so reverse()+slice yields three lines where two produce candidates
    # and start with fence[0], ensuring filenames collects multiple entries and the
    # difflib branch is reached.
    lines = ["```f1", "```f2", "```"]

    # strip_filename returns a candidate for the two fence-prefixed lines
    def fake_strip(line, fence_arg):
        if line == "```f2":
            return "fuzzy_one"
        if line == "```f1":
            return "fuzzy_two"
        return None

    monkeypatch.setattr(eb, "strip_filename", fake_strip)

    # valid_fnames list has no exact or basename matches for the fuzzy names
    valid_fnames = ["close_match.py", "other.py"]

    # Patch difflib.get_close_matches on the module object to return a single match
    def fake_get_close_matches(fname, seq, n, cutoff):
        return [seq[0]]

    monkeypatch.setattr(eb.difflib, "get_close_matches", fake_get_close_matches)

    result = eb.find_filename(lines, fence, valid_fnames)

    # Primary oracle: the function should return the collaborator's sole result (value equality)
    assert result == valid_fnames[0]
