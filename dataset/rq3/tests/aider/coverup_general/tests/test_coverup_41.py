# file: aider/coders/search_replace.py:406-431
# asked: {"lines": [407, 408, 410, 412, 413, 414, 416, 417, 420, 421, 422, 423, 424, 425, 427, 428, 429, 431], "branches": [[421, 422], [421, 431], [422, 423], [422, 424], [424, 425], [424, 427], [428, 421], [428, 429]]}
# gained: {"lines": [407, 408, 410, 412, 413, 414, 416, 417, 420, 421, 422, 423, 424, 425, 427, 428, 429, 431], "branches": [[421, 422], [421, 431], [422, 423], [422, 424], [424, 425], [424, 427], [428, 421], [428, 429]]}

import pytest

from types import SimpleNamespace


def make_fake_dmp(mapping, diffs):
    """
    Create a fake diff_match_patch class whose methods mimic the interface used
    by aider.coders.search_replace.diff_lines. `mapping` is a list of lines
    (each should include its line ending). `diffs` is the sequence that
    diff_main should return: a list of tuples (op_int, token_string) where
    token_string is tokens separated by '|' that index into mapping.
    """

    class FakeDMP:
        # store last instance for test inspection
        last_instance = None

        def __init__(self):
            # tests will set/assert this attribute via the instance stored on the class
            self.Diff_Timeout = None
            FakeDMP.last_instance = self
            # no Diff_EditCost used here

        def diff_linesToChars(self, search_text, replace_text):
            # ignore inputs, return dummy encoded strings and the mapping
            return "SEARCH", "REPLACE", mapping

        def diff_main(self, s, r, _):
            # Return a shallow copy so tests can reuse make_fake_dmp safely
            return list(diffs)

        def diff_cleanupSemantic(self, diffs_in):
            # mark that cleanup was called
            setattr(self, "semantic_cleaned", True)

        def diff_cleanupEfficiency(self, diffs_in):
            # mark that cleanup was called
            setattr(self, "efficiency_cleaned", True)

        def diff_charsToLines(self, diffs_in, mapping_in):
            # mutate diffs_in in place to replace token strings with actual line content
            for i, (op, token_str) in enumerate(list(diffs_in)):
                if token_str == "":
                    # allow empty token strings
                    lines = ""
                else:
                    parts = token_str.split("|")
                    # join mapping entries (each should already include newline)
                    lines = "".join(mapping_in[int(p)] for p in parts)
                # assign back as a tuple (op stays an int)
                diffs_in[i] = (op, lines)

    return FakeDMP


def test_diff_lines_produces_minus_space_plus_and_timeout_set(monkeypatch):
    # Prepare mapping and diffs to exercise -, ' ', and + branches and line splitting
    mapping = [
        "deleted line 1\n",  # index 0
        "inserted line 1\n",  # index 1
        "common line 1\n",  # index 2
    ]
    # diffs: deletion of index 0 and 2, equality of 2, insertion of 1
    diffs = [(-1, "0|2"), (0, "2"), (1, "1")]

    Fake = make_fake_dmp(mapping, diffs)

    # Import the module under test and monkeypatch the diff_match_patch name it imported
    import importlib

    mod = importlib.import_module("aider.coders.search_replace")
    monkeypatch.setattr(mod, "diff_match_patch", Fake)

    # Call the function under test
    udiff = mod.diff_lines("ignored search", "ignored replace")

    # Verify Diff_Timeout was set on the created instance
    assert Fake.last_instance is not None
    assert Fake.last_instance.Diff_Timeout == 5

    # Expected udiff sequence:
    expected = [
        "-deleted line 1\n",
        "-common line 1\n",
        " common line 1\n",
        "+inserted line 1\n",
    ]
    assert udiff == expected


def test_diff_lines_handles_empty_diff(monkeypatch):
    # Test the case where diff_main returns an empty list (no changes)
    mapping = []
    diffs = []

    Fake = make_fake_dmp(mapping, diffs)

    import importlib

    mod = importlib.import_module("aider.coders.search_replace")
    monkeypatch.setattr(mod, "diff_match_patch", Fake)

    udiff = mod.diff_lines("", "")

    # No diff lines expected
    assert udiff == []
    # Cleanups should have been called (attributes set on instance)
    assert getattr(Fake.last_instance, "semantic_cleaned", False) is True
    assert getattr(Fake.last_instance, "efficiency_cleaned", False) is True
    # Timeout must still be set
    assert Fake.last_instance.Diff_Timeout == 5
