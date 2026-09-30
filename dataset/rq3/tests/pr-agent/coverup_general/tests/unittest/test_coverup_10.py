# file: pr_agent/git_providers/gitea_provider.py:444-518
# asked: {"lines": [446, 447, 449, 450, 451, 452, 453, 454, 455, 457, 458, 459, 461, 462, 463, 464, 465, 467, 468, 469, 470, 472, 473, 476, 478, 479, 480, 482, 483, 485, 487, 488, 489, 491, 492, 493, 494, 495, 496, 497, 498, 500, 501, 503, 504, 505, 506, 507, 508, 509, 510, 512, 514, 515, 517, 518], "branches": [[446, 447], [446, 449], [452, 453], [452, 514], [454, 455], [454, 457], [457, 458], [457, 461], [467, 468], [467, 472], [469, 470], [469, 472], [472, 473], [472, 476], [478, 479], [478, 482], [482, 483], [482, 485], [491, 492], [491, 493], [493, 494], [493, 495], [495, 496], [495, 497], [497, 498], [497, 500], [514, 515], [514, 517]]}
# gained: {"lines": [446, 449, 450, 451, 452, 453, 454, 455, 457, 458, 459, 461, 462, 463, 464, 465, 467, 468, 469, 470, 472, 473, 476, 478, 479, 480, 482, 483, 485, 487, 488, 489, 491, 492, 493, 495, 497, 498, 500, 501, 503, 504, 505, 506, 507, 508, 509, 510, 512, 514, 515, 517, 518], "branches": [[446, 449], [452, 453], [452, 514], [454, 455], [454, 457], [457, 458], [457, 461], [467, 468], [467, 472], [469, 470], [469, 472], [472, 473], [472, 476], [478, 479], [478, 482], [482, 483], [482, 485], [491, 492], [491, 493], [493, 495], [495, 497], [497, 498], [497, 500], [514, 515], [514, 517]]}

import types
from types import SimpleNamespace

import pytest

import pr_agent.git_providers.gitea_provider as gitea_mod
from pr_agent.git_providers.gitea_provider import GiteaProvider
from pr_agent.git_providers.gitea_provider import FilePatchInfo
from pr_agent.algo.types import EDIT_TYPE


class FakeLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def error(self, msg):
        self.errors.append(msg)


def _make_provider_instance():
    # Create instance without invoking __init__
    inst = GiteaProvider.__new__(GiteaProvider)
    # assign defaults used by get_diff_files
    inst.diff_files = []
    inst.git_files = []
    inst.file_contents = {}
    inst.file_diffs = {}
    inst.incremental = SimpleNamespace(is_incremental=False)
    inst.unreviewed_files_set = {}
    inst.logger = FakeLogger()
    return inst


def test_get_diff_files_non_incremental_with_avoid_load_and_invalids(monkeypatch):
    # Reduce the MAX_FILES_ALLOWED_FULL to a small number to hit the avoid_load logic quickly
    monkeypatch.setattr(gitea_mod, "MAX_FILES_ALLOWED_FULL", 2)

    # Monkeypatch is_valid_file to treat 'ignored.lock' as invalid, others valid
    def fake_is_valid_file(filename, bad_extensions=None):
        if not filename:
            return False
        if filename == "ignored.lock":
            return False
        return True

    monkeypatch.setattr(gitea_mod, "is_valid_file", fake_is_valid_file)

    gp = _make_provider_instance()

    # Provide file content / diffs and stub base retrieval
    gp.file_contents = {
        "a.py": "print('a')",
        "b.py": "print('b')",
        "c.py": "print('c')",
    }
    gp.file_diffs = {
        "a.py": "patch-a",
        "b.py": "patch-b",
        "c.py": "patch-c",
    }

    # _get_file_content_from_base should be called for files when avoid_load is False
    gp._get_file_content_from_base = lambda fn: f"base:{fn}"
    gp._get_file_content_from_latest_commit = lambda fn: f"latest:{fn}"

    # Build git_files to exercise branches:
    # - one entry with filename None (skipped)
    # - one invalid filename (ignored.lock) -> should be filtered out and logged
    # - three valid files to trigger avoid_load on the second valid (MAX=2)
    gp.git_files = [
        {"filename": None, "additions": 0, "deletions": 0, "status": "modified"},
        {"filename": "ignored.lock", "additions": 0, "deletions": 0, "status": "modified"},
        {"filename": "a.py", "additions": 1, "deletions": 0, "status": "added"},
        {"filename": "b.py", "additions": 2, "deletions": 1, "status": "modified"},
        {"filename": "c.py", "additions": 0, "deletions": 3, "status": "weird"},
    ]

    # Ensure incremental flag is False and unreviewed_files_set empty
    gp.incremental = SimpleNamespace(is_incremental=False)
    gp.unreviewed_files_set = {}

    result = gp.get_diff_files()

    # Expect 3 valid FilePatchInfo entries (a.py, b.py, c.py)
    assert isinstance(result, list)
    assert len(result) == 3

    # Map results by filename for assertions
    res_map = {f.filename: f for f in result}

    # a.py was processed before reaching MAX -> should have head and base filled and edit_type ADDED
    a = res_map["a.py"]
    assert a.head_file == "print('a')"
    assert a.base_file == "base:a.py"
    assert a.patch == "patch-a"
    assert a.edit_type == EDIT_TYPE.ADDED
    assert a.num_plus_lines == 1
    assert a.num_minus_lines == 0

    # b.py should hit avoid_load (since counter_valid == MAX_FILES_ALLOWED_FULL) -> head and base empty
    b = res_map["b.py"]
    assert b.head_file == ""
    assert b.base_file == ""
    assert b.patch == "patch-b"
    assert b.edit_type == EDIT_TYPE.MODIFIED

    # c.py should also have avoid_load True (since after threshold) and unknown edit type for status 'weird'
    c = res_map["c.py"]
    assert c.head_file == ""
    assert c.base_file == ""
    assert c.patch == "patch-c"
    assert c.edit_type == EDIT_TYPE.UNKNOWN

    # Logger should have recorded the "Too many files" info (once) and the filtered invalid files info
    info_msgs = " | ".join(gp.logger.infos)
    assert "Too many files in PR, will avoid loading full content for rest of files" in info_msgs
    assert "Filtered out files with invalid extensions" in info_msgs

    # Error log should have at least one entry for the unknown edit type 'weird'
    assert any("Unknown edit type" in e for e in gp.logger.errors)


def test_get_diff_files_incremental_updates_unreviewed_files_set(monkeypatch):
    # Ensure MAX is large so avoid_load does not trigger
    monkeypatch.setattr(gitea_mod, "MAX_FILES_ALLOWED_FULL", 100)

    # All files considered valid
    monkeypatch.setattr(gitea_mod, "is_valid_file", lambda filename, bad_extensions=None: True)

    gp = _make_provider_instance()

    # Prepare a single file that is unreviewed initially
    gp.git_files = [
        {"filename": "a.py", "additions": 4, "deletions": 1, "status": "modified"},
    ]
    gp.file_diffs = {"a.py": "patch-inc-a"}
    gp.file_contents = {"a.py": "print('inc a')"}

    # incremental True and unreviewed_files_set truthy -> triggers latest commit base retrieval
    gp.incremental = SimpleNamespace(is_incremental=True)
    gp.unreviewed_files_set = {"a.py": None}

    gp._get_file_content_from_latest_commit = lambda fn: f"latest:{fn}"
    gp._get_file_content_from_base = lambda fn: f"base:{fn}"

    out = gp.get_diff_files()

    # One result and types are correct
    assert len(out) == 1
    fpi = out[0]
    assert isinstance(fpi, FilePatchInfo)
    assert fpi.filename == "a.py"
    # For incremental + unreviewed set, base should come from latest commit
    assert fpi.base_file == "latest:a.py"
    # head_file should be loaded from file_contents since avoid_load not set
    assert fpi.head_file == "print('inc a')"
    assert fpi.patch == "patch-inc-a"
    assert fpi.edit_type == EDIT_TYPE.MODIFIED

    # unreviewed_files_set should have been updated to include the patch for the file
    assert gp.unreviewed_files_set["a.py"] == "patch-inc-a"
