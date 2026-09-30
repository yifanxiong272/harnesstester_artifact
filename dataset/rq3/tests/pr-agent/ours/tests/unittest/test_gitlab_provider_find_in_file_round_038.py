import re
import types

import pytest

from pr_agent.git_providers.gitlab_provider import GitLabProvider


class DummyFile:
    def __init__(self, patch: str):
        self.patch = patch


def _make_provider_with_default_edit_type():
    # Create an instance without running real __init__
    prov = object.__new__(GitLabProvider)
    # RE_HUNK_HEADER expects 5 capture groups: start_old, size_old, start_new, size_new, rest
    prov.RE_HUNK_HEADER = re.compile(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@(.*)")

    def get_edit_type(line: str) -> str:
        # simple deterministic logic for tests
        if line.startswith("+"):
            return "addition"
        if line.startswith("-"):
            return "deletion"
        if line.startswith(" "):
            return "context"
        return "unknown"

    prov.get_edit_type = get_edit_type
    return prov


def test_find_in_file_context_round_038():
    """
    Cover the path where a hunk header is parsed and a context line matches the relevant text.
    Expect source/target line counters to be updated by the context line before matching.
    """
    prov = _make_provider_with_default_edit_type()

    # header sets source_line_no=1, target_line_no=5; then a context line increments both by 1
    patch = "@@ -1,1 +5,1 @@ description\n matching line\n"
    f = DummyFile(patch)

    edit_type, found, source_line_no, returned_file, target_line_no = prov.find_in_file(f, "matching line")

    assert found is True
    assert edit_type == "context"
    # After header: source_line_no=1, target_line_no=5; context line increments both -> 2,6
    assert source_line_no == 2
    assert target_line_no == 6
    # The function should return the original file object as target_file
    assert returned_file is f


def test_find_in_file_plus_prefix_round_038():
    """
    Cover the branch where the relevant_line_in_file begins with '+' but the patch line is a context line
    (the model-added '+' prefix case). This triggers the special elif that strips the '+' and matches.
    """
    prov = _make_provider_with_default_edit_type()

    # header sets source_line_no=3, target_line_no=8; context line increments both by 1
    patch = "@@ -3,2 +8,2 @@ meta\n added line\n"
    f = DummyFile(patch)

    # relevant_line_in_file simulates the model adding a leading '+' to the suggestion
    relevant = "+added line"

    edit_type, found, source_line_no, returned_file, target_line_no = prov.find_in_file(f, relevant)

    assert found is True
    # edit_type comes from the line in the patch which is a context line (starts with ' ' in patch string)
    # Our get_edit_type treats lines starting with ' ' as 'context'
    assert edit_type == "context"
    # After header: source_line_no=3, target_line_no=8; context line increments both -> 4,9
    assert source_line_no == 4
    assert target_line_no == 9
    assert returned_file is f
