# file: pr_agent/git_providers/codecommit_provider.py:103-157
# asked: {"lines": [113, 114, 116, 118, 119, 120, 121, 122, 123, 124, 125, 126, 128, 130, 131, 132, 133, 134, 136, 138, 141, 142, 143, 144, 145, 146, 147, 148, 149, 154, 155, 157], "branches": [[113, 114], [113, 116], [119, 120], [119, 157], [121, 122], [121, 128], [125, 126], [125, 130], [130, 131], [130, 136], [133, 134], [133, 138], [154, 119], [154, 155]]}
# gained: {"lines": [113, 114, 116, 118, 119, 120, 121, 122, 123, 124, 125, 126, 128, 130, 131, 132, 133, 134, 136, 138, 141, 142, 143, 144, 145, 146, 148, 149, 154, 155, 157], "branches": [[113, 114], [113, 116], [119, 120], [119, 157], [121, 122], [121, 128], [125, 126], [130, 131], [130, 136], [133, 134], [133, 138], [154, 119], [154, 155]]}

import pytest
from types import SimpleNamespace

import pr_agent.git_providers.codecommit_provider as cc_module
from pr_agent.git_providers.codecommit_provider import CodeCommitProvider


class FakeDiffItem:
    def __init__(self, a_blob_id, a_path, b_blob_id, b_path, edit_type):
        self.a_blob_id = a_blob_id
        self.a_path = a_path
        self.b_blob_id = b_blob_id
        self.b_path = b_path
        self.edit_type = edit_type


def make_provider():
    p = CodeCommitProvider()
    p.repo_name = "repo"
    p.pr = SimpleNamespace(destination_commit="dest_commit", source_commit="src_commit")
    p.codecommit_client = SimpleNamespace()
    return p


def test_get_diff_files_returns_cached_and_does_not_call_get_files(monkeypatch):
    p = make_provider()
    called = {"get_files": False}

    def fake_get_files():
        called["get_files"] = True
        return []

    p.diff_files = ["cached"]
    # monkeypatch the instance method
    monkeypatch.setattr(p, "get_files", fake_get_files)

    res = p.get_diff_files()
    assert res == ["cached"]
    assert called["get_files"] is False


def test_get_diff_files_full_flow(monkeypatch):
    p = make_provider()

    diff1 = FakeDiffItem(a_blob_id="a1", a_path="old1.txt", b_blob_id="b1", b_path="new1.txt", edit_type="M")
    diff2 = FakeDiffItem(a_blob_id=None, a_path=None, b_blob_id="b2", b_path="new2.txt", edit_type="A")
    diff3 = FakeDiffItem(a_blob_id="a3", a_path="old3.txt", b_blob_id=None, b_path="bad.txt", edit_type="D")
    files = [diff1, diff2, diff3]

    monkeypatch.setattr(p, "get_files", lambda: files)

    def fake_get_file(repo, path, commit):
        if path == "old1.txt" and commit == p.pr.destination_commit:
            return b"orig1_bytes"
        if path == "new1.txt" and commit == p.pr.source_commit:
            return bytearray(b"new1_bytearray")
        if path == "new2.txt" and commit == p.pr.source_commit:
            return "new2_str"
        if path == "old3.txt" and commit == p.pr.destination_commit:
            return b"orig3_bytes"
        return None

    p.codecommit_client.get_file = fake_get_file

    captured = {"calls": []}

    def fake_load_large_diff(patch_filename, new_content, original_content):
        captured["calls"].append((patch_filename, new_content, original_content))
        new_len = len(new_content) if new_content is not None else -1
        orig_len = len(original_content) if original_content is not None else -1
        return f"PATCH:{patch_filename}:{new_len}:{orig_len}"

    monkeypatch.setattr(cc_module, "load_large_diff", fake_load_large_diff)

    def fake_is_valid_file(filename):
        if filename is None:
            return False
        return filename != "bad.txt"

    monkeypatch.setattr(cc_module, "is_valid_file", fake_is_valid_file)

    p.diff_files = None

    res = p.get_diff_files()

    assert isinstance(res, list)
    # diff1 and diff2 pass is_valid_file, diff3 filtered out
    assert len(res) == 2

    info1 = res[0]
    assert info1.filename == "new1.txt"
    # dataclass fields: base_file (original), head_file (new)
    assert info1.base_file == "orig1_bytes"
    assert info1.head_file == "new1_bytearray"
    assert info1.patch.startswith("PATCH:new1.txt:")
    assert info1.edit_type == "M"
    assert info1.old_filename == "old1.txt"

    info2 = res[1]
    assert info2.filename == "new2.txt"
    assert info2.base_file == ""  # original missing -> empty string
    assert info2.head_file == "new2_str"
    assert info2.edit_type == "A"
    assert info2.old_filename is None

    # load_large_diff should be called for all three diff items (including filtered one)
    assert len(captured["calls"]) == 3
    call0 = captured["calls"][0]
    assert call0[0] == "new1.txt"
    assert call0[1] == "new1_bytearray"
    assert call0[2] == "orig1_bytes"

    # provider cached result
    assert p.diff_files is res
