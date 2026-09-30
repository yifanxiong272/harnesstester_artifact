# file: pr_agent/git_providers/codecommit_provider.py:103-157
# asked: {"lines": [113, 114, 116, 118, 119, 120, 121, 122, 123, 124, 125, 126, 128, 130, 131, 132, 133, 134, 136, 138, 141, 142, 143, 144, 145, 146, 147, 148, 149, 154, 155, 157], "branches": [[113, 114], [113, 116], [119, 120], [119, 157], [121, 122], [121, 128], [125, 126], [125, 130], [130, 131], [130, 136], [133, 134], [133, 138], [154, 119], [154, 155]]}
# gained: {"lines": [113, 114, 116, 118, 119, 120, 121, 122, 123, 124, 125, 126, 128, 130, 131, 132, 133, 134, 136, 138, 141, 142, 143, 144, 145, 146, 147, 148, 149, 154, 155, 157], "branches": [[113, 114], [113, 116], [119, 120], [119, 157], [121, 122], [121, 128], [125, 126], [130, 131], [130, 136], [133, 134], [133, 138], [154, 119], [154, 155]]}

import types
import pytest

from pr_agent.git_providers import codecommit_provider
from pr_agent.git_providers.codecommit_provider import CodeCommitProvider


class DummyPR:
    def __init__(self, source_commit="src", destination_commit="dst"):
        self.source_commit = source_commit
        self.destination_commit = destination_commit


class DummyDiffItem:
    def __init__(self, a_blob_id, a_path, b_blob_id, b_path, edit_type):
        self.a_blob_id = a_blob_id
        self.a_path = a_path
        self.b_blob_id = b_blob_id
        self.b_path = b_path
        self.edit_type = edit_type


def make_provider():
    # Create a bare object to act as the provider instance
    provider = types.SimpleNamespace()
    # Attach the method function so we can call the class method with this instance
    provider.get_diff_files = CodeCommitProvider.get_diff_files.__get__(provider, CodeCommitProvider)
    return provider


def test_get_diff_files_returns_cached_when_present():
    provider = make_provider()
    # set diff_files to a truthy value to trigger early return
    provider.diff_files = ["cached"]
    # Ensure that get_files isn't present and won't be called
    # Call the method and verify it returns the cached list
    result = CodeCommitProvider.get_diff_files(provider)
    assert result == ["cached"]


def test_get_diff_files_handles_all_branches(monkeypatch):
    provider = make_provider()
    # Start with no cached diffs
    provider.diff_files = []

    # Prepare diff items to cover branches:
    # 1) a_blob_id present and b_blob_id present, both returned as bytes -> decoding branch exercised
    # 2) a_blob_id None, b_blob_id present with str -> original empty, new kept as str
    # 3) a_blob_id present returns bytes, b_blob_id None -> new empty
    diff1 = DummyDiffItem("A", "a.py", "B", "b.py", "M")
    diff2 = DummyDiffItem(None, "c.py", "c.py", "c.py", "A")  # a_path == b_path so old_filename None
    diff3 = DummyDiffItem("A3", "d.py", None, "d.py", "D")

    provider.get_files = lambda: [diff1, diff2, diff3]

    # Fake PR info
    provider.pr = DummyPR(source_commit="srcrev", destination_commit="dstrev")
    provider.repo_name = "myrepo"

    # Create a fake codecommit_client with get_file behavior depending on path & commit
    class FakeClient:
        def get_file(self, repo, path, commit):
            # return bytes for certain paths, str for others, and ensure commit passed is correct
            if path == "a.py":
                assert commit == "dstrev"  # original of diff1 uses destination_commit
                return b"original a"
            if path == "b.py":
                assert commit == "srcrev"  # new of diff1 uses source_commit
                return b"new b"
            if path == "c.py":
                # For diff2, original is '', new should be requested with source_commit
                if commit == "dstrev":
                    return None  # will be treated as non-bytes -> but code checks None then sets '' when a_blob_id is None
                else:
                    assert commit == "srcrev"
                    return "new c"
            if path == "d.py":
                # For diff3, original requested with destination commit
                assert commit == "dstrev"
                return b"original d"
            raise AssertionError("Unexpected get_file call: repo=%s path=%s commit=%s" % (repo, path, commit))

    provider.codecommit_client = FakeClient()

    # Monkeypatch FilePatchInfo to a simple class to avoid dependency on actual implementation
    class FakeFilePatchInfo:
        def __init__(self, original, new, patch, filename, edit_type=None, old_filename=None):
            self.original = original
            self.new = new
            self.patch = patch
            self.filename = filename
            self.edit_type = edit_type
            self.old_filename = old_filename

        def __repr__(self):
            return f"FakeFilePatchInfo({self.filename})"

    monkeypatch.setattr(codecommit_provider, "FilePatchInfo", FakeFilePatchInfo)

    # Track calls to load_large_diff and return a predictable patch string
    load_calls = []

    def fake_load_large_diff(patch_filename, new_content, original_content):
        load_calls.append((patch_filename, new_content, original_content))
        return f"PATCH for {patch_filename}"

    monkeypatch.setattr(codecommit_provider, "load_large_diff", fake_load_large_diff)

    # is_valid_file should return True for b.py and c.py, False for d.py (to test skipping)
    def fake_is_valid_file(filename):
        if filename == "d.py":
            return False
        return True

    monkeypatch.setattr(codecommit_provider, "is_valid_file", fake_is_valid_file)

    # Call the method under test
    result = CodeCommitProvider.get_diff_files(provider)

    # Assertions about load_large_diff being called for each diff item with expected patch_filename
    # For diff1: patch_filename should be b_path ('b.py') because b_blob_id not None and assigned later
    # For diff2: a_blob_id is None so patch_filename becomes b_path ('c.py')
    # For diff3: b_blob_id is None so patch_filename set to a_path ('d.py')
    assert any(call[0] == "b.py" for call in load_calls)
    assert any(call[0] == "c.py" for call in load_calls)
    assert any(call[0] == "d.py" for call in load_calls)

    # result should contain FakeFilePatchInfo objects only for diff1 and diff2 (d.py skipped by is_valid_file)
    assert isinstance(result, list)
    filenames = [fi.filename for fi in result]
    assert "b.py" in filenames
    assert "c.py" in filenames
    assert "d.py" not in filenames

    # Validate decoded content for diff1 (both returned bytes -> decoded to strings)
    fi_b = next(fi for fi in result if fi.filename == "b.py")
    assert fi_b.original == "original a"
    assert fi_b.new == "new b"
    assert fi_b.patch == "PATCH for b.py"
    # old_filename should be a.py because a_path != b_path
    assert fi_b.old_filename == "a.py"
    assert fi_b.edit_type == "M"

    # For diff2 where a_blob_id is None and b_blob_id present (and a_path == b_path),
    # original should be empty string, new should be "new c"
    fi_c = next(fi for fi in result if fi.filename == "c.py")
    assert fi_c.original == ""  # original_file_content_str set to "" when a_blob_id is None
    assert fi_c.new == "new c"
    assert fi_c.old_filename is None  # since a_path == b_path
    assert fi_c.patch == "PATCH for c.py"
