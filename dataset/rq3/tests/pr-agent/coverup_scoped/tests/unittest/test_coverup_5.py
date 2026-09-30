# file: pr_agent/git_providers/github_provider.py:1107-1190
# asked: {"lines": [1111, 1112, 1113, 1114, 1116, 1118, 1119, 1120, 1121, 1122, 1125, 1126, 1127, 1128, 1129, 1130, 1131, 1133, 1134, 1135, 1137, 1138, 1139, 1140, 1141, 1142, 1145, 1146, 1147, 1149, 1150, 1151, 1152, 1153, 1154, 1155, 1156, 1157, 1158, 1159, 1160, 1161, 1162, 1163, 1164, 1165, 1167, 1168, 1169, 1172, 1173, 1174, 1175, 1176, 1177, 1178, 1180, 1181, 1182, 1183, 1184, 1186, 1187, 1188, 1189, 1190], "branches": [[1118, 1119], [1118, 1190], [1121, 1118], [1121, 1122], [1122, 1121], [1122, 1125], [1126, 1127], [1126, 1137], [1129, 1130], [1129, 1137], [1130, 1129], [1130, 1131], [1133, 1129], [1133, 1134], [1141, 1142], [1141, 1145], [1149, 1150], [1149, 1164], [1152, 1153], [1152, 1157], [1157, 1149], [1157, 1158], [1161, 1149], [1161, 1162], [1164, 1121], [1164, 1165], [1165, 1167], [1165, 1186]]}
# gained: {"lines": [1111, 1112, 1113, 1114, 1116, 1118, 1119, 1120, 1121, 1122, 1125, 1126, 1127, 1128, 1129, 1130, 1131, 1133, 1134, 1135, 1137, 1138, 1139, 1140, 1141, 1145, 1146, 1147, 1149, 1150, 1151, 1152, 1153, 1154, 1155, 1156, 1164, 1190], "branches": [[1118, 1119], [1118, 1190], [1121, 1118], [1121, 1122], [1122, 1125], [1126, 1127], [1129, 1130], [1129, 1137], [1130, 1129], [1130, 1131], [1133, 1134], [1141, 1145], [1149, 1150], [1152, 1153], [1164, 1121]]}

import types
import re
from types import SimpleNamespace

import pytest

import pr_agent.git_providers.github_provider as gp_mod
from pr_agent.git_providers.github_provider import GithubProvider


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def error(self, msg):
        self.errors.append(msg)


def make_file(filename, patch):
    return SimpleNamespace(filename=filename, patch=patch)


def test_validate_comments_inside_hunks_valid_hunk(monkeypatch):
    # Prepare
    # Patch extract_hunk_headers to produce predictable values:
    def fake_extract_hunk_headers(match):
        # return section_header, size1, size2, start1, start2
        return ("@@ -1,1 +5,2 @@", 1, 2, 1, 5)

    monkeypatch.setattr(gp_mod, "extract_hunk_headers", fake_extract_hunk_headers)
    monkeypatch.setattr(gp_mod, "set_file_languages", lambda x: x)

    logger = DummyLogger()
    monkeypatch.setattr(gp_mod, "get_logger", lambda: logger)

    # Create a diff file with a hunk starting at 5 and size 2 -> range 5..6
    patch_str = "@@ -1,1 +5,2 @@\n+ added line\n"
    diff_files = [make_file("file1.py", patch_str)]

    # Create a fake self that only needs get_diff_files
    fake_self = SimpleNamespace(get_diff_files=lambda: diff_files)

    # Suggestion that is inside the hunk (start=5 end=5)
    orig_sugg = {
        "relevant_file": "file1.py",
        "relevant_lines_start": 5,
        "relevant_lines_end": 5,
        "original_suggestion": {
            "existing_code": "a\nb\n",
            "improved_code": "a\nb\nc\n"
        },
        "body": "No changes here"
    }

    # Keep copy for verifying original not mutated
    import copy
    orig_copy = copy.deepcopy(orig_sugg)

    result = GithubProvider.validate_comments_inside_hunks(fake_self, [orig_sugg])

    # Should return a deep-copied list
    assert result is not [orig_sugg]
    assert result[0]["relevant_file"] == "file1.py"

    # Because the comment was inside a valid hunk, body and lines should remain unchanged
    assert result[0]["relevant_lines_start"] == orig_copy["relevant_lines_start"]
    assert result[0]["relevant_lines_end"] == orig_copy["relevant_lines_end"]
    assert result[0]["body"] == orig_copy["body"]

    # No errors expected, possibly an info log about processing
    # Since it was valid, we should have no error messages
    assert logger.errors == []


def test_validate_comments_inside_hunks_near_hunk_modified_and_diff_replaced(monkeypatch):
    # Prepare
    def fake_extract_hunk_headers(match):
        # return section_header, size1, size2, start1, start2
        # hunk start at line 5 with size 2 => range 5..6
        return ("@@ -1,1 +5,2 @@", 1, 2, 1, 5)

    monkeypatch.setattr(gp_mod, "extract_hunk_headers", fake_extract_hunk_headers)
    monkeypatch.setattr(gp_mod, "set_file_languages", lambda x: x)

    logger = DummyLogger()
    monkeypatch.setattr(gp_mod, "get_logger", lambda: logger)

    patch_str = "@@ -1,1 +5,2 @@\n+ added line\n"
    diff_files = [make_file("file2.py", patch_str)]
    fake_self = SimpleNamespace(get_diff_files=lambda: diff_files)

    # Suggestion outside the hunk but close (start 7 end 8), contains a 