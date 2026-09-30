# file: pr_agent/git_providers/gitlab_provider.py:638-655
# asked: {"lines": [639, 640, 641, 642, 643, 644, 645, 646, 647, 648, 649, 650, 651, 652, 653, 654, 655], "branches": [[642, 643], [642, 645], [646, 647], [646, 649], [649, 650], [649, 655], [650, 651], [650, 653], [651, 650], [651, 652]]}
# gained: {"lines": [639, 640, 641, 642, 645, 646, 649, 650, 651, 652, 653, 654, 655], "branches": [[642, 645], [646, 649], [649, 650], [649, 655], [650, 651], [650, 653], [651, 650], [651, 652]]}

import pytest

from pr_agent.git_providers.gitlab_provider import GitLabProvider


class DummyMR:
    def __init__(self, changes_return, diffs_return):
        self._changes_return = changes_return
        self._diffs_return = diffs_return

    def changes(self):
        return self._changes_return

    class _Diffs:
        def __init__(self, diffs_return):
            self._diffs_return = diffs_return

        def list(self, get_all=True):
            # emulate GitLab list(get_all=True)
            return self._diffs_return

    @property
    def diffs(self):
        return DummyMR._Diffs(self._diffs_return)


def _make_provider(monkeypatch, changes_return, diffs_return):
    # Bypass original __init__ to avoid external config and authentication
    monkeypatch.setattr(GitLabProvider, "__init__", lambda self, merge_request_url=None, incremental=False: None)
    provider = GitLabProvider()
    # attach minimal attributes used by get_relevant_diff
    provider.mr = DummyMR(changes_return, diffs_return)
    # default expand function returns same list but we can track calls
    called = {"count": 0}

    def _expand_submodule_changes(changes):
        called["count"] += 1
        return changes

    provider._expand_submodule_changes = _expand_submodule_changes
    provider.last_diff = {"id": "LAST_DIFF"}
    return provider, called


def test_get_relevant_diff_returns_matching_diff(monkeypatch):
    # Setup: changes contain a change matching relevant_file and relevant_line_in_file
    changes_return = {"changes": [{"new_path": "a.txt", "diff": "line-1\ntarget_line\nline-3"}]}
    diffs_return = [{"id": "diff1"}, {"id": "diff2"}]

    provider, called = _make_provider(monkeypatch, changes_return, diffs_return)

    # Call with matching file and line substring
    res = provider.get_relevant_diff("a.txt", "target_line")

    # Assert expand_submodule_changes was called and returned the first diff (per implementation)
    assert called["count"] == 1
    assert res == diffs_return[0]


def test_get_relevant_diff_falls_back_to_last_diff_when_no_match(monkeypatch):
    # Setup: changes do not match the relevant file/line; diffs list non-empty
    changes_return = {"changes": [{"new_path": "other.txt", "diff": "no match here"}]}
    diffs_return = [{"id": "d1"}, {"id": "d2"}]

    provider, called = _make_provider(monkeypatch, changes_return, diffs_return)

    # Ensure last_diff is distinct and will be used as fallback
    provider.last_diff = {"id": "FALLBACK_LAST_DIFF"}

    res = provider.get_relevant_diff("a.txt", "target_line_not_present")

    # expand_submodule_changes called once
    assert called["count"] == 1
    # Since no matching change was found across diffs, should return last_diff
    assert res == {"id": "FALLBACK_LAST_DIFF"}
