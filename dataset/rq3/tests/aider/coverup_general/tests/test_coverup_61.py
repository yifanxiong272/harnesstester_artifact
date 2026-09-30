# file: aider/linter.py:234-256
# asked: {"lines": [235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 246, 248, 249, 250, 251, 252, 253, 254, 256], "branches": []}
# gained: {"lines": [235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 246, 248, 249, 250, 251, 252, 253, 254, 256], "branches": []}

import pytest
import aider.linter as linter


class FakeTreeContextBase:
    def __init__(self, fname, code, **kwargs):
        # capture constructor args
        self.fname = fname
        self.code = code
        self.kwargs = kwargs
        self.added_lois = None
        self.add_context_called = False
        # store the last created instance on the class for inspection by tests
        self.__class__.last_instance = self

    def add_lines_of_interest(self, lois):
        # capture the set passed in
        self.added_lois = set(lois)

    def add_context(self):
        self.add_context_called = True

    def format(self):
        # to be overridden per-subclass
        return "<formatted>"


def test_tree_context_single_line(monkeypatch):
    # Prepare a fake TreeContext that returns a known format string
    class FakeTreeContextSingle(FakeTreeContextBase):
        def format(self):
            return "SINGLE_FORMAT"

    # Patch the TreeContext used in the linter module
    monkeypatch.setattr(linter, "TreeContext", FakeTreeContextSingle)

    fname = "example.py"
    code = "print('hello')\n"
    lines = [3]  # single line

    out = linter.tree_context(fname, code, lines)

    # Verify output contents: singular "line" (no 's') and filename and formatted content
    expected_header = "## See relevant line below marked with █.\n\n"
    assert out.startswith(expected_header)
    assert fname + ":\n" in out
    assert out.endswith("SINGLE_FORMAT")

    # Inspect the instance that tree_context created
    inst = FakeTreeContextSingle.last_instance
    assert inst is not None
    # Check that the default kwargs expected by tree_context are present on the instance
    expected_kwargs = {
        "color": False,
        "line_number": True,
        "child_context": False,
        "last_line": False,
        "margin": 0,
        "mark_lois": True,
        "loi_pad": 3,
        "show_top_of_file_parent_scope": False,
    }
    for k, v in expected_kwargs.items():
        assert inst.kwargs.get(k) == v

    # Verify that add_lines_of_interest and add_context were called with the correct values
    assert inst.added_lois == set(lines)
    assert inst.add_context_called is True


def test_tree_context_multiple_lines(monkeypatch):
    # Prepare a fake TreeContext that returns a distinct format string
    class FakeTreeContextMulti(FakeTreeContextBase):
        def format(self):
            # return a multi-line string to ensure concatenation works
            return "LINE1\nLINE2\n"

    # Patch the TreeContext used in the linter module
    monkeypatch.setattr(linter, "TreeContext", FakeTreeContextMulti)

    fname = "multi.py"
    code = "a=1\nb=2\nc=3\n"
    lines = [1, 2]  # multiple lines should yield 'lines' in header

    out = linter.tree_context(fname, code, lines)

    # Verify header uses plural 'lines' and contains filename and formatted content
    expected_header = "## See relevant lines below marked with █.\n\n"
    assert out.startswith(expected_header)
    # the output structure is header, blank line, then "fname:" on its own line
    assert fname + ":" in out
    assert out.endswith("LINE1\nLINE2\n")

    # Inspect the instance that tree_context created
    inst = FakeTreeContextMulti.last_instance
    assert inst is not None
    # Verify that add_lines_of_interest receives a set and that it matches the input
    assert inst.added_lois == set(lines)
    assert inst.add_context_called is True
