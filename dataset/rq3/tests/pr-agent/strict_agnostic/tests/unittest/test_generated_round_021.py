import types
import pytest

from pr_agent.git_providers import gitlab_provider as gl_mod
from pr_agent.git_providers.gitlab_provider import (
    GitLabProvider,
    FilePatchInfo,
    EDIT_TYPE,
)


def make_provider_without_init():
    # create instance without calling __init__ to avoid side-effects
    prov = object.__new__(GitLabProvider)
    # default attributes that get_diff_files expects
    prov.diff_files = None
    prov.id_mr = 123
    return prov


def test_returns_cached_diff_files_round_021():
    # Ensure early return when diff_files already set (covers lines ~405-406)
    provider = make_provider_without_init()
    cached = [
        FilePatchInfo("orig", "new", patch="p", filename="f.py", edit_type=EDIT_TYPE.MODIFIED, old_filename=None, num_plus_lines=0, num_minus_lines=0)
    ]
    provider.diff_files = cached

    ret = GitLabProvider.get_diff_files(provider)
    assert ret is cached
    assert isinstance(ret[0], FilePatchInfo)


def test_complex_diff_handling_round_021(monkeypatch):
    # This test exercises filtering, invalid-file filtering, MAX_FILES_ALLOWED_FULL behavior,
    # loading full content vs skipping it, using load_large_diff when patch is empty,
    # edit_type determination for added/deleted/renamed, and plus/minus counting.

    provider = make_provider_without_init()

    # Prepare raw changes (diffs_original)
    diffs_original = [
        # invalid file (should be filtered out by is_valid_file)
        {"new_path": "ignored.txt", "old_path": "ignored.txt", "diff": "", "new_file": False, "deleted_file": False, "renamed_file": False},
        # a.py: empty diff -> will cause get_pr_file_content to be used and then load_large_diff
        {"new_path": "a.py", "old_path": "a.py", "diff": "", "new_file": False, "deleted_file": False, "renamed_file": False},
        # b.py: has diff provided and is an added file
        {"new_path": "b.py", "old_path": "b.py", "diff": "+b1\n+b2\n-b3\n", "new_file": True, "deleted_file": False, "renamed_file": False},
        # c.py: empty diff and renamed (old_path different)
        {"new_path": "c.py", "old_path": "oldc.py", "diff": "", "new_file": False, "deleted_file": False, "renamed_file": True},
    ]

    class DummyMR:
        def __init__(self, changes):
            self._changes = changes
            self.diff_refs = {"base_sha": "base", "head_sha": "head"}

        def changes(self):
            return {"changes": self._changes}

    mr = DummyMR(diffs_original)
    provider.mr = mr

    # Monkeypatch helpers in the module under test
    # 1) _expand_submodule_changes should return the input as-is
    monkeypatch.setattr(gl_mod.GitLabProvider, "_expand_submodule_changes", lambda self, changes: changes)

    # 2) filter_ignored should remove the ignored.txt entry to trigger the `diffs != diffs_original` logging branch
    def fake_filter_ignored(diffs, source):
        return [d for d in diffs if not d["new_path"].endswith(".txt")]

    monkeypatch.setattr(gl_mod, "filter_ignored", fake_filter_ignored)

    # 3) is_valid_file -> mark .txt invalid, others valid
    monkeypatch.setattr(gl_mod, "is_valid_file", lambda p: not p.endswith('.txt'))

    # 4) decode_if_bytes: if bytes, decode; otherwise return unchanged
    monkeypatch.setattr(gl_mod, "decode_if_bytes", lambda x: x.decode('utf-8') if isinstance(x, (bytes, bytearray)) else x)

    # 5) load_large_diff: return a small synthetic patch for files where patch is empty
    def fake_load_large_diff(filename, new_content, original_content):
        if filename == "a.py":
            return "+line_a\n-line_a_old\n"
        if filename == "c.py":
            return "+line_c\n"
        return ""

    monkeypatch.setattr(gl_mod, "load_large_diff", fake_load_large_diff)

    # 6) Control MAX_FILES_ALLOWED_FULL to exercise the logging branch when reaching the limit
    monkeypatch.setattr(gl_mod, "MAX_FILES_ALLOWED_FULL", 2)

    # 7) get_pr_file_content: return bytes for a.py to test decode_if_bytes path; for b.py will not be used (since it's considered added and has diff), for c.py after threshold the code will set empty strings (so this won't be called)
    def fake_get_pr_file_content(path, sha):
        if path == "a.py":
            return b"old a\n"
        if path == "b.py":
            return b"new b\n"
        if path == "oldc.py":
            return b"old c\n"
        return b""

    # Assign the function as an attribute on the instance (callable signature matches use in method)
    provider.get_pr_file_content = fake_get_pr_file_content

    # Ensure no prior diff cache
    provider.diff_files = None

    # Execute
    result = GitLabProvider.get_diff_files(provider)

    # Assertions (observable behaviors):
    # - ignored.txt should be filtered out entirely
    filenames = [fp.filename for fp in result]
    assert "ignored.txt" not in filenames

    # - we expect three processed files (a.py, b.py, c.py)
    assert set(filenames) == {"a.py", "b.py", "c.py"}

    # Find entries by filename for detailed checks
    by_name = {fp.filename: fp for fp in result}

    # a.py: came from empty diff -> load_large_diff provided +/-, so counts should match
    fa = by_name["a.py"]
    assert fa.num_plus_lines == 1
    assert fa.num_minus_lines == 1
    assert fa.edit_type == EDIT_TYPE.MODIFIED

    # b.py: had diff string with two plus, one minus; also marked as new_file -> ADDED
    fb = by_name["b.py"]
    assert fb.num_plus_lines == 2
    assert fb.num_minus_lines == 1
    assert fb.edit_type == EDIT_TYPE.ADDED

    # c.py: renamed_file True, old_filename should be set and considered RENAMED
    fc = by_name["c.py"]
    assert fc.edit_type == EDIT_TYPE.RENAMED
    assert fc.old_filename == "oldc.py"
    assert fc.num_plus_lines == 1
    assert fc.num_minus_lines == 0

    # Finally, provider.diff_files was set and subsequent calls should return the same list
    second_call = GitLabProvider.get_diff_files(provider)
    assert second_call is provider.diff_files
