import types
import pytest

from pr_agent.git_providers import gitea_provider as gp_module
from pr_agent.git_providers.gitea_provider import EDIT_TYPE, FilePatchInfo


class DummyLogger:
    def __init__(self):
        self.info_msgs = []
        self.error_msgs = []

    def info(self, msg):
        self.info_msgs.append(str(msg))

    def error(self, msg):
        self.error_msgs.append(str(msg))


class DummyInc:
    def __init__(self, is_inc: bool):
        self.is_incremental = is_inc


def make_provider_instance():
    # Create instance without calling real __init__ to avoid network/side effects
    prov = object.__new__(gp_module.GiteaProvider)
    prov.diff_files = None
    prov.git_files = []
    prov.file_diffs = {}
    prov.file_contents = {}
    prov.incremental = DummyInc(False)
    prov.unreviewed_files_set = {}
    prov.logger = DummyLogger()

    # Provide default implementations for the two content-getting helpers
    prov._get_file_content_from_latest_commit = types.MethodType(
        lambda self, filename: f"latest_content:{filename}", prov
    )
    prov._get_file_content_from_base = types.MethodType(
        lambda self, filename: f"base_content:{filename}", prov
    )

    return prov


def test_get_diff_files_early_return_round_020():
    """
    If diff_files is already set, get_diff_files should return it immediately.
    """
    prov = make_provider_instance()
    sentinel = ["SENTINEL"]
    prov.diff_files = sentinel

    result = gp_module.GiteaProvider.get_diff_files(prov)

    # Observable behavior: exact same object returned (early return)
    assert result is sentinel


def test_get_diff_files_non_incremental_avoid_load_and_unknown_status_round_020(monkeypatch):
    """
    Covers branches:
    - skip entries with filename None
    - collect invalid filenames when is_valid_file returns False
    - trigger avoid_load when MAX_FILES_ALLOWED_FULL is reached for non-incremental PRs
    - map status strings to EDIT_TYPE (including unknown mapping path)
    - check that head/base become empty when avoid_load True
    """
    prov = make_provider_instance()

    # Make MAX_FILES_ALLOWED_FULL small to hit avoid_load logic deterministically
    monkeypatch.setattr(gp_module, "MAX_FILES_ALLOWED_FULL", 1)

    # Control validity: treat 'invalid.py' as invalid, others valid
    def fake_is_valid_file(name):
        if name == "invalid.py":
            return False
        return True

    monkeypatch.setattr(gp_module, "is_valid_file", fake_is_valid_file)

    # Prepare git_files including None filename, an invalid filename, and two valid ones
    prov.git_files = [
        {"filename": None},
        {"filename": "invalid.py", "additions": 0, "deletions": 0, "status": "modified"},
        {"filename": "file_added.py", "additions": 2, "deletions": 0, "status": "added"},
        {"filename": "file_unknown_status.py", "additions": 1, "deletions": 1, "status": "weird_status"},
    ]

    # Provide diffs and contents
    prov.file_diffs = {
        "file_added.py": "patch_added",
        "file_unknown_status.py": "patch_unknown",
    }
    prov.file_contents = {"file_added.py": "head content"}

    # Non-incremental
    prov.incremental = DummyInc(False)
    prov.unreviewed_files_set = {}

    result = gp_module.GiteaProvider.get_diff_files(prov)

    # There should be two FilePatchInfo objects for valid files only
    assert isinstance(result, list)
    # file_added and file_unknown_status are valid; invalid.py excluded; None excluded
    assert {fp.filename for fp in result} == {"file_added.py", "file_unknown_status.py"}

    # For non-incremental + MAX_FILES_ALLOWED_FULL==1 with a patch for first valid file,
    # avoid_load should have been set and the provider should have logged the warning
    info_msgs = prov.logger.info_msgs
    # Should contain the 'Too many files in PR' message when counter reaches MAX_FILES_ALLOWED_FULL
    assert any("Too many files in PR" in m for m in info_msgs)
    # And also should have info about filtered invalid extensions
    assert any("Filtered out files with invalid extensions" in m for m in info_msgs)

    # Confirm mapping of statuses: added -> EDIT_TYPE.ADDED, unknown -> EDIT_TYPE.UNKNOWN
    mapping = {fp.filename: fp.edit_type for fp in result}
    assert mapping["file_added.py"] == EDIT_TYPE.ADDED
    assert mapping["file_unknown_status.py"] == EDIT_TYPE.UNKNOWN

    # Because avoid_load applied for non-incremental scenario, head_file and base_file should be empty strings
    for fp in result:
        assert fp.head_file == ""
        # base_file also should be empty when avoid_load is True (and not incremental)
        assert fp.base_file == ""


def test_get_diff_files_incremental_unreviewed_round_020(monkeypatch):
    """
    Covers branches for incremental PRs:
    - when incremental.is_incremental is True and unreviewed_files_set is non-empty,
      base_file comes from _get_file_content_from_latest_commit and unreviewed_files_set is updated
    - status mapping for 'removed' -> EDIT_TYPE.DELETED and 'renamed' -> EDIT_TYPE.RENAMED
    """
    prov = make_provider_instance()

    # Ensure MAX_FILES_ALLOWED_FULL won't trigger avoid_load for this scenario
    monkeypatch.setattr(gp_module, "MAX_FILES_ALLOWED_FULL", 1000)

    # Make all filenames valid
    monkeypatch.setattr(gp_module, "is_valid_file", lambda name: True)

    prov.git_files = [
        {"filename": "file_removed.py", "additions": 0, "deletions": 4, "status": "removed"},
        {"filename": "file_renamed.py", "additions": 1, "deletions": 1, "status": "renamed"},
    ]

    prov.file_diffs = {
        "file_removed.py": "patch_removed",
        "file_renamed.py": "patch_renamed",
    }
    prov.file_contents = {"file_renamed.py": "head renamed content"}

    # Make this an incremental PR and include an unreviewed files set initially non-empty
    prov.incremental = DummyInc(True)
    prov.unreviewed_files_set = {"file_renamed.py": "old"}

    result = gp_module.GiteaProvider.get_diff_files(prov)

    # Two items should be processed
    assert len(result) == 2
    mapping = {fp.filename: fp for fp in result}

    # For incremental, base_file should come from latest commit helper
    assert mapping["file_removed.py"].base_file == "latest_content:file_removed.py"
    assert mapping["file_renamed.py"].base_file == "latest_content:file_renamed.py"

    # unreviewed_files_set should be updated to keep the patch for processed files
    assert prov.unreviewed_files_set["file_renamed.py"] == "patch_renamed"

    # Status mapping checks
    assert mapping["file_removed.py"].edit_type == EDIT_TYPE.DELETED
    assert mapping["file_renamed.py"].edit_type == EDIT_TYPE.RENAMED
