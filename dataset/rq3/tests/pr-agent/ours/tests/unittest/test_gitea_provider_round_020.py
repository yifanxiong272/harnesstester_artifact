import pytest

import pr_agent.git_providers.gitea_provider as gitea_provider
from pr_agent.git_providers.gitea_provider import GiteaProvider, FilePatchInfo, EDIT_TYPE


class DummyLogger:
    def __init__(self):
        self.info_msgs = []
        self.error_msgs = []

    def info(self, msg):
        # ensure deterministic string storage
        self.info_msgs.append(str(msg))

    def error(self, msg):
        self.error_msgs.append(str(msg))


def _fake_settings():
    # minimal settings used by GiteaProvider.__init__
    return {
        "GITEA.PERSONAL_ACCESS_TOKEN": "fake-token",
        "GITEA.URL": "https://gitea.local",
        "GITEA.SKIP_SSL_VERIFICATION": False,
        "GITEA.SSL_CA_CERT": None,
    }


def test_get_diff_files_cached_round_020(monkeypatch):
    """If diff_files is already present, get_diff_files should return it unchanged."""
    # Patch settings so construction doesn't raise and is deterministic
    monkeypatch.setattr(gitea_provider, "get_settings", lambda: _fake_settings())
    # Keep language validator default behavior for this simple test

    provider = GiteaProvider("http://example.com")

    # Prepare a cached FilePatchInfo and assert it's returned directly
    fp = FilePatchInfo(base_file="b", head_file="h", patch="p", filename="a.py", num_minus_lines=0, num_plus_lines=1, edit_type=EDIT_TYPE.ADDED)
    provider.diff_files = [fp]

    returned = provider.get_diff_files()
    assert returned is provider.diff_files
    assert len(returned) == 1
    assert returned[0].filename == "a.py"
    assert returned[0].edit_type == EDIT_TYPE.ADDED


def test_get_diff_files_complex_branches_round_020(monkeypatch):
    """Exercise multiple branches in get_diff_files including missing filename, invalid files, avoid_load logic,
    different edit types, and logging of unknown edit type and filtered invalids.
    """
    # Patch settings and validators/constants used in the function
    monkeypatch.setattr(gitea_provider, "get_settings", lambda: _fake_settings())

    # Treat only 'invalid_ext.py' as invalid; all others valid
    def is_valid_file_stub(name):
        return False if name == "invalid_ext.py" else True

    monkeypatch.setattr(gitea_provider, "is_valid_file", is_valid_file_stub)

    # Force the threshold for 'Too many files' to 1 so the avoid_load path is triggered early
    monkeypatch.setattr(gitea_provider, "MAX_FILES_ALLOWED_FULL", 1)

    provider = GiteaProvider("http://example.com")

    # Replace logger with a deterministic dummy logger
    logger = DummyLogger()
    provider.logger = logger

    # Ensure we're not in incremental mode for this test path
    provider.incremental.is_incremental = False
    provider.unreviewed_files_set = {}

    # Prepare file_contents and file_diffs to control head/base resolution
    provider.file_contents = {
        "file2.py": "head_content_file2",
        "file4.py": "head_content_file4",
        "file5.py": "head_content_file5",
    }
    provider.file_diffs = {
        "file1.py": "patch1",
        "file3.py": "patch3",
        "file5.py": "patch5",
    }

    # Compose git_files to hit many branches
    provider.git_files = [
        {"filename": None},  # missing filename -> continue
        {"filename": "invalid_ext.py", "additions": 0, "deletions": 0, "status": ""},  # invalid -> filtered
        {"filename": "file1.py", "additions": 10, "deletions": 2, "status": "added"},
        {"filename": "file2.py", "additions": 3, "deletions": 1, "status": "deleted"},
        {"filename": "file3.py", "additions": 0, "deletions": 0, "status": "renamed"},
        {"filename": "file4.py", "additions": 1, "deletions": 1, "status": "modified"},
        {"filename": "file5.py", "additions": 0, "deletions": 0, "status": "unknown"},
    ]

    # Provide deterministic implementations for fetching base / latest commit contents
    provider._get_file_content_from_base = lambda filename: f"base:{filename}"
    provider._get_file_content_from_latest_commit = lambda filename: f"latest:{filename}"

    diff_files = provider.get_diff_files()

    # We expect the returned list to contain only the valid, named files: file1..file5 -> 5 entries
    assert len(diff_files) == 5

    by_name = {f.filename: f for f in diff_files}

    # file1 had a patch and MAX_FILES_ALLOWED_FULL == 1 so avoid_load should be True -> head/base are empty
    assert by_name["file1"].patch == "patch1"
    assert by_name["file1"].head_file == ""
    assert by_name["file1"].base_file == ""
    assert by_name["file1"].edit_type == EDIT_TYPE.ADDED

    # file2 had no patch -> full content should be loaded from file_contents and base from _get_file_content_from_base
    assert by_name["file2"].head_file == "head_content_file2"
    assert by_name["file2"].base_file == "base:file2.py"
    assert by_name["file2"].edit_type == EDIT_TYPE.DELETED

    # file3 had a patch -> RENAMED
    assert by_name["file3"].edit_type == EDIT_TYPE.RENAMED

    # file4 modified -> MODIFIED
    assert by_name["file4"].edit_type == EDIT_TYPE.MODIFIED

    # file5 had unknown status -> UNKNOWN and patch existed -> avoid_load behavior for head/base follows patch presence
    assert by_name["file5"].edit_type == EDIT_TYPE.UNKNOWN

    # Validate logging: filtered invalids and too many files info should have been logged
    assert any("invalid_ext.py" in m for m in logger.info_msgs), "expected invalid filename mention in info logs"
    assert any("Too many files" in m for m in logger.info_msgs), "expected 'Too many files' mention in info logs"

    # Unknown edit type should produce an error log entry
    assert any("Unknown edit type" in m for m in logger.error_msgs), "expected unknown edit type to be logged as error"
