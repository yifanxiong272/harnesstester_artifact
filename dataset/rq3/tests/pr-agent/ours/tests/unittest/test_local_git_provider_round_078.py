import types
from pr_agent.git_providers.local_git_provider import LocalGitProvider
from pr_agent.algo.types import EDIT_TYPE, FilePatchInfo


def _make_blob(content: str):
    class Stream:
        def read(self_inner):
            return content.encode("utf-8")

    class Blob:
        def __init__(self):
            self.data_stream = Stream()

    return Blob()


class _DummyDiffItem:
    def __init__(self, *, a_blob=None, b_blob=None, diff=b"", a_path="a.txt", b_path="a.txt", new_file=False, deleted_file=False, renamed_file=False):
        self.a_blob = a_blob
        self.b_blob = b_blob
        self.diff = diff
        self.a_path = a_path
        self.b_path = b_path
        self.new_file = new_file
        self.deleted_file = deleted_file
        self.renamed_file = renamed_file


class _DummyCommit:
    def __init__(self, diffs):
        self._diffs = diffs

    def diff(self, _merge_base_result, *, create_patch=True, R=True):
        # ignore args, return configured list
        return self._diffs


class _DummyHead:
    def __init__(self, commit):
        self.commit = commit


class _DummyRepo:
    def __init__(self, diffs, branches_mapping=None):
        self._diffs = diffs
        self.head = _DummyHead(_DummyCommit(diffs))
        # allow indexing like branches[name]
        self.branches = branches_mapping or {}

    def merge_base(self, head, branch):
        # return an opaque object used as first argument to commit.diff; not used by our DummyCommit
        return (head, branch)


def test_get_diff_files_various_kinds_round_078():
    """
    Exercise get_diff_files across modified, added, deleted, and renamed files.
    Ensures a_blob/b_blob None paths and different edit_type branches are covered.
    """
    # prepare diff items covering branches:
    # 1) Modified file: both blobs present, same path -> old_filename None
    modified = _DummyDiffItem(
        a_blob=_make_blob("orig content"),
        b_blob=_make_blob("new content"),
        diff=b"-orig\n+new\n",
        a_path="file1.txt",
        b_path="file1.txt",
        new_file=False,
        deleted_file=False,
        renamed_file=False,
    )

    # 2) Added file: a_blob None, b_blob present -> ADDED
    added = _DummyDiffItem(
        a_blob=None,
        b_blob=_make_blob("added content"),
        diff=b"+added\n",
        a_path="/dev/null",
        b_path="file2.txt",
        new_file=True,
        deleted_file=False,
        renamed_file=False,
    )

    # 3) Deleted file: a_blob present, b_blob None -> DELETED
    deleted = _DummyDiffItem(
        a_blob=_make_blob("deleted content"),
        b_blob=None,
        diff=b"-deleted\n",
        a_path="file3.txt",
        b_path="/dev/null",
        new_file=False,
        deleted_file=True,
        renamed_file=False,
    )

    # 4) Renamed file: both blobs present, paths differ -> RENAMED and old_filename set
    renamed = _DummyDiffItem(
        a_blob=_make_blob("old name content"),
        b_blob=_make_blob("new name content"),
        diff=b"rename old->new\n",
        a_path="old_name.txt",
        b_path="new_name.txt",
        new_file=False,
        deleted_file=False,
        renamed_file=True,
    )

    diffs = [modified, added, deleted, renamed]

    # Create provider instance without invoking __init__ to avoid real Repo operations.
    provider = object.__new__(LocalGitProvider)
    # set required attributes: repo and target_branch_name
    provider.repo = _DummyRepo(diffs, branches_mapping={"main": object()})
    provider.target_branch_name = "main"

    # Call method under test
    result = LocalGitProvider.get_diff_files(provider)

    # Build expected FilePatchInfo instances matching how the source constructs them
    expected = [
        FilePatchInfo("orig content", "new content", modified.diff.decode("utf-8"), "file1.txt", edit_type=EDIT_TYPE.MODIFIED, old_filename=None),
        FilePatchInfo("", "added content", added.diff.decode("utf-8"), "file2.txt", edit_type=EDIT_TYPE.ADDED, old_filename=None),
        FilePatchInfo("deleted content", "", deleted.diff.decode("utf-8"), "/dev/null", edit_type=EDIT_TYPE.DELETED, old_filename=None),
        FilePatchInfo("old name content", "new name content", renamed.diff.decode("utf-8"), "new_name.txt", edit_type=EDIT_TYPE.RENAMED, old_filename="old_name.txt"),
    ]

    # Assert length and that items equal expected ones (constructor & equality used as oracle)
    assert isinstance(result, list), "expected list from get_diff_files"
    assert len(result) == len(expected)

    for got, exp in zip(result, expected):
        # rely on FilePatchInfo equality/attributes; check both repr and attribute access as guard
        assert got == exp, f"expected {exp!r}, got {got!r}"


def test_get_diff_files_handles_empty_diffs_and_sets_internal_state_round_078():
    """
    When there are no diffs, get_diff_files should return an empty list and set provider.diff_files accordingly.
    """
    provider = object.__new__(LocalGitProvider)
    provider.repo = _DummyRepo([], branches_mapping={"main": object()})
    provider.target_branch_name = "main"

    result = provider.get_diff_files()
    assert result == []
    # internal state should be updated
    assert hasattr(provider, "diff_files")
    assert provider.diff_files == []
