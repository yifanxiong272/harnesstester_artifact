import types
import traceback

import pytest

from pr_agent.git_providers import github_provider as gp
from pr_agent.git_providers.github_provider import EDIT_TYPE


class FakeContext(dict):
    def get(self, key, default=None):
        return dict.get(self, key, default)


class DummyFile:
    def __init__(self, filename, status="modified", patch=None, additions=None, deletions=None):
        self.filename = filename
        self.status = status
        self.patch = patch
        if additions is not None:
            self.additions = additions
        if deletions is not None:
            self.deletions = deletions


class DummyPRPart:
    def __init__(self, sha):
        self.sha = sha


class DummyCompare:
    def __init__(self, merge_sha):
        self.merge_base_commit = types.SimpleNamespace(sha=merge_sha)


class DummyRepo:
    def __init__(self, merge_sha=None, raise_on_compare=False):
        self._merge_sha = merge_sha
        self._raise = raise_on_compare

    def compare(self, base_sha, head_sha):
        if self._raise:
            raise Exception("compare failed")
        return DummyCompare(self._merge_sha)


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, *args, **kwargs):
        # record message and any extra
        try:
            self.infos.append((args, kwargs))
        except Exception:
            self.infos.append((str(args), dict(kwargs)))

    def error(self, *args, **kwargs):
        try:
            self.errors.append((args, kwargs))
        except Exception:
            self.errors.append((str(args), dict(kwargs)))


def make_provider():
    # Create an instance without invoking __init__ network behavior
    prov = object.__new__(gp.GithubProvider)
    # set minimal attributes used by get_diff_files
    prov.repo_obj = None
    prov.pr = types.SimpleNamespace(base=DummyPRPart("base_sha"), head=DummyPRPart("head_sha"))
    prov.incremental = types.SimpleNamespace(is_incremental=False, last_seen_commit_sha="last_seen",)
    prov.unreviewed_files_set = {}
    prov.diff_files = None

    def _get_pr_file_content(file, sha):
        # deterministic content based on filename and sha
        return f"content:{file.filename}@{sha}"

    prov._get_pr_file_content = _get_pr_file_content
    return prov


def test_get_diff_files_uses_context_round_005(monkeypatch):
    """
    If context already contains diff_files the function should return it immediately (early return).
    This covers the inner try/context.get path around lines ~231-236.
    """
    saved_get = gp.context.get
    try:
        # Make context.get return a sentinel list
        monkeypatch.setattr(gp.context, "get", lambda key, default=None: ["ctx-sentinel"])
        prov = make_provider()
        result = prov.get_diff_files()
        assert result == ["ctx-sentinel"]
    finally:
        # restore if necessary
        try:
            monkeypatch.setattr(gp.context, "get", saved_get)
        except Exception:
            pass


def test_get_diff_files_process_files_round_005(monkeypatch):
    """
    Create a provider and fake environment exercising multiple branches in get_diff_files:
    - filter_ignored returning a different list than get_files (triggers the logging path)
    - repo.compare returning a different merge_base_commit.sha (triggers info logging)
    - one file skipped as invalid (appended to invalid_files_names)
    - one file processed normally (loads content via _get_pr_file_content and load_large_diff)
    - one file triggers the 'unknown' edit type branch

    The test asserts the returned structures, recorded logger messages, and that context was updated.
    """
    # Prepare fake context that supports get and item assignment
    fake_context = FakeContext()
    monkeypatch.setattr(gp, "context", fake_context)

    # Replace global logger with our dummy logger to capture calls
    dummy_logger = DummyLogger()

    monkeypatch.setattr(gp, "get_logger", lambda: dummy_logger)

    # Ensure load_large_diff returns a deterministic patch with + and - lines
    monkeypatch.setattr(gp, "load_large_diff", lambda filename, new, orig: "line\n+added line\n-deleted line\n")

    # Make filter_ignored return a different (filtered) list from get_files
    f1 = DummyFile("a.py", status="modified", patch=None)
    f2 = DummyFile("ignored.py", status="modified", patch=None)
    f3 = DummyFile("b.txt", status="removed", patch="-old\n+new\n")
    f4 = DummyFile("weird.ext", status="weird", patch="+x\n-y\n")

    files_original = [f1, f2, f3, f4]
    filtered_files = [f1, f3, f4]

    # monkeypatch filter_ignored to return filtered list (so files_original != files triggers info logging)
    monkeypatch.setattr(gp, "filter_ignored", lambda files: filtered_files)

    # get_files should return the original list
    prov = make_provider()
    prov.get_files = lambda: files_original

    # Repo compare should return a merge_base_commit with different sha to provoke the 'Using merge base commit ...' info log
    prov.repo_obj = DummyRepo(merge_sha="merge_sha")
    prov.pr = types.SimpleNamespace(base=DummyPRPart("base_sha"), head=DummyPRPart("head_sha"))

    # Make is_valid_file return False for b.txt to exercise invalid_files_names path
    def fake_is_valid(filename):
        return not filename.endswith(".txt")

    monkeypatch.setattr(gp, "is_valid_file", fake_is_valid)

    # Ensure MAX_FILES_ALLOWED_FULL small enough to trigger avoid_load logging for second valid file
    monkeypatch.setattr(gp, "MAX_FILES_ALLOWED_FULL", 2)

    # Finally, run
    result = prov.get_diff_files()

    # Validate that the returned list contains FilePatchInfo objects for processed files (skips invalid b.txt)
    assert isinstance(result, list)
    # We expect two processed files: a.py and weird.ext (b.txt was invalid by our fake_is_valid)
    filenames = [fp.filename for fp in result]
    assert "a.py" in filenames
    assert "weird.ext" in filenames
    assert "b.txt" not in filenames

    # Check edit types mapping: a.py (modified) should map to EDIT_TYPE.MODIFIED
    entry_a = next(fp for fp in result if fp.filename == "a.py")
    assert entry_a.edit_type == EDIT_TYPE.MODIFIED

    # weird.ext had an unknown status -> should be mapped to EDIT_TYPE.UNKNOWN
    entry_weird = next(fp for fp in result if fp.filename == "weird.ext")
    assert entry_weird.edit_type == EDIT_TYPE.UNKNOWN

    # The patch we provided has a plus and minus line so counts must be present and > 0
    assert entry_weird.num_plus_lines >= 1
    assert entry_weird.num_minus_lines >= 1

    # The provider should cache the diff into self.diff_files and also write to context
    assert prov.diff_files is result
    assert fake_context.get("diff_files") == result

    # Logger must have recorded that ignore filtering happened and that invalid files were filtered out
    # Look for messages in dummy_logger.infos and dummy_logger.errors
    info_texts = " ".join(str(args) + str(kwargs) for args, kwargs in dummy_logger.infos)
    assert "Filtered out [ignore] files" in info_texts or "Filtered out" in info_texts

    # Also expect at least one call not to produce an exception
    assert isinstance(result, list)
