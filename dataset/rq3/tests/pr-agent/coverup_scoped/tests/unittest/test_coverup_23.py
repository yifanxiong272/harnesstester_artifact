# file: pr_agent/git_providers/local_git_provider.py:65-98
# asked: {"lines": [66, 67, 68, 69, 71, 72, 73, 74, 76, 77, 78, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 97, 98], "branches": [[72, 73], [72, 97], [73, 74], [73, 76], [77, 78], [77, 80], [82, 83], [82, 84], [84, 85], [84, 86], [86, 87], [86, 88]]}
# gained: {"lines": [66, 67, 68, 69, 71, 72, 73, 74, 76, 77, 78, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 97, 98], "branches": [[72, 73], [72, 97], [73, 74], [73, 76], [77, 78], [77, 80], [82, 83], [82, 84], [84, 85], [84, 86], [86, 87], [86, 88]]}

import types
from pr_agent.git_providers.local_git_provider import LocalGitProvider
from pr_agent.algo.types import EDIT_TYPE
import pytest


class FakeDataStream:
    def __init__(self, data: bytes):
        self._data = data
        self.read_called = False

    def read(self):
        self.read_called = True
        return self._data


class FakeBlob:
    def __init__(self, data: bytes):
        self.data_stream = FakeDataStream(data)


class FakeDiffItem:
    def __init__(self, *, a_blob=None, b_blob=None, diff=b"", b_path=None, a_path=None,
                 new_file=False, deleted_file=False, renamed_file=False):
        self.a_blob = a_blob
        self.b_blob = b_blob
        self.diff = diff
        self.b_path = b_path
        self.a_path = a_path
        self.new_file = new_file
        self.deleted_file = deleted_file
        self.renamed_file = renamed_file


class FakeCommit:
    def __init__(self, diffs_list, record):
        # diffs_list is returned by diff()
        self._diffs = diffs_list
        # record is a dict used to capture call args for assertions
        self._record = record

    def diff(self, base, create_patch=False, R=False):
        # record what was passed in
        self._record['base'] = base
        self._record['create_patch'] = create_patch
        self._record['R'] = R
        return self._diffs


class FakeHead:
    def __init__(self, commit):
        self.commit = commit


class FakeBranches(dict):
    def __getitem__(self, item):
        # return a simple marker object for branch
        return f"branch-{item}"


class FakeRepo:
    def __init__(self, commit):
        self.head = FakeHead(commit)
        self.branches = FakeBranches()
        self.merge_base_called_with = None

    def merge_base(self, head, branch):
        # record args and return a fake base object
        self.merge_base_called_with = (head, branch)
        return "fake-merge-base"


def make_provider_with_diffs(diffs):
    """
    Create a LocalGitProvider instance (without calling __init__) and attach a fake repo
    that will return the provided diffs from head.commit.diff(...)
    """
    record = {}
    commit = FakeCommit(diffs, record)
    fake_repo = FakeRepo(commit)
    # create instance without running __init__
    provider = object.__new__(LocalGitProvider)
    provider.repo = fake_repo
    provider.target_branch_name = "target-branch"
    provider.diff_files = None
    return provider, record


def test_get_diff_files_all_edit_types_and_old_filename_behavior():
    # Prepare diff items covering MODIFIED, ADDED, DELETED, RENAMED
    modified = FakeDiffItem(
        a_blob=FakeBlob(b"old content 1"),
        b_blob=FakeBlob(b"new content 1"),
        diff=b"@@ -1 +1 @@\n-old content 1\n+new content 1\n",
        b_path="file1.txt",
        a_path="file1.txt",  # same path -> old_filename should be None
        new_file=False,
        deleted_file=False,
        renamed_file=False,
    )

    added = FakeDiffItem(
        a_blob=None,
        b_blob=FakeBlob(b"added content"),
        diff=b"@@ -0 +1 @@\n+added content\n",
        b_path="file2.txt",
        a_path=None,  # a_path different from b_path (None != 'file2.txt') -> old_filename becomes a_path (None)
        new_file=True,
        deleted_file=False,
        renamed_file=False,
    )

    deleted = FakeDiffItem(
        a_blob=FakeBlob(b"to be deleted"),
        b_blob=None,
        diff=b"@@ -1 +0 @@\n-to be deleted\n",
        b_path="file3.txt",
        a_path="file3.txt",
        new_file=False,
        deleted_file=True,
        renamed_file=False,
    )

    renamed = FakeDiffItem(
        a_blob=FakeBlob(b"old name content"),
        b_blob=FakeBlob(b"new name content"),
        diff=b"@@ -1 +1 @@\n-old name content\n+new name content\n",
        b_path="newname.txt",
        a_path="oldname.txt",
        new_file=False,
        deleted_file=False,
        renamed_file=True,
    )

    provider, record = make_provider_with_diffs([modified, added, deleted, renamed])

    result = LocalGitProvider.get_diff_files(provider)

    # Basic checks
    assert isinstance(result, list)
    assert len(result) == 4
    # Check that merge_base was called with provider.repo.head and the target branch marker
    assert provider.repo.merge_base_called_with is not None
    assert provider.repo.merge_base_called_with[1] == provider.repo.branches[provider.target_branch_name]

    # Check recorded diff() kwargs
    assert record.get('create_patch') is True
    assert record.get('R') is True
    assert record.get('base') == "fake-merge-base"

    # Map by filename for easier assertions
    by_name = {fp.filename: fp for fp in result}

    # Modified file checks
    fp1 = by_name["file1.txt"]
    assert fp1.base_file == "old content 1"
    assert fp1.head_file == "new content 1"
    assert "old content 1" in fp1.patch
    assert fp1.edit_type == EDIT_TYPE.MODIFIED
    assert fp1.old_filename is None  # same a_path and b_path -> None

    # Added file checks
    fp2 = by_name["file2.txt"]
    assert fp2.base_file == ""  # a_blob was None -> empty string
    assert fp2.head_file == "added content"
    assert fp2.edit_type == EDIT_TYPE.ADDED
    # a_path was None while b_path is 'file2.txt' -> old_filename equals a_path (which is None)
    assert fp2.old_filename is None

    # Deleted file checks
    fp3 = by_name["file3.txt"]
    assert fp3.base_file == "to be deleted"
    assert fp3.head_file == ""  # b_blob was None -> empty string
    assert fp3.edit_type == EDIT_TYPE.DELETED
    assert fp3.old_filename is None  # a_path == b_path -> None

    # Renamed file checks
    fp4 = by_name["newname.txt"]
    assert fp4.base_file == "old name content"
    assert fp4.head_file == "new name content"
    assert fp4.edit_type == EDIT_TYPE.RENAMED
    assert fp4.old_filename == "oldname.txt"  # different a_path -> preserved

    # Ensure provider.diff_files was set
    assert provider.diff_files is result


def test_get_diff_files_with_empty_diff_list_sets_empty_and_returns_list():
    provider, record = make_provider_with_diffs([])

    result = LocalGitProvider.get_diff_files(provider)

    assert isinstance(result, list)
    assert result == []
    assert provider.diff_files == []
    # Even if no diffs, merge_base should still have been called and recorded
    assert provider.repo.merge_base_called_with is not None
    # diff should have been called and recorded as well
    assert record.get('create_patch') is True
    assert record.get('R') is True
