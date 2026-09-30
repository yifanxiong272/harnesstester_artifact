import io
import types
import pytest

import pr_agent.git_providers.gerrit_provider as gp


class _StubFilePatchInfo:
    def __init__(self, original, new, diff, path, edit_type=None, old_filename=None):
        # store exactly what was passed for deterministic assertions
        self.original = original
        self.new = new
        self.diff = diff
        self.path = path
        self.edit_type = edit_type
        self.old_filename = old_filename

    def __repr__(self):
        return (
            f"_StubFilePatchInfo(original={self.original!r}, new={self.new!r}, "
            f"diff={self.diff!r}, path={self.path!r}, edit_type={self.edit_type!r}, "
            f"old_filename={self.old_filename!r})"
        )


class _StubEditType:
    MODIFIED = "MODIFIED"
    ADDED = "ADDED"
    DELETED = "DELETED"
    RENAMED = "RENAMED"


class FakeBlob:
    def __init__(self, data: bytes):
        # provide a data_stream with a read() method that returns bytes
        self.data_stream = io.BytesIO(data)


class FakeDiffItem:
    def __init__(self, *, a_blob=None, b_blob=None, diff=b"", b_path="p", a_path="p",
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
    def __init__(self, diffs):
        # parents needs at least one element (used in call)
        self.parents = ["parent"]
        self._diffs = diffs

    def diff(self, parent, create_patch=True, R=True):
        # ignore provided args and return the preconstructed diffs
        assert parent == self.parents[0]
        # ensure kwargs are honored signature-wise but not used
        return list(self._diffs)


class FakeHead:
    def __init__(self, commit):
        self.commit = commit


class FakeRepo:
    def __init__(self, commit):
        self.head = FakeHead(commit)


def _make_provider_with_diffs(diffs):
    # Patch the module-level symbols so the test does not depend on real types
    gp.FilePatchInfo = _StubFilePatchInfo
    gp.EDIT_TYPE = _StubEditType

    # construct a GerritProvider instance without running its __init__
    provider = object.__new__(gp.GerritProvider)
    fake_commit = FakeCommit(diffs)
    provider.repo = FakeRepo(fake_commit)
    # ensure no leftover diff_files
    provider.diff_files = None
    return provider


def test_get_diff_files_all_branches_round_075():
    # Create a variety of diff items to exercise branches:
    # 1) modified file: both blobs present, a_path == b_path -> old_filename None
    diff1 = FakeDiffItem(
        a_blob=FakeBlob(b"orig content 1"),
        b_blob=FakeBlob(b"new content 1"),
        diff=b"@@ -1 +1 @@\n+new1",
        b_path="file1.txt",
        a_path="file1.txt",
        new_file=False,
        deleted_file=False,
        renamed_file=False,
    )

    # 2) added file: a_blob is None, b_blob present, new_file True, a_path != b_path -> old_filename set
    diff2 = FakeDiffItem(
        a_blob=None,
        b_blob=FakeBlob(b"new content 2"),
        diff=b"@@ -0 +1 @@\n+added",
        b_path="file2.txt",
        a_path="OLD_file2.txt",
        new_file=True,
        deleted_file=False,
        renamed_file=False,
    )

    # 3) deleted file: a_blob present, b_blob is None, deleted_file True
    diff3 = FakeDiffItem(
        a_blob=FakeBlob(b"orig content 3"),
        b_blob=None,
        diff=b"@@ -1 +0 @@\n-deleted",
        b_path="file3.txt",
        a_path="file3.txt",
        new_file=False,
        deleted_file=True,
        renamed_file=False,
    )

    # 4) renamed file: both blobs present, renamed_file True
    diff4 = FakeDiffItem(
        a_blob=FakeBlob(b"orig content 4"),
        b_blob=FakeBlob(b"new content 4"),
        diff=b"@@ -1 +1 @@\n-rename",
        b_path="file4_new.txt",
        a_path="file4_old.txt",
        new_file=False,
        deleted_file=False,
        renamed_file=True,
    )

    provider = _make_provider_with_diffs([diff1, diff2, diff3, diff4])

    result = provider.get_diff_files()

    # The function should return the same list stored on the provider
    assert result is provider.diff_files
    assert len(result) == 4

    # Validate item 1 (modified, old_filename None)
    it1 = result[0]
    assert isinstance(it1, _StubFilePatchInfo)
    assert it1.original == "orig content 1"
    assert it1.new == "new content 1"
    assert it1.diff == "@@ -1 +1 @@\n+new1"
    assert it1.path == "file1.txt"
    assert it1.edit_type == _StubEditType.MODIFIED
    assert it1.old_filename is None

    # Validate item 2 (added)
    it2 = result[1]
    assert it2.original == ""  # a_blob was None
    assert it2.new == "new content 2"
    assert it2.diff == "@@ -0 +1 @@\n+added"
    assert it2.path == "file2.txt"
    assert it2.edit_type == _StubEditType.ADDED
    # since a_path != b_path we expect old_filename to be the a_path
    assert it2.old_filename == "OLD_file2.txt"

    # Validate item 3 (deleted)
    it3 = result[2]
    assert it3.original == "orig content 3"
    assert it3.new == ""  # b_blob was None
    assert it3.diff == "@@ -1 +0 @@\n-deleted"
    assert it3.path == "file3.txt"
    assert it3.edit_type == _StubEditType.DELETED
    # a_path == b_path => old filename None
    assert it3.old_filename is None

    # Validate item 4 (renamed)
    it4 = result[3]
    assert it4.original == "orig content 4"
    assert it4.new == "new content 4"
    assert it4.diff == "@@ -1 +1 @@\n-rename"
    assert it4.path == "file4_new.txt"
    assert it4.edit_type == _StubEditType.RENAMED
    assert it4.old_filename == "file4_old.txt"


def test_get_diff_files_empty_diffs_round_075():
    # if the repo returns an empty list, get_diff_files should return empty list and set attribute
    provider = _make_provider_with_diffs([])
    res = provider.get_diff_files()
    assert res == []
    assert provider.diff_files == []
