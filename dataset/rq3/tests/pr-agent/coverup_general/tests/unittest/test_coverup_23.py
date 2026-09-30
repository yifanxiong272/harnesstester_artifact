# file: pr_agent/git_providers/gerrit_provider.py:234-274
# asked: {"lines": [235, 236, 237, 238, 241, 242, 243, 244, 245, 248, 249, 250, 251, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 273, 274], "branches": [[242, 243], [242, 273], [243, 244], [243, 248], [249, 250], [249, 253], [255, 256], [255, 257], [257, 258], [257, 259], [259, 260], [259, 261]]}
# gained: {"lines": [235, 236, 237, 238, 241, 242, 243, 244, 245, 248, 249, 250, 251, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 273, 274], "branches": [[242, 243], [242, 273], [243, 244], [243, 248], [249, 250], [249, 253], [255, 256], [255, 257], [257, 258], [257, 259], [259, 260], [259, 261]]}

import io

from pr_agent.algo.types import EDIT_TYPE, FilePatchInfo
from pr_agent.git_providers.gerrit_provider import GerritProvider


class FakeBlob:
    def __init__(self, content_bytes: bytes):
        self.data_stream = io.BytesIO(content_bytes)


class FakeDiffItem:
    def __init__(
        self,
        a_blob,
        b_blob,
        diff_bytes,
        b_path,
        a_path,
        new_file=False,
        deleted_file=False,
        renamed_file=False,
    ):
        self.a_blob = a_blob
        self.b_blob = b_blob
        self.diff = diff_bytes
        self.b_path = b_path
        self.a_path = a_path
        self.new_file = new_file
        self.deleted_file = deleted_file
        self.renamed_file = renamed_file


class FakeCommit:
    def __init__(self, diffs):
        self._diffs = diffs
        self.parents = [object()]  # placeholder parent

    def diff(self, parent, create_patch=True, R=True):
        # validate that diff() was called with expected kwargs
        assert create_patch is True
        assert R is True
        return self._diffs


class FakeHead:
    def __init__(self, commit):
        self.commit = commit


class FakeRepo:
    def __init__(self, diffs):
        self.head = FakeHead(FakeCommit(diffs))


def make_provider_with_diffs(diffs):
    # Create a GerritProvider instance without calling __init__
    prov = object.__new__(GerritProvider)
    prov.repo = FakeRepo(diffs)
    if hasattr(prov, "diff_files"):
        delattr(prov, "diff_files")
    return prov


def test_get_diff_files_exercises_all_branches():
    # Prepare diff items covering branches:
    # 1) Modified file: both blobs present, a_path == b_path -> old_filename None
    a_blob1 = FakeBlob(b"original content 1")
    b_blob1 = FakeBlob(b"new content 1")
    diff1 = FakeDiffItem(
        a_blob=a_blob1,
        b_blob=b_blob1,
        diff_bytes=b"diff1",
        b_path="file1.txt",
        a_path="file1.txt",
        new_file=False,
        deleted_file=False,
        renamed_file=False,
    )

    # 2) Added file: a_blob is None, b_blob present, new_file True -> EDIT_TYPE.ADDED
    b_blob2 = FakeBlob(b"added content")
    diff2 = FakeDiffItem(
        a_blob=None,
        b_blob=b_blob2,
        diff_bytes=b"diff2",
        b_path="added.txt",
        a_path="",  # no original path
        new_file=True,
        deleted_file=False,
        renamed_file=False,
    )

    # 3) Deleted file: a_blob present, b_blob is None, deleted_file True -> EDIT_TYPE.DELETED
    a_blob3 = FakeBlob(b"to be deleted")
    diff3 = FakeDiffItem(
        a_blob=a_blob3,
        b_blob=None,
        diff_bytes=b"diff3",
        b_path="deleted.txt",
        a_path="deleted.txt",
        new_file=False,
        deleted_file=True,
        renamed_file=False,
    )

    # 4) Renamed file: both present, renamed_file True, a_path != b_path -> EDIT_TYPE.RENAMED and old_filename set
    a_blob4 = FakeBlob(b"old name content")
    b_blob4 = FakeBlob(b"new name content")
    diff4 = FakeDiffItem(
        a_blob=a_blob4,
        b_blob=b_blob4,
        diff_bytes=b"diff4",
        b_path="new_name.txt",
        a_path="old_name.txt",
        new_file=False,
        deleted_file=False,
        renamed_file=True,
    )

    diffs = [diff1, diff2, diff3, diff4]

    prov = make_provider_with_diffs(diffs)
    result = prov.get_diff_files()

    # There should be 4 FilePatchInfo entries
    assert isinstance(result, list)
    assert len(result) == 4

    # Validate each entry using correct FilePatchInfo field names
    r1 = result[0]
    assert isinstance(r1, FilePatchInfo)
    assert r1.base_file == "original content 1"
    assert r1.head_file == "new content 1"
    assert r1.patch == "diff1"
    assert r1.filename == "file1.txt"
    assert r1.edit_type == EDIT_TYPE.MODIFIED
    assert r1.old_filename is None  # same path -> None

    r2 = result[1]
    assert r2.base_file == ""  # a_blob was None
    assert r2.head_file == "added content"
    assert r2.patch == "diff2"
    assert r2.filename == "added.txt"
    assert r2.edit_type == EDIT_TYPE.ADDED
    # a_path != b_path used to set old_filename; here a_path was empty string so it's different
    assert r2.old_filename == ""  # expected per code: a_path when not equal

    r3 = result[2]
    assert r3.base_file == "to be deleted"
    assert r3.head_file == ""  # b_blob was None
    assert r3.patch == "diff3"
    assert r3.filename == "deleted.txt"
    assert r3.edit_type == EDIT_TYPE.DELETED
    assert r3.old_filename is None  # a_path == b_path -> None

    r4 = result[3]
    assert r4.base_file == "old name content"
    assert r4.head_file == "new name content"
    assert r4.patch == "diff4"
    assert r4.filename == "new_name.txt"
    assert r4.edit_type == EDIT_TYPE.RENAMED
    assert r4.old_filename == "old_name.txt"  # renamed -> old filename preserved

    # Also ensure provider.diff_files was set to the returned list
    assert getattr(prov, "diff_files") is result


def test_get_diff_files_handles_empty_blobs_and_paths():
    # Test edge case: both blobs None -> both strings empty, modified by default
    diff = FakeDiffItem(
        a_blob=None,
        b_blob=None,
        diff_bytes=b"",
        b_path="empty.txt",
        a_path="empty.txt",
        new_file=False,
        deleted_file=False,
        renamed_file=False,
    )
    prov = make_provider_with_diffs([diff])
    result = prov.get_diff_files()

    assert len(result) == 1
    item = result[0]
    assert item.base_file == ""
    assert item.head_file == ""
    assert item.patch == ""  # diff was empty bytes decoded
    assert item.filename == "empty.txt"
    assert item.edit_type == EDIT_TYPE.MODIFIED
    assert item.old_filename is None
