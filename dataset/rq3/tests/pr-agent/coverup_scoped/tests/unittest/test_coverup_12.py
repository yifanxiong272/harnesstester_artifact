# file: pr_agent/git_providers/gitlab_provider.py:234-287
# asked: {"lines": [239, 240, 241, 242, 243, 245, 246, 247, 249, 250, 251, 252, 253, 256, 257, 258, 259, 260, 262, 263, 264, 265, 266, 268, 269, 270, 271, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 287], "branches": [[240, 241], [240, 245], [246, 247], [246, 249], [250, 251], [250, 287], [252, 253], [252, 256], [258, 259], [258, 260], [264, 265], [264, 268], [269, 270], [269, 273], [275, 250], [275, 276]]}
# gained: {"lines": [239, 240, 241, 242, 243, 245, 246, 247, 249, 250, 251, 252, 256, 257, 258, 260, 262, 263, 264, 265, 266, 268, 269, 270, 271, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 287], "branches": [[240, 241], [240, 245], [246, 247], [246, 249], [250, 251], [250, 287], [252, 256], [258, 260], [264, 265], [264, 268], [269, 270], [269, 273], [275, 250], [275, 276]]}

import types
import pytest

from types import SimpleNamespace

import pr_agent.git_providers.gitlab_provider as glmod
from pr_agent.git_providers.gitlab_provider import GitLabProvider


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, msg):
        self.infos.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)


def make_provider(monkeypatch, initial_settings=None):
    """
    Helper to create a GitLabProvider instance with controlled environment.
    Returns (provider, logger)
    """
    # default minimal settings required by __init__
    base_settings = {
        "GITLAB.URL": "https://gitlab.example",
        "GITLAB.PERSONAL_ACCESS_TOKEN": "token",
        "GITLAB.AUTH_TYPE": "oauth_token",
        "GITLAB.SSL_VERIFY": True,
    }
    if initial_settings:
        base_settings.update(initial_settings)

    # Prevent _set_merge_request from running during __init__
    monkeypatch.setattr(glmod.GitLabProvider, "_set_merge_request", lambda self, x: None)

    # monkeypatch gitlab.Gitlab to a dummy constructor
    monkeypatch.setattr(glmod, "gitlab", SimpleNamespace(Gitlab=lambda **kwargs: object()))
    # monkeypatch get_settings to return base_settings for instantiation
    monkeypatch.setattr(glmod, "get_settings", lambda: base_settings)

    # simple logger capture
    logger = DummyLogger()
    monkeypatch.setattr(glmod, "get_logger", lambda: logger)

    provider = GitLabProvider()  # instantiate with safe dummy gitlab
    return provider, logger


def test_expand_submodule_changes_settings_raises(monkeypatch):
    # Create provider with normal settings but we will make get_settings raise later
    provider, _ = make_provider(monkeypatch)

    # Now monkeypatch get_settings to raise when called during method execution
    def bad_get_settings():
        raise RuntimeError("boom")

    monkeypatch.setattr(glmod, "get_settings", bad_get_settings)

    changes = [{"foo": "bar"}]
    out = provider._expand_submodule_changes(changes)
    # Should soft-fail and return original unchanged object (or equal list)
    assert out == changes


def test_expand_submodule_changes_disabled_flag_returns(monkeypatch):
    provider, _ = make_provider(monkeypatch)

    # get_settings returns a dict with flag disabled
    monkeypatch.setattr(glmod, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": False})
    changes = [{"a": 1}]
    out = provider._expand_submodule_changes(changes)
    assert out == changes


def test_expand_submodule_changes_no_gitmodules(monkeypatch):
    provider, _ = make_provider(monkeypatch)
    # enable flag
    monkeypatch.setattr(glmod, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": True})
    # ensure _get_gitmodules_map returns empty
    monkeypatch.setattr(provider, "_get_gitmodules_map", lambda: {})
    changes = [{"a": 1}]
    out = provider._expand_submodule_changes(changes)
    assert out == changes


def test_expand_submodule_changes_submodule_no_url(monkeypatch):
    provider, logger = make_provider(monkeypatch)
    monkeypatch.setattr(glmod, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": True})

    # gitmodules map does not include the sub path
    monkeypatch.setattr(provider, "_get_gitmodules_map", lambda: {"other": "https://example.git"})
    # create change containing a Subproject commit diff and new_path 'submod'
    changes = [{
        "new_path": "submod",
        "diff": "-Subproject commit abcdef1\n+Subproject commit 1234567\n"
    }]
    out = provider._expand_submodule_changes(changes)
    # no expansion, should be same length
    assert out == changes
    # a warning about missing url should have been emitted
    assert any("no url" in w for w in logger.warnings)


def test_expand_submodule_changes_url_parse_failure(monkeypatch):
    provider, logger = make_provider(monkeypatch)
    monkeypatch.setattr(glmod, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": True})

    # gitmodules map includes the sub path
    monkeypatch.setattr(provider, "_get_gitmodules_map", lambda: {"submod": "git@invalid:repo.git"})
    # url parsing returns None to simulate failure
    monkeypatch.setattr(provider, "_url_to_project_path", lambda url: None)

    changes = [{
        "new_path": "submod",
        "diff": "-Subproject commit abcdef1\n+Subproject commit 1234567\n"
    }]
    out = provider._expand_submodule_changes(changes)
    assert out == changes
    # should have warning about cannot parse project path
    assert any("cannot parse project path" in w for w in logger.warnings)


def test_expand_submodule_changes_successful_expansion(monkeypatch):
    provider, logger = make_provider(monkeypatch)
    monkeypatch.setattr(glmod, "get_settings", lambda: {"GITLAB.EXPAND_SUBMODULE_DIFFS": True})

    # gitmodules map includes the sub path
    monkeypatch.setattr(provider, "_get_gitmodules_map", lambda: {"submod": "https://gitlab.example/group/proj.git"})
    # url parsing returns a project path
    monkeypatch.setattr(provider, "_url_to_project_path", lambda url: "group/proj")
    # _compare_submodule returns diffs; include various key combos
    def fake_compare(proj_path, old_sha, new_sha):
        # one entry with explicit old/new paths and flags
        entry1 = {
            "a_path": "file1.txt",
            "b_path": "file1.txt",
            "diff": "some diff",
            "new_file": True,
            "deleted_file": False,
            "renamed_file": False
        }
        # another entry missing a_path/b_path to exercise defaults
        entry2 = {
            "diff": "other diff",
            "new_file": False,
            "deleted_file": True,
            "renamed_file": True
        }
        return [entry1, entry2]

    monkeypatch.setattr(provider, "_compare_submodule", fake_compare)

    changes = [{
        "new_path": "submod",
        "diff": "-Subproject commit abcdef1\n+Subproject commit 1234567\n",
        "old_path": None
    }]
    out = provider._expand_submodule_changes(changes)
    # original change should be present
    assert any(ch.get("diff") == changes[0]["diff"] for ch in out)
    # two appended diffs should have been added
    # total length should be original + 2
    assert len(out) == 1 + 2
    # check that appended entries have proper path prefixes
    appended = out[1:]
    assert appended[0]["old_path"].startswith("submod/")
    assert appended[0]["new_path"].startswith("submod/")
    assert appended[0]["diff"] == "some diff"
    # second appended used submod as path when no sd_old present
    assert appended[1]["old_path"] == "submod"
    assert appended[1]["new_path"] == "submod"
    # flags carried over
    assert appended[0]["new_file"] is True
    assert appended[1]["deleted_file"] is True
    assert appended[1]["renamed_file"] is True
    # info log entry about mapping should have been emitted
    assert any("url=" in i for i in logger.infos)
