import pytest

from pr_agent.git_providers import bitbucket_provider as bb_mod
from pr_agent.git_providers.bitbucket_provider import BitbucketProvider
from pr_agent.algo.types import EDIT_TYPE, FilePatchInfo


class _Ver:
    def __init__(self, path, links=None):
        self.path = path
        self._links = links or {}

    def get_data(self, key):
        if key == "links":
            return self._links
        raise KeyError


class _Diff:
    def __init__(self, path, status, lines_added=1, lines_removed=0, old_links=None, new_links=None):
        self.new = _Ver(path, links=new_links)
        self.old = _Ver(path, links=old_links)
        self.data = {"status": status, "lines_added": lines_added, "lines_removed": lines_removed}


def _build_diff_patch_for(path, body_lines):
    # build a diff part that contains a header which will be stripped by the provider
    # ensure there are at least 6 lines so the header-detection branch is exercised
    header = "\n".join([
        " ",
        f" a/{path}",
        f"--- a/{path}",
        f"+++ b/{path}",
        "@@ -1 +1 @@",
    ])
    return header + "\n" + "\n".join(body_lines)


def _make_provider_with_pr(pr_obj):
    # Create a BitbucketProvider-like instance without running __init__
    p = object.__new__(BitbucketProvider)
    p.pr = pr_obj
    p.diff_files = None
    return p


def test_get_diff_files_basic_mapping_and_header_stripping_round_003(monkeypatch):
    """
    Exercise normal path where: diffs == diffs_original, headers are detected and stripped,
    files are valid and full contents are loaded via _get_pr_file_content, and edit_type mapping
    for added/removed/modified/renamed is applied.
    """
    # Prepare four diffs with different statuses
    diffs = [
        _Diff("f_added.py", "added", old_links={'self': {'href': 'origA'}}, new_links={'self': {'href': 'newA'}}),
        _Diff("f_removed.py", "removed", old_links={'self': {'href': 'origB'}}, new_links={'self': {'href': 'newB'}}),
        _Diff("f_modified.py", "modified", old_links={'self': {'href': 'origC'}}, new_links={'self': {'href': 'newC'}}),
        _Diff("f_renamed.py", "renamed", old_links={'self': {'href': 'origD'}}, new_links={'self': {'href': 'newD'}}),
    ]

    # pr.diffstat() should return diffs_original
    class PR:
        def diffstat(self):
            return list(diffs)

        def diff(self):
            # craft pr_patches with 4 parts where each has header lines to trigger header stripping
            parts = [
                _build_diff_patch_for(d.new.path, ["+line1", "+line2"]) for d in diffs
            ]
            return "".join(["diff --git" + p for p in parts])

    pr = PR()

    # monkeypatch functions in module to deterministic behaviors
    monkeypatch.setattr(bb_mod, "filter_ignored", lambda x, _src: x)
    monkeypatch.setattr(bb_mod, "get_settings", lambda: {})
    monkeypatch.setattr(bb_mod, "is_valid_file", lambda p: True)

    # make provider instance and ensure _get_pr_file_content returns deterministic content and records calls
    provider = _make_provider_with_pr(pr)
    recorded_calls = []

    def _fake_get_content(url):
        recorded_calls.append(url)
        return f"content-for-{url}"

    provider._get_pr_file_content = _fake_get_content

    files = provider.get_diff_files()

    # We expect one FilePatchInfo per diff, and proper edit_type for each status
    assert isinstance(files, list) and len(files) == 4
    statuses = [f.edit_type for f in files]
    assert statuses[0] == EDIT_TYPE.ADDED
    assert statuses[1] == EDIT_TYPE.DELETED
    assert statuses[2] == EDIT_TYPE.MODIFIED
    assert statuses[3] == EDIT_TYPE.RENAMED

    # Instead of accessing a concrete attribute name for file path (which may differ on FilePatchInfo),
    # assert that the provider tried to fetch expected file contents (both old and new links were provided)
    expected_hrefs = {"origA", "newA", "origB", "newB", "origC", "newC", "origD", "newD"}
    assert set(recorded_calls) == expected_hrefs


def test_get_diff_files_diff_decode_failure_raises_valueerror_round_003(monkeypatch):
    """
    Simulate pr.diff() raising a generic exception and then pr.diff(encoding=...) raising
    UnicodeDecodeError for all encodings: provider should raise ValueError as coded.
    """

    class PR:
        def diffstat(self):
            return []

        def diff(self, encoding=None):
            # When called without encoding the code expects an exception raised
            if encoding is None:
                raise Exception("initial decode fail")
            # When called with an encoding raise UnicodeDecodeError to simulate decode failures
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid")

    pr = PR()
    provider = _make_provider_with_pr(pr)

    # Ensure ignored filtering and settings are deterministic
    monkeypatch.setattr(bb_mod, "filter_ignored", lambda x, _src: x)
    monkeypatch.setattr(bb_mod, "get_settings", lambda: {})

    with pytest.raises(ValueError):
        provider.get_diff_files()


def test_get_diff_files_diff_split_mismatch_returns_empty_round_003(monkeypatch):
    """
    If the number of split diff parts does not match the number of diffs, the function logs
    an error and returns an empty list. This test asserts the empty-list behavior.
    """

    # Create two diffs but produce only one diff part
    diffs = [
        _Diff("a.py", "modified"),
        _Diff("b.py", "modified"),
    ]

    class PR:
        def diffstat(self):
            return list(diffs)

        def diff(self):
            # produce only one diff part even though we have two diffs in stat
            return "diff --git a/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n+line\n"

    pr = PR()
    provider = _make_provider_with_pr(pr)

    monkeypatch.setattr(bb_mod, "filter_ignored", lambda x, _src: x)
    monkeypatch.setattr(bb_mod, "get_settings", lambda: {})
    monkeypatch.setattr(bb_mod, "is_valid_file", lambda p: True)

    result = provider.get_diff_files()
    assert result == []
