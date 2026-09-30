import pytest

from pr_agent.git_providers.gitlab_provider import GitLabProvider
import pr_agent.git_providers.gitlab_provider as glmod

# We will construct GitLabProvider instances without calling __init__ to avoid
# side effects. We'll monkeypatch functions imported in the module (get_settings)
# and instance helper methods to exercise branching in _expand_submodule_changes.

def _make_provider():
    # create instance without invoking __init__
    return object.__new__(GitLabProvider)


def test_setting_disabled_round_035(monkeypatch):
    # If GITLAB.EXPAND_SUBMODULE_DIFFS is False, function should return the
    # original changes object unchanged (early return path).
    monkeypatch.setattr(glmod, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": False})
    prov = _make_provider()
    changes = [{"a_path": "x", "b_path": "x", "diff": "some diff"}]

    res = GitLabProvider._expand_submodule_changes(prov, changes)
    # Early return should return the same object
    assert res is changes


def test_get_settings_exception_round_035(monkeypatch):
    # If get_settings raises, function should soft-fail and return original changes
    def _raise():
        raise RuntimeError("no settings")
    monkeypatch.setattr(glmod, "get_settings", _raise)
    prov = _make_provider()
    changes = [{"a_path": "x", "b_path": "x", "diff": "irrelevant"}]

    res = GitLabProvider._expand_submodule_changes(prov, changes)
    assert res is changes


def test_no_gitmodules_round_035(monkeypatch):
    # When expand enabled but _get_gitmodules_map returns falsy, return original changes
    monkeypatch.setattr(glmod, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": True})
    prov = _make_provider()
    prov._get_gitmodules_map = lambda: {}
    changes = [{"a_path": "x", "b_path": "x", "diff": "irrelevant"}]

    res = GitLabProvider._expand_submodule_changes(prov, changes)
    # Code returns the same changes object when no gitmodules
    assert res is changes


def test_change_without_subproject_round_035(monkeypatch):
    # If the patch does not contain 'Subproject commit', changes should be copied but not expanded
    monkeypatch.setattr(glmod, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": True})
    prov = _make_provider()
    prov._get_gitmodules_map = lambda: {"sub/path": "git@example:repo.git"}
    changes = [{"old_path": "sub/path/file.txt", "new_path": "sub/path/file.txt", "diff": "@@ -1 +1 @@\n-foo\n+bar\n"}]

    res = GitLabProvider._expand_submodule_changes(prov, changes)
    # Should return a new list equal to original (no expansion)
    assert res == list(changes)
    assert res is not changes


def test_missing_old_new_sha_round_035(monkeypatch):
    # If patch contains 'Subproject commit' but regex can't find both old and new SHAs, skip expansion
    monkeypatch.setattr(glmod, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": True})
    prov = _make_provider()
    prov._get_gitmodules_map = lambda: {"sub": "git@example:repo.git"}
    # include the phrase but not proper -/+ SHA lines
    changes = [{"new_path": "sub", "diff": "-Subproject commit abcdef\n some other line\n"}]

    res = GitLabProvider._expand_submodule_changes(prov, changes)
    # No sub-diffs found due to missing both old and new regex matches
    assert res == list(changes)


def test_missing_repo_url_round_035(monkeypatch):
    # If the gitmodules mapping has no url for the sub_path, warn and skip
    monkeypatch.setattr(glmod, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": True})
    prov = _make_provider()
    # gitmodules does not contain the expected sub path
    prov._get_gitmodules_map = lambda: {"other/path": "git@example:repo.git"}
    # provide both old and new sha lines and a sub path that won't be found in gitmodules
    diff = "-Subproject commit 0123456789abcdef\n+Subproject commit fedcba9876543210\n"
    changes = [{"new_path": "missing/path", "diff": diff}]

    res = GitLabProvider._expand_submodule_changes(prov, changes)
    assert res == list(changes)


def test_missing_proj_path_round_035(monkeypatch):
    # If repo_url cannot be parsed into proj_path, skip expansion
    monkeypatch.setattr(glmod, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": True})
    prov = _make_provider()
    prov._get_gitmodules_map = lambda: {"sub": "git@example:repo.git"}
    # make _url_to_project_path return falsy
    prov._url_to_project_path = lambda url: ""
    diff = "-Subproject commit 0123456789abcdef\n+Subproject commit fedcba9876543210\n"
    changes = [{"new_path": "sub", "diff": diff}]

    res = GitLabProvider._expand_submodule_changes(prov, changes)
    assert res == list(changes)


def test_expand_with_subdiffs_round_035(monkeypatch):
    # Full expansion path: valid gitmodules entry, proj_path returned, _compare_submodule returns diffs
    monkeypatch.setattr(glmod, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": True})
    prov = _make_provider()
    prov._get_gitmodules_map = lambda: {"libs/lib1": "git@example:org/lib1.git"}
    prov._url_to_project_path = lambda url: "org/lib1"

    # _compare_submodule should be called with proj_path, old and new sha and return list of file-diffs
    def _cmp(proj_path, old, new):
        # provide two sample sub-diffs exercising old_path/new_path fallback logic
        return [
            {"a_path": "fileA.txt", "b_path": "fileA.txt", "diff": "@@ -1 +1 @@\n-foo\n+bar\n"},
            {"old_path": "fileB_old.txt", "new_path": "fileB_new.txt", "diff": "@@ -1 +1 @@\n-old\n+new\n", "new_file": True}
        ]
    prov._compare_submodule = _cmp

    diff = "-Subproject commit 0000000000000000\n+Subproject commit ffffffffffffffff\n"
    changes = [{"new_path": "libs/lib1", "diff": diff}]

    res = GitLabProvider._expand_submodule_changes(prov, changes)

    # Expect original item still present (copied) plus two appended entries from subdiffs
    assert isinstance(res, list)
    # original present as first element
    assert res[0]["new_path"] == "libs/lib1"
    # Find appended entries by their diff contents
    appended = [r for r in res if r.get("diff") and r.get("diff").startswith("@@")]
    # Should include both sub-diffs
    assert any(r.get("old_path") == "libs/lib1/fileA.txt" for r in appended)
    assert any(r.get("new_file") is True and r.get("old_path") == "libs/lib1/fileB_old.txt" or r.get("old_path") == "libs/lib1/fileB_old.txt" for r in appended)
