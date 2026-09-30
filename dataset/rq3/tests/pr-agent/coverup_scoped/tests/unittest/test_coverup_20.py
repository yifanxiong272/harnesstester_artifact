# file: pr_agent/algo/utils.py:1125-1197
# asked: {"lines": [1136, 1145, 1147, 1148, 1149, 1150, 1151, 1152, 1155, 1157, 1158, 1159, 1182, 1183, 1184, 1185, 1186, 1187, 1188, 1189, 1191, 1194, 1195, 1196], "branches": [[1130, 1132], [1135, 1136], [1144, 1145], [1145, 1138], [1145, 1147], [1147, 1148], [1147, 1151], [1151, 1152], [1151, 1155], [1157, 1145], [1157, 1158], [1181, 1182], [1183, 1138], [1183, 1184], [1184, 1185], [1184, 1188], [1188, 1189], [1188, 1191], [1191, 1183], [1191, 1194]]}
# gained: {"lines": [1136, 1145, 1147, 1148, 1149, 1150, 1151, 1152, 1155, 1157, 1158, 1159, 1182, 1183, 1184, 1185, 1186, 1187, 1188, 1189, 1191, 1194, 1195, 1196], "branches": [[1130, 1132], [1135, 1136], [1144, 1145], [1145, 1147], [1147, 1148], [1147, 1151], [1151, 1152], [1157, 1145], [1157, 1158], [1181, 1182], [1183, 1184], [1184, 1185], [1184, 1188], [1188, 1189], [1191, 1183], [1191, 1194]]}

import types
import pytest

from pr_agent.algo.utils import find_line_number_of_relevant_line_in_file


def make_filepatch(filename: str, patch: str):
    # Use a simple namespace to emulate FilePatchInfo without importing its class
    return types.SimpleNamespace(filename=filename, patch=patch)


def test_empty_diff_files_and_none_absolute():
    # absolute_position is None -> should be converted to -1, and empty diff_files returns early
    pos, abs_pos = find_line_number_of_relevant_line_in_file([], "some_file.py", "irrelevant", absolute_position=None)
    assert pos == -1
    assert abs_pos == -1


def test_find_by_absolute_position():
    # Create a patch with a hunk starting at +3. The second non-deleted line should map to absolute position 4.
    patch = "\n".join([
        "@@ -1,1 +3,5 @@",
        " context1",
        "+added1",
        " context2",
    ])
    fp = make_filepatch("file.py", patch)
    # We search for absolute_position 4 -> should find index 2 ("+added1")
    pos, abs_pos = find_line_number_of_relevant_line_in_file([fp], "file.py", "unused", absolute_position=4)
    assert pos == 2
    assert abs_pos == 4


def test_difflib_single_plus_match_updates_and_matches():
    # difflib should find a single exact match that starts with '+', then that line should be matched
    patch = "\n".join([
        "@@ -10,0 +20,3 @@",
        " context A",
        "+matchline",
        " context B",
    ])
    fp = make_filepatch(" file.py ", patch)  # include spaces to ensure .strip() is used
    # Pass relevant_line that exactly matches the '+matchline' so difflib.get_close_matches returns it
    pos, abs_pos = find_line_number_of_relevant_line_in_file([fp], "file.py", "+matchline", absolute_position=None)
    # "+matchline" is the 3rd line in patch (index 2); start2 is 20, delta at that line is 2 -> absolute = 20 + 2 - 1 = 21
    assert pos == 2
    assert abs_pos == 21


def test_plus_prefix_no_plus_line_fallback():
    # If relevant_line starts with '+' but is not present, function should try the no-plus variant
    patch = "\n".join([
        "@@ -1,1 +2,4 @@",
        " contextX",
        " contextY",
    ])
    fp = make_filepatch("file2.py", patch)
    # Provide a relevant_line that starts with '+' but only the context (without '+') exists in the patch
    pos, abs_pos = find_line_number_of_relevant_line_in_file([fp], "file2.py", "+contextY", absolute_position=None)
    # The matching line is at index 2; start2 is 2, delta for that line is 2 -> absolute = 2 + 2 - 1 = 3
    assert pos == 2
    assert abs_pos == 3
