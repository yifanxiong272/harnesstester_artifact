import types
import re
import pytest

from pr_agent.git_providers import gitlab_provider as glp
from pr_agent.git_providers.gitlab_provider import GitLabProvider


class LoggerMock:
    def __init__(self):
        self.warnings = []
        self.infos = []

    def warning(self, msg):
        self.warnings.append(msg)

    def info(self, msg):
        self.infos.append(msg)


def bind_expand_to(obj):
    """Bind the class method to a simple namespace instance for testing."""
    return GitLabProvider._expand_submodule_changes.__get__(obj, GitLabProvider)


def make_dummy_self():
    return types.SimpleNamespace()


def test_returns_changes_when_settings_disabled_round_035(monkeypatch):
    monkeypatch.setattr(glp, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": False})

    dummy = make_dummy_self()
    # method will not call any other helpers because it returns early
    method = bind_expand_to(dummy)

    changes = [{"some": "change"}]
    out = method(changes)
    assert out is changes or out == changes


def test_returns_changes_when_get_settings_raises_round_035(monkeypatch):
    def raising_settings():
        raise RuntimeError("boom")

    monkeypatch.setattr(glp, "get_settings", raising_settings)

    dummy = make_dummy_self()
    method = bind_expand_to(dummy)

    changes = [{"x": "y"}]
    out = method(changes)
    assert out == changes


def test_returns_changes_when_no_gitmodules_round_035(monkeypatch):
    monkeypatch.setattr(glp, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": True})

    dummy = make_dummy_self()
    dummy._get_gitmodules_map = lambda: {}  # falsy -> should return early
    method = bind_expand_to(dummy)

    changes = [{"a": 1}]
    out = method(changes)
    assert out == changes


def test_skip_when_patch_has_no_subproject_text_round_035(monkeypatch):
    monkeypatch.setattr(glp, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": True})
    monkeypatch.setattr(glp, "get_logger", lambda: LoggerMock())

    dummy = make_dummy_self()
    # gitmodules present but patch won't contain 'Subproject commit'
    dummy._get_gitmodules_map = lambda: {"sub/path": "git@example.com:group/repo.git"}
    dummy._url_to_project_path = lambda url: "group/repo"
    dummy._compare_submodule = lambda proj, o, n: []

    method = bind_expand_to(dummy)

    changes = [{"new_path": "sub/path", "diff": "some other diff"}]
    out = method(changes)
    assert out == changes


def test_skip_when_old_new_regex_missing_round_035(monkeypatch):
    monkeypatch.setattr(glp, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": True})
    monkeypatch.setattr(glp, "get_logger", lambda: LoggerMock())

    dummy = make_dummy_self()
    dummy._get_gitmodules_map = lambda: {"sub": "git@example.com:group/repo.git"}
    dummy._url_to_project_path = lambda url: "group/repo"
    dummy._compare_submodule = lambda proj, o, n: []

    method = bind_expand_to(dummy)

    # include the phrase but not the -/+ form required by the regex
    patch = " Subproject commit abcdef1\n Subproject commit 1234567"
    changes = [{"new_path": "sub", "diff": patch}]
    out = method(changes)
    assert out == changes


def test_warns_and_skips_when_repo_url_missing_round_035(monkeypatch):
    monkeypatch.setattr(glp, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": True})
    logger = LoggerMock()
    monkeypatch.setattr(glp, "get_logger", lambda: logger)

    dummy = make_dummy_self()
    # gitmodules map does not contain the sub path -> triggers warning
    dummy._get_gitmodules_map = lambda: {"other": "git@example.com:group/repo.git"}
    dummy._url_to_project_path = lambda url: "group/repo"
    dummy._compare_submodule = lambda proj, o, n: []

    method = bind_expand_to(dummy)

    patch = "-Subproject commit 1234567\n+Subproject commit abcdef0\n"
    changes = [{"new_path": "sub/path", "diff": patch}]
    out = method(changes)

    # unchanged
    assert out == changes
    # ensure the logger got a warning mentioning .gitmodules skip
    assert any("no url" in w or "no url for" in w for w in logger.warnings)


def test_warns_and_skips_when_unparsable_proj_path_round_035(monkeypatch):
    monkeypatch.setattr(glp, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": True})
    logger = LoggerMock()
    monkeypatch.setattr(glp, "get_logger", lambda: logger)

    dummy = make_dummy_self()
    dummy._get_gitmodules_map = lambda: {"sub": "git@example.com:group/repo.git"}
    # simulate failure to parse a project path
    dummy._url_to_project_path = lambda url: ""  # falsy -> warn and continue
    dummy._compare_submodule = lambda proj, o, n: []

    method = bind_expand_to(dummy)

    patch = "-Subproject commit 1234567\n+Subproject commit abcdef0\n"
    changes = [{"new_path": "sub", "diff": patch}]
    out = method(changes)

    assert out == changes
    assert any("cannot parse project path" in w or "cannot parse" in w for w in logger.warnings)


def test_expands_submodule_with_sub_diffs_round_035(monkeypatch):
    # Full happy path where sub_diffs are appended
    monkeypatch.setattr(glp, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": True})
    logger = LoggerMock()
    monkeypatch.setattr(glp, "get_logger", lambda: logger)

    dummy = make_dummy_self()
    dummy._get_gitmodules_map = lambda: {"libs/foo": "git@example.com:group/foo.git"}
    dummy._url_to_project_path = lambda url: "group/foo"

    # Return two sub diffs exercising different path fallbacks and flags
    sd1 = {
        "diff": "-old\n+new\n",
        "old_path": "a.py",
        "new_path": "a.py",
        "new_file": True,
    }
    sd2 = {
        "diff": "-old2\n+new2\n",
        # simulate a case with only a_path/b_path style keys
        "a_path": "b.txt",
        "b_path": "c.txt",
        "deleted_file": True,
    }

    # ensure compare_submodule gets the parsed proj_path and SHAs we pass
    captured = {}

    def compare_submodule(proj_path, old_sha, new_sha):
        captured['proj_path'] = proj_path
        captured['old_sha'] = old_sha
        captured['new_sha'] = new_sha
        return [sd1, sd2]

    dummy._compare_submodule = compare_submodule

    method = bind_expand_to(dummy)

    # create a patch with the required -/+ Subproject commit lines (7 hex chars)
    old = "1234567"
    new = "abcdef0"
    patch = f"-Subproject commit {old}\n+Subproject commit {new}\n"
    changes = [{"new_path": "libs/foo", "diff": patch}]

    out = method(changes)

    # original change should still exist
    assert any(ch.get("new_path") == "libs/foo" for ch in out)

    # appended items from sub_diffs should be present with paths prefixed by sub path
    appended_old_paths = [item.get("old_path") for item in out if item.get("old_path") != "libs/foo"]
    appended_new_paths = [item.get("new_path") for item in out if item.get("new_path") != "libs/foo"]

    assert "libs/foo/a.py" in appended_old_paths
    assert "libs/foo/a.py" in appended_new_paths
    # for sd2, old comes from a_path and new from b_path
    assert "libs/foo/b.txt" in appended_old_paths
    assert "libs/foo/c.txt" in appended_new_paths

    # flags preserved
    assert any(item.get("new_file") is True for item in out)
    assert any(item.get("deleted_file") is True for item in out)

    # ensure compare_submodule was called with parsed project path and shas
    assert captured['proj_path'] == "group/foo"
    assert captured['old_sha'] == old
    assert captured['new_sha'] == new
