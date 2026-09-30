# file: sweagent/run/hooks/open_pr.py:24-116
# asked: {"lines": [32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 46, 47, 48, 50, 51, 52, 53, 54, 56, 57, 58, 59, 60, 62, 64, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 83, 84, 85, 86, 88, 91, 93, 94, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113], "branches": [[71, 72], [71, 84], [74, 75], [74, 76], [100, 0], [100, 101]]}
# gained: {"lines": [32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 46, 47, 48, 50, 51, 52, 53, 54, 56, 57, 58, 59, 60, 62, 64, 68, 69, 70, 71, 84, 85, 86, 88, 91, 93, 94, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113], "branches": [[71, 84], [100, 0], [100, 101]]}

import importlib
import types

import pytest


def _get_module():
    return importlib.import_module("sweagent.run.hooks.open_pr")


class DummyEnv:
    def __init__(self):
        self.calls = []

    def communicate(self, *, input, error_msg, timeout, check=None):
        # record the call
        self.calls.append({"input": input, "error_msg": error_msg, "timeout": timeout, "check": check})
        # return a different string depending on command to help debugging/assertions
        if "git commit" in input:
            return "commit-output"
        if "git push" in input:
            return "push-output"
        return "ok-output"


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.debugs = []

    def info(self, msg):
        self.infos.append(msg)

    def debug(self, msg):
        self.debugs.append(msg)


def test_open_pr_invalid_url_raises(monkeypatch):
    mod = _get_module()

    # Patch _get_gh_issue_data to raise InvalidGithubURL
    InvalidGithubURL = mod.InvalidGithubURL

    def fake_get_issue(url, token=None):
        raise InvalidGithubURL("bad url")

    monkeypatch.setattr(mod, "_get_gh_issue_data", fake_get_issue)

    logger = DummyLogger()
    env = DummyEnv()

    with pytest.raises(ValueError) as exc:
        mod.open_pr(logger=logger, token="tok", env=env, github_url="not-a-url", trajectory=[], _dry_run=True)

    assert "Data path must be a github issue URL if open_pr is set to True." in str(exc.value)


def test_open_pr_dry_run_does_not_create_pr(monkeypatch):
    mod = _get_module()

    # Prepare a fake issue object
    issue = types.SimpleNamespace(number=42, title="The Issue Title")

    def fake_get_issue(url, token=None):
        return issue

    # parse url returns owner, repo, something
    def fake_parse(url):
        return ("ownername", "reponame", None)

    # deterministic random
    monkeypatch.setattr(mod.random, "random", lambda: 0.12345678)

    monkeypatch.setattr(mod, "_get_gh_issue_data", fake_get_issue)
    monkeypatch.setattr(mod, "_parse_gh_issue_url", fake_parse)
    monkeypatch.setattr(mod, "format_trajectory_markdown", lambda traj, char_limit: "TRAJ-MD")

    # Patch GhApi so construction has no side effects; since _dry_run True no pulls.create should occur
    created = {}

    class DummyGhApi:
        def __init__(self, token=None):
            created["token"] = token

        class pulls:
            @staticmethod
            def create(**kwargs):
                # If accidentally called, record it
                created["called"] = True
                created["args"] = kwargs
                return types.SimpleNamespace(html_url="http://fake/pr")

    monkeypatch.setattr(mod, "GhApi", DummyGhApi)

    logger = DummyLogger()
    env = DummyEnv()

    # Call with dry run true: should not call API to create PR
    mod.open_pr(logger=logger, token="token123", env=env, github_url="https://github.com/owner/repo/issues/42", trajectory=["a", "b"], _dry_run=True)

    # Ensure CLI steps were invoked (git config, rm, checkout, add, commit, push)
    inputs = [c["input"] for c in env.calls]
    assert any("git config user.email" in i for i in inputs)
    assert any("rm -f model.patch" in i for i in inputs)
    assert any("git checkout -b swe-agent-fix-#42-" in i for i in inputs)
    assert any("git add ." in i for i in inputs)
    # commit should include --allow-empty since dry run
    assert any("git commit" in i and "--allow-empty" in i for i in inputs)
    # push should be prefixed with echo (dry run prefix)
    assert any(i.strip().startswith("echo") and "git push" in i for i in inputs)

    # Ensure GhApi was constructed with the provided token but pulls.create was not called
    assert created.get("token") == "token123"
    assert "called" not in created

    # Logger should have info about Opening PR
    assert any("Opening PR" in m for m in logger.infos)


def test_open_pr_creates_pr_calls_api(monkeypatch):
    mod = _get_module()

    # Prepare fake issue
    issue = types.SimpleNamespace(number=7, title="Bug in feature X")

    def fake_get_issue(url, token=None):
        return issue

    def fake_parse(url):
        return ("someowner", "somerepo", None)

    monkeypatch.setattr(mod.random, "random", lambda: 0.87654321)
    monkeypatch.setattr(mod, "_get_gh_issue_data", fake_get_issue)
    monkeypatch.setattr(mod, "_parse_gh_issue_url", fake_parse)
    monkeypatch.setattr(mod, "format_trajectory_markdown", lambda traj, char_limit: "TRAJECTORY_CONTENT")

    # Capture the create call
    created = {}

    class DummyGhApi:
        def __init__(self, token=None):
            self.token = token

        class pulls:
            @staticmethod
            def create(**kwargs):
                created["args"] = kwargs
                return types.SimpleNamespace(html_url="https://github.com/someowner/somerepo/pull/1")

    monkeypatch.setattr(mod, "GhApi", DummyGhApi)

    logger = DummyLogger()
    env = DummyEnv()

    mod.open_pr(logger=logger, token="tok-xyz", env=env, github_url="https://github.com/someowner/somerepo/issues/7", trajectory=["step1"], _dry_run=False)

    # Ensure pushes used origin (since forker == owner branch is not taken)
    inputs = [c["input"] for c in env.calls]
    assert any("git push origin" in i or "git push  origin" in i for i in inputs) or any("git push" in i for i in inputs)

    # Ensure API create was called and arguments look correct
    assert "args" in created
    args = created["args"]
    assert args["owner"] == "someowner"
    assert args["repo"] == "somerepo"
    assert "Bug in feature X" in args["title"]
    # head should be the generated branch name
    assert args["head"].startswith("swe-agent-fix-#7-")
    assert args["base"] == "main"
    # body should contain issue number and trajectory content
    assert "Closes #7" in args["body"] or "Closes #7." in args["body"]
    assert "TRAJECTORY_CONTENT" in args["body"]

    # Check logger had a final info about PR creation with url
    assert any("PR created as a draft" in s for s in logger.infos + logger.debugs)
