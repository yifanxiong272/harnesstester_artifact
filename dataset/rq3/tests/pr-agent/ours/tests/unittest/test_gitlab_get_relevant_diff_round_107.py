import types
import pytest

from pr_agent.git_providers.gitlab_provider import GitLabProvider


class FakeLogger:
    def __init__(self):
        self.errors = []
        self.debugs = []

    def error(self, msg):
        self.errors.append(msg)

    def debug(self, msg):
        self.debugs.append(msg)


class FakeDiffs:
    def __init__(self, diffs):
        self._diffs = diffs

    def list(self, get_all=False):
        # match signature used in code under test
        return self._diffs


class FakeMR:
    def __init__(self, changes_return, diffs_return):
        # changes_return can be any mapping-like object
        self._changes_return = changes_return
        self.diffs = FakeDiffs(diffs_return)

    def changes(self):
        return self._changes_return


class FakeChangesMapping:
    """
    A mapping-like object that accepts ['changes'] assignment via __setitem__ and
    get(), but reports __len__ == 0 so bool(instance) is False even after assignment.
    This allows exercising the `if not changes:` branch in the code under test.
    """

    def __init__(self, initial=None):
        self._store = {} if initial is None else dict(initial)

    def get(self, k, default=None):
        return self._store.get(k, default)

    def __setitem__(self, k, v):
        # intentionally do not update _store so that __len__ stays zero
        # this simulates a mapping that remains falsy even after assignment
        return None

    def __len__(self):
        # always zero to produce falsy mapping
        return 0


def make_provider_with(monkeypatch, mr):
    # Create a GitLabProvider instance without calling __init__ and set attributes
    provider = GitLabProvider.__new__(GitLabProvider)
    provider.mr = mr
    # make _expand_submodule_changes identity by default (can be overridden in tests)
    provider._expand_submodule_changes = lambda changes: changes
    # default last_diff
    provider.last_diff = {"id": "last-diff"}
    # Ensure tests patch the module-level logger via monkeypatch where code resolves it
    fake_logger = FakeLogger()
    monkeypatch.setattr(
        "pr_agent.git_providers.gitlab_provider.get_logger",
        lambda: fake_logger,
    )
    return provider, fake_logger


def test_no_changes_round_107(monkeypatch):
    """
    Simulate mr.changes() returning a mapping-like object that remains falsy
    even after assignment, exercising the 'No changes found' branch (lines ~642-644).
    """
    fake_changes = FakeChangesMapping()
    mr = FakeMR(changes_return=fake_changes, diffs_return=[{"id": "d1"}])
    provider, fake_logger = make_provider_with(monkeypatch, mr)

    result = GitLabProvider.get_relevant_diff(provider, "some/file.py", "line content")

    assert result is None
    # Ensure the logger recorded the expected error message
    assert any("No changes found for the merge request." in e for e in fake_logger.errors)


def test_no_diffs_round_107(monkeypatch):
    """
    Provide a normal changes dict so the code proceeds to reading diffs,
    but make diffs.list return an empty list to trigger the 'No diffs found'
    branch (lines ~646-648).
    """
    changes = {"changes": [{"new_path": "a.py", "diff": "some diff"}]}
    mr = FakeMR(changes_return=changes, diffs_return=[])
    provider, fake_logger = make_provider_with(monkeypatch, mr)

    result = GitLabProvider.get_relevant_diff(provider, "a.py", "some diff")

    assert result is None
    assert any("No diffs found for the merge request." in e for e in fake_logger.errors)


def test_find_relevant_diff_round_107(monkeypatch):
    """
    Provide changes that include a matching change (new_path matches and the
    relevant line text is contained in change['diff']). The function should
    return the first diff that matches.
    """
    changes = {
        "changes": [
            {"new_path": "file1.py", "diff": "line_a\nrelevant line\nline_b"},
            {"new_path": "file2.py", "diff": "other"},
        ]
    }
    # Prepare diffs: order matters; expect the matching diff to be returned
    diffs = [
        {"id": "diff-1", "content": "not used"},
        {"id": "diff-2", "content": "also not used"},
    ]

    mr = FakeMR(changes_return=changes, diffs_return=diffs)
    provider, fake_logger = make_provider_with(monkeypatch, mr)

    # No special expansion required
    provider._expand_submodule_changes = lambda c: c

    returned = GitLabProvider.get_relevant_diff(provider, "file1.py", "relevant line")

    # The implementation returns the first diff from all_diffs when a change matches
    assert returned == diffs[0]
    # no error messages expected
    assert not fake_logger.errors


def test_fallback_last_diff_round_107(monkeypatch):
    """
    Provide changes and diffs such that none of the diffs are considered
    relevant to the given file/line; expect the function to log a debug
    message and return self.last_diff as fallback (line ~655).
    """
    changes = {"changes": [{"new_path": "unrelated.py", "diff": "no match here"}]}
    # Two diffs, none will match the change
    diffs = [
        {"id": "d1"},
        {"id": "d2"},
    ]
    mr = FakeMR(changes_return=changes, diffs_return=diffs)
    provider, fake_logger = make_provider_with(monkeypatch, mr)

    # Set a distinct last_diff to assert fallback
    provider.last_diff = {"id": "FALLBACK"}

    returned = GitLabProvider.get_relevant_diff(provider, "some_other.py", "some text")

    # When no relevant diff found, the function should fall back to last_diff
    assert returned == {"id": "FALLBACK"}
    # The debug message should have been recorded at least once
    assert any("No relevant diff found for" in d for d in fake_logger.debugs)
