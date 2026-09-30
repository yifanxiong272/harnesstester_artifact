import types
from types import SimpleNamespace
import pytest

from pr_agent.git_providers import codecommit_provider
from pr_agent.git_providers.codecommit_provider import CodeCommitProvider


def test_get_diff_files_cached_round_057():
    """If diff_files is already populated, get_diff_files should return it without calling get_files."""
    provider = CodeCommitProvider.__new__(CodeCommitProvider)
    # pre-populate diff_files to simulate cached behavior
    sentinel = ["cached"]
    provider.diff_files = sentinel

    # If get_files is called, the test should fail; attach a callable that raises
    provider.get_files = lambda: (_ for _ in ()).throw(AssertionError("get_files should not be called when diff_files is cached"))

    result = provider.get_diff_files()
    # The method should return the exact cached object
    assert result is sentinel


def test_get_diff_files_various_branching_round_057(monkeypatch):
    """
    Covers branches for a_blob_id / b_blob_id presence, bytes decoding, load_large_diff usage,
    and filtering via is_valid_file.
    """
    provider = CodeCommitProvider.__new__(CodeCommitProvider)
    # Ensure we start with no cached diffs
    provider.diff_files = None
    provider.repo_name = "example-repo"
    provider.pr = SimpleNamespace(destination_commit="destsha", source_commit="srcsha")

    # Create three diff items to exercise branches:
    # 1) Both a_blob_id and b_blob_id present, same paths -> old_filename should be None
    item_both_same = SimpleNamespace(
        a_blob_id="a1",
        a_path="same.py",
        b_blob_id="b1",
        b_path="same.py",
        edit_type="MODIFY",
    )
    # 2) Only b_blob_id present (added file) -> no original content
    item_only_b = SimpleNamespace(
        a_blob_id=None,
        a_path=None,
        b_blob_id="b2",
        b_path="new.bin",
        edit_type="ADD",
    )
    # 3) Only a_blob_id present (deleted file) -> no new content
    item_only_a = SimpleNamespace(
        a_blob_id="a3",
        a_path="old.txt",
        b_blob_id=None,
        b_path=None,
        edit_type="DELETE",
    )

    provider.get_files = lambda: [item_both_same, item_only_b, item_only_a]

    # Fake CodeCommit client that returns bytes or str depending on the path
    class FakeClient:
        def get_file(self, repo, path, commit):
            # Return bytes for paths expected to trigger decoding branch
            if path == "same.py":
                # return bytes for dest (original) and bytes for source (new)
                if commit == "destsha":
                    return b"orig-same"
                return b"new-same"
            if path == "new.bin":
                # return a str value (no decode path) to distinguish behavior
                return "new-bin-str"
            if path == "old.txt":
                # return bytes for original content of deleted file
                return b"old-txt-bytes"
            return ""

    provider.codecommit_client = FakeClient()

    # Capture calls and return a deterministic patch string including the filename
    def fake_load_large_diff(patch_filename, new, original):
        return f"PATCH[{patch_filename}]:{original}->{new}"

    monkeypatch.setattr(codecommit_provider, "load_large_diff", fake_load_large_diff)

    # Make is_valid_file return False for the binary new.bin path and True otherwise
    def fake_is_valid_file(filename):
        if filename is None:
            return False
        return not str(filename).endswith(".bin")

    monkeypatch.setattr(codecommit_provider, "is_valid_file", fake_is_valid_file)

    # Run the method under test
    result = provider.get_diff_files()

    # result should be a list appended only for valid files (same.py and old.txt). new.bin should be filtered out
    assert isinstance(result, list)
    # Two valid files appended (item_both_same and item_only_a)
    assert len(result) == 2

    # Helper to inspect stored FilePatchInfo objects without depending on exact attribute names.
    def inspect_info(obj):
        # Use __dict__ to find values placed by the FilePatchInfo constructor
        d = getattr(obj, "__dict__", {})
        return d

    infos = [inspect_info(x) for x in result]

    # Ensure the patches include the expected filenames and the fake_load_large_diff output
    # Look for 'PATCH[' token and the filename inside one of the values
    assert any(any(isinstance(v, str) and "PATCH[" in v and "same.py" in v for v in info.values()) for info in infos), (
        "Expected a patch containing same.py from fake_load_large_diff"
    )
    assert any(any(isinstance(v, str) and "PATCH[" in v and "old.txt" in v for v in info.values()) for info in infos), (
        "Expected a patch containing old.txt from fake_load_large_diff"
    )

    # Confirm that for the item where a_path == b_path (same.py) the old_filename value was set to None by constructor
    same_info = next(info for info in infos if any(isinstance(v, str) and "same.py" in v for v in info.values()))
    # old_filename (if present) should be None; check presence and value deterministically
    if "old_filename" in same_info:
        assert same_info["old_filename"] is None
    else:
        # If attribute named differently, ensure None is present among values which indicates old filename set to None
        assert any(v is None for v in same_info.values())

    # Check that binary file new.bin was not included (no entry contains 'new.bin')
    assert not any(any(isinstance(v, str) and "new.bin" in v for v in info.values()) for info in infos)
