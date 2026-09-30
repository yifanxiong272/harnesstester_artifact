import types
import pytest

import pr_agent.tools.pr_add_docs as pr_add_docs
from pr_agent.tools.pr_add_docs import PRAddDocs


class FakeFile:
    def __init__(self, filename, head_file):
        self.filename = filename
        self.head_file = head_file


class FakeGitProviderGetDiff:
    # diff_files is falsy to force get_diff_files() path
    diff_files = False

    def get_diff_files(self):
        # first file is unrelated, second matches
        return [
            FakeFile("other.py", "x = 1\n"),
            FakeFile("relevant.py", "    orig_line\n    next_line\n")
        ]


class FakeGitProviderList:
    # diff_files provided directly (truthy)
    def __init__(self, files):
        self.diff_files = files


def make_instance():
    # Create PRAddDocs instance without running its real __init__
    inst = PRAddDocs.__new__(PRAddDocs)
    return inst


def test_dedent_after_add_original_indent_round_048():
    """
    Covers branch where get_diff_files() is used, a matching file is found,
    doc_placement == 'after', delta_spaces > 0 (indentation applied),
    and add_original_line == True (original line is prepended).
    """
    inst = make_instance()
    inst.git_provider = FakeGitProviderGetDiff()

    relevant_file = "relevant.py"
    # relevant_lines_start = 1 -> original_initial_line is first line, '    orig_line'
    new_code_snippet = "def new():\n    pass\n"

    result = inst.dedent_code(relevant_file, 1, new_code_snippet, doc_placement='after', add_original_line=True)

    # textwrap.indent adds spaces to every line of new_code_snippet; original_initial_spaces = 4
    # suggested_initial_spaces = 0 -> delta_spaces = 4 -> both lines get 4 more spaces
    expected_indented = "    def new():\n        pass"  # first line has 4 leading spaces, second line has original 4 + 4 = 8
    expected = "    orig_line\n" + expected_indented

    assert result == expected


def test_dedent_before_append_original_no_indent_round_048():
    """
    Covers branch where diff_files is provided directly, the loop skips a non-matching file
    and finds a matching file, doc_placement != 'after' (before), delta_spaces <= 0 (no indent),
    and add_original_line == True (original line is appended).
    """
    inst = make_instance()

    # Provide a diff_files list directly: first file non-matching, second matching
    files = [
        FakeFile("not_this.py", "irrelevant\n"),
        FakeFile("relevant.py", "orig\n  next_line\n")
    ]
    inst.git_provider = FakeGitProviderList(files)

    relevant_file = "relevant.py"
    # Make suggested initial line more-indented than original to force delta_spaces <= 0
    new_code_snippet = "  def x():\n    pass\n"

    result = inst.dedent_code(relevant_file, 1, new_code_snippet, doc_placement='before', add_original_line=True)

    # Because doc_placement != 'after', line used for original_initial_spaces is original_initial_line ('orig') -> 0 spaces
    # suggested_initial_spaces is 2 -> delta_spaces = -2 -> no indent applied
    # add_original_line True and doc_placement != 'after' => snippet + '\n' + original_initial_line
    expected = new_code_snippet.rstrip() + "\n" + "orig"

    assert result == expected


def test_exception_path_round_048(monkeypatch):
    """
    Force an exception inside the try block (new_code_snippet is None -> AttributeError on splitlines()),
    and verify that when verbosity_level >= 2 the logger.info is invoked and the original value is returned.
    """
    inst = make_instance()

    # Provide a matching file so the code enters the block that will attempt to call splitlines() on new_code_snippet
    inst.git_provider = FakeGitProviderList([FakeFile("relevant.py", "orig\nnext\n")])

    captured = []

    # Monkeypatch get_settings to report verbosity_level >= 2
    monkeypatch.setattr(pr_add_docs, "get_settings", lambda: types.SimpleNamespace(config=types.SimpleNamespace(verbosity_level=2)))

    # Monkeypatch get_logger to capture info calls
    monkeypatch.setattr(pr_add_docs, "get_logger", lambda: types.SimpleNamespace(info=lambda msg: captured.append(msg)))

    # Cause AttributeError inside try by passing new_code_snippet = None
    result = inst.dedent_code("relevant.py", 1, None, doc_placement='after', add_original_line=False)

    # The function should return the original new_code_snippet (None) after catching the exception
    assert result is None

    # And the logger should have been called with a message mentioning the file
    assert any("relevant.py" in str(m) and "Could not dedent code snippet" in str(m) for m in captured)
