# file: pr_agent/git_providers/gitea_provider.py:444-518
# asked: {"lines": [446, 447, 449, 450, 451, 452, 453, 454, 455, 457, 458, 459, 461, 462, 463, 464, 465, 467, 468, 469, 470, 472, 473, 476, 478, 479, 480, 482, 483, 485, 487, 488, 489, 491, 492, 493, 494, 495, 496, 497, 498, 500, 501, 503, 504, 505, 506, 507, 508, 509, 510, 512, 514, 515, 517, 518], "branches": [[446, 447], [446, 449], [452, 453], [452, 514], [454, 455], [454, 457], [457, 458], [457, 461], [467, 468], [467, 472], [469, 470], [469, 472], [472, 473], [472, 476], [478, 479], [478, 482], [482, 483], [482, 485], [491, 492], [491, 493], [493, 494], [493, 495], [495, 496], [495, 497], [497, 498], [497, 500], [514, 515], [514, 517]]}
# gained: {"lines": [446, 449, 450, 451, 452, 453, 454, 455, 457, 458, 459, 461, 462, 463, 464, 465, 467, 468, 469, 470, 472, 473, 476, 478, 479, 480, 482, 483, 485, 487, 488, 489, 491, 492, 493, 494, 495, 496, 497, 498, 500, 501, 503, 504, 505, 506, 507, 508, 509, 510, 512, 514, 515, 517, 518], "branches": [[446, 449], [452, 453], [452, 514], [454, 455], [454, 457], [457, 458], [457, 461], [467, 468], [467, 472], [469, 470], [469, 472], [472, 473], [472, 476], [478, 479], [478, 482], [482, 483], [482, 485], [491, 492], [491, 493], [493, 494], [493, 495], [495, 496], [495, 497], [497, 498], [497, 500], [514, 515], [514, 517]]}

import types
import pytest

from pr_agent.algo.types import EDIT_TYPE
from pr_agent.git_providers.gitea_provider import GiteaProvider
import pr_agent.git_providers.gitea_provider as gitea_module


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def error(self, msg):
        self.errors.append(msg)


def make_instance():
    inst = object.__new__(GiteaProvider)
    # set defaults that will be overridden in tests
    inst.diff_files = None
    inst.git_files = []
    inst.file_diffs = {}
    inst.file_contents = {}
    inst.incremental = types.SimpleNamespace(is_incremental=False)
    inst.unreviewed_files_set = {}
    inst.logger = DummyLogger()
    # default implementations
    inst._get_file_content_from_latest_commit = lambda filename: f"latest:{filename}"
    inst._get_file_content_from_base = lambda filename: f"base:{filename}"
    return inst


def test_get_diff_files_non_incremental_and_various_statuses(monkeypatch):
    # Ensure is_valid_file uses only .py as valid
    monkeypatch.setattr(gitea_module, "is_valid_file", lambda name: isinstance(name, str) and name.endswith(".py"))
    # Force MAX_FILES_ALLOWED_FULL small to trigger avoid_load logic
    monkeypatch.setattr(gitea_module, "MAX_FILES_ALLOWED_FULL", 2)

    inst = make_instance()

    inst.git_files = [
        {"filename": "valid1.py", "additions": 1, "deletions": 0, "status": "added"},
        {"filename": "invalid.xyz", "additions": 0, "deletions": 0, "status": "modified"},
        {"filename": "valid2.py", "additions": 2, "deletions": 1, "status": "removed"},
        {"filename": "valid3.py", "additions": 0, "deletions": 0, "status": "renamed"},
        {"filename": "valid4.py", "additions": 5, "deletions": 2, "status": "modified"},
        {"filename": "valid5.py", "additions": 0, "deletions": 0, "status": "unknownstatus"},
    ]

    # Provide patches for some files to trigger avoid_load when counter >= MAX
    inst.file_diffs = {
        "valid2.py": "patch2",
        "valid3.py": "patch3",
        "valid4.py": "patch4",
    }

    # Provide file contents for non-avoided files
    inst.file_contents = {
        "valid1.py": "head content 1",
        "valid5.py": "head content 5",
    }

    # Provide base content loader
    inst._get_file_content_from_base = lambda filename: f"base_content_for:{filename}"

    # Ensure incremental is False so avoid_load logic can trigger
    inst.incremental = types.SimpleNamespace(is_incremental=False)
    inst.unreviewed_files_set = {}  # won't be used in non-incremental mode

    # Run
    diff_files = GiteaProvider.get_diff_files(inst)

    # We expect 5 valid files (one invalid was filtered)
    assert len(diff_files) == 5

    # Map results by filename for easier assertions
    by_name = {f.filename: f for f in diff_files}

    # valid1: not avoided, added
    vf1 = by_name["valid1.py"]
    assert vf1.head_file == "head content 1"
    assert vf1.base_file == "base_content_for:valid1.py"
    assert vf1.edit_type == EDIT_TYPE.ADDED
    assert vf1.num_plus_lines == 1
    assert vf1.num_minus_lines == 0
    assert vf1.patch == ""  # no patch provided

    # valid2: counter == MAX_FILES_ALLOWED_FULL and has patch -> avoid_load True
    vf2 = by_name["valid2.py"]
    assert vf2.head_file == ""  # avoided
    assert vf2.base_file == ""  # avoided
    assert vf2.edit_type == EDIT_TYPE.DELETED
    assert vf2.patch == "patch2"

    # valid3: counter > MAX and has patch -> avoid_load True
    vf3 = by_name["valid3.py"]
    assert vf3.head_file == ""
    assert vf3.base_file == ""
    assert vf3.edit_type == EDIT_TYPE.RENAMED
    assert vf3.patch == "patch3"

    # valid4: also avoided due to patch and counter over limit
    vf4 = by_name["valid4.py"]
    assert vf4.head_file == ""
    assert vf4.base_file == ""
    assert vf4.edit_type == EDIT_TYPE.MODIFIED
    assert vf4.patch == "patch4"

    # valid5: unknown status, no patch -> should load content and log error
    vf5 = by_name["valid5.py"]
    assert vf5.head_file == "head content 5"
    assert vf5.base_file == "base_content_for:valid5.py"
    assert vf5.edit_type == EDIT_TYPE.UNKNOWN
    assert vf5.patch == ""

    # Logging checks: info about too many files and filtered invalid extension
    infos = inst.logger.infos
    assert any("Too many files in PR" in m for m in infos)
    assert any("Filtered out files with invalid extensions" in m for m in infos)

    # Error logging for unknown status must have been called
    errors = inst.logger.errors
    assert any("Unknown edit type" in m for m in errors)


def test_get_diff_files_incremental_updates_unreviewed(monkeypatch):
    # Valid only .py files
    monkeypatch.setattr(gitea_module, "is_valid_file", lambda name: isinstance(name, str) and name.endswith(".py"))
    # Ensure MAX is large so avoid_load does not trigger
    monkeypatch.setattr(gitea_module, "MAX_FILES_ALLOWED_FULL", 9999)

    inst = make_instance()

    # Include one file with filename and one entry without filename to trigger the continue branch
    inst.git_files = [
        {"filename": "inc.py", "additions": 3, "deletions": 1, "status": "changed"},
        {"no_filename_here": True},
    ]

    inst.file_diffs = {"inc.py": "inc-patch"}
    inst.file_contents = {"inc.py": "inc-head-content"}

    # incremental true and unreviewed_files_set must be truthy to take that branch
    inst.incremental = types.SimpleNamespace(is_incremental=True)
    inst.unreviewed_files_set = {"placeholder": "value"}

    # Provide methods for retrieving content
    inst._get_file_content_from_latest_commit = lambda filename: f"latest-content-for:{filename}"
    inst._get_file_content_from_base = lambda filename: f"base-content-for:{filename}"

    # Run
    diff_files = GiteaProvider.get_diff_files(inst)

    # Only the one valid file should be returned
    assert len(diff_files) == 1
    fp = diff_files[0]
    assert fp.filename == "inc.py"
    # In incremental mode base_file should come from latest commit
    assert fp.base_file == "latest-content-for:inc.py"
    assert fp.head_file == "inc-head-content"
    assert fp.patch == "inc-patch"
    assert fp.edit_type == EDIT_TYPE.MODIFIED

    # unreviewed_files_set should have been updated with the file mapping to its patch
    assert inst.unreviewed_files_set.get("inc.py") == "inc-patch"
