# file: sweagent/environment/repo.py:187-209
# asked: {"lines": [197, 198, 199, 200, 201, 202, 203, 204, 205, 207, 208, 209], "branches": [[197, 198], [197, 199], [199, 200], [199, 201], [201, 202], [201, 203], [203, 204], [203, 208], [204, 205], [204, 207]]}
# gained: {"lines": [197, 198, 199, 200, 201, 202, 203, 204, 205, 207, 208, 209], "branches": [[197, 198], [197, 199], [199, 200], [199, 201], [201, 202], [201, 203], [203, 204], [203, 208], [204, 205], [204, 207]]}

import pytest
from pathlib import Path

from sweagent.environment.repo import (
    repo_from_simplified_input,
    LocalRepoConfig,
    GithubRepoConfig,
    PreExistingRepoConfig,
)


def test_repo_from_simplified_input_local():
    cfg = repo_from_simplified_input(input="some/local/path", base_commit="abc123", type="local")
    assert isinstance(cfg, LocalRepoConfig)
    # ensure attributes set as expected
    assert getattr(cfg, "path") == Path("some/local/path")
    assert getattr(cfg, "base_commit") == "abc123"


def test_repo_from_simplified_input_github():
    url = "https://github.com/example/repo"
    cfg = repo_from_simplified_input(input=url, base_commit="def456", type="github")
    assert isinstance(cfg, GithubRepoConfig)
    assert getattr(cfg, "github_url") == url
    assert getattr(cfg, "base_commit") == "def456"


def test_repo_from_simplified_input_preexisting():
    name = "org/repo@main"
    cfg = repo_from_simplified_input(input=name, base_commit="deadbeef", type="preexisting")
    assert isinstance(cfg, PreExistingRepoConfig)
    assert getattr(cfg, "repo_name") == name
    assert getattr(cfg, "base_commit") == "deadbeef"


def test_repo_from_simplified_input_auto_detects_github():
    url = "https://github.com/owner/repo"
    cfg = repo_from_simplified_input(input=url, type="auto")
    assert isinstance(cfg, GithubRepoConfig)
    assert getattr(cfg, "github_url") == url
    # default base_commit should be 'HEAD'
    assert getattr(cfg, "base_commit") == "HEAD"


def test_repo_from_simplified_input_auto_detects_local():
    local = "relative/path/to/repo"
    cfg = repo_from_simplified_input(input=local, type="auto")
    assert isinstance(cfg, LocalRepoConfig)
    assert getattr(cfg, "path") == Path(local)
    assert getattr(cfg, "base_commit") == "HEAD"


def test_repo_from_simplified_input_unknown_type_raises():
    with pytest.raises(ValueError) as exc:
        repo_from_simplified_input(input="irrelevant", type="not-a-type")
    assert "Unknown repo type: not-a-type" in str(exc.value)
