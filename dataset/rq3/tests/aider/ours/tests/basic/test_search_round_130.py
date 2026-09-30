import aider.gui as gui
from aider.gui import search


def test_search_no_files_round_130(monkeypatch):
    """When os.walk yields nothing, search should return an empty list."""
    def fake_walk(start):
        # simulate no files under the directory
        if start == "aider":
            return []
        return []

    # Patch the os.walk that the search function uses
    monkeypatch.setattr(gui.os, "walk", fake_walk)

    result = search()
    assert isinstance(result, list)
    assert result == []


def test_search_returns_all_when_text_none_round_130(monkeypatch):
    """When text is None, all paths produced by os.walk should be returned in order."""
    entries = [
        ("aider", [], ["file1.py", "file2.txt"]),
        ("aider/sub", [], ["subfile.md"]),
    ]

    def fake_walk(start):
        assert start == "aider"
        # return a list (iterable) preserving the order
        return entries

    monkeypatch.setattr(gui.os, "walk", fake_walk)

    result = search(text=None)
    # build expected using real os.path.join to mirror search behavior
    expected = [gui.os.path.join(*pair) for pair in [ (entries[0][0], entries[0][2][0]),
                                                      (entries[0][0], entries[0][2][1]),
                                                      (entries[1][0], entries[1][2][0]) ]]
    assert result == expected


def test_search_filters_by_text_round_130(monkeypatch):
    """When a text substring is provided, only paths containing it are returned."""
    entries = [
        ("aider/pkg", [], ["match_one.txt", "nomatch.txt"]),
        ("aider/other", [], ["another_match.md", "skip.py"]),
    ]

    def fake_walk(start):
        assert start == "aider"
        return entries

    monkeypatch.setattr(gui.os, "walk", fake_walk)

    result = search(text="match")
    # expect only paths that include the substring "match"
    expected = [
        gui.os.path.join("aider/pkg", "match_one.txt"),
        gui.os.path.join("aider/other", "another_match.md"),
    ]
    assert result == expected


def test_search_no_match_round_130(monkeypatch):
    """When text doesn't match any path, result should be empty even if files exist."""
    entries = [
        ("aider/x", [], ["a.py", "b.txt"]),
    ]

    def fake_walk(start):
        return entries

    monkeypatch.setattr(gui.os, "walk", fake_walk)

    result = search(text="__no_such_substring__")
    assert result == []
