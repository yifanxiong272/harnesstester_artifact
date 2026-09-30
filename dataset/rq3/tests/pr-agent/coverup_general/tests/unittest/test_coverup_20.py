# file: pr_agent/git_providers/gitlab_provider.py:710-744
# asked: {"lines": [711, 712, 713, 714, 715, 716, 717, 718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735, 736, 737, 738, 741, 742, 743, 744], "branches": [[718, 719], [718, 744], [719, 720], [719, 727], [721, 722], [721, 723], [727, 728], [727, 729], [729, 730], [729, 731], [731, 732], [731, 734], [734, 735], [734, 738], [738, 718], [738, 741]]}
# gained: {"lines": [711, 712, 713, 714, 715, 716, 717, 718, 719, 720, 721, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735, 736, 737, 738, 741, 742, 743, 744], "branches": [[718, 719], [719, 720], [719, 727], [721, 723], [727, 728], [727, 729], [729, 730], [729, 731], [731, 732], [734, 735], [734, 738], [738, 718], [738, 741]]}

import re
from types import SimpleNamespace

import pytest

from pr_agent.git_providers import gitlab_provider


def make_provider():
    # Create an instance without calling __init__
    provider = object.__new__(gitlab_provider.GitLabProvider)
    # Ensure RE_HUNK_HEADER exists and will match our test hunk header
    provider.RE_HUNK_HEADER = re.compile(r'^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@(.*)')
    return provider


def test_find_in_file_addition_line_matches_directly():
    provider = make_provider()

    patch = (
        "@@ -1,3 +1,4 @@\n"
        " def foo():\n"
        "-print(\"old\")\n"
        "+print(\"new\")\n"
        " line2\n"
    )
    file = SimpleNamespace(patch=patch)

    # relevant_line_in_file exactly matches the addition line in the patch
    relevant = '+print("new")'

    edit_type, found, source_line_no, target_file, target_line_no = provider.find_in_file(
        file, relevant
    )

    assert found is True
    assert edit_type == 'addition'
    # After header start_old=1, start_new=1
    # ' def foo()' increments both to 2
    # '-print("old")' increments source to 3
    # '+print("new")' increments target to 3 then we match and break
    assert source_line_no == 3
    assert target_line_no == 3
    assert target_file is file


def test_find_in_file_plus_prefixed_relevant_matches_context_line():
    provider = make_provider()

    patch = (
        "@@ -1,3 +1,4 @@\n"
        " def foo():\n"
        "-print(\"old\")\n"
        "+print(\"new\")\n"
        " line2\n"
    )
    file = SimpleNamespace(patch=patch)

    # Model added a '+' but the original line was a context line (starts with ' ')
    relevant = '+ def foo():'

    edit_type, found, source_line_no, target_file, target_line_no = provider.find_in_file(
        file, relevant
    )

    assert found is True
    # The matched line in the patch starts with ' ' so get_edit_type should return 'context'
    assert edit_type == 'context'
    # After header start_old=1, start_new=1
    # ' def foo()' increments both to 2 and then we match via the special branch
    assert source_line_no == 2
    assert target_line_no == 2
    assert target_file is file
