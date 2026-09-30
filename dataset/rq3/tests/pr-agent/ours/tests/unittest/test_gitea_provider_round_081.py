import types
import pytest

from pr_agent.git_providers import gitea_provider
from pr_agent.git_providers.gitea_provider import GiteaProvider


class DummyLogger:
    def __init__(self):
        self.debug_calls = []
        self.info_calls = []
        self.error_calls = []

    def debug(self, msg):
        self.debug_calls.append(msg)

    def info(self, msg):
        self.info_calls.append(msg)

    def error(self, msg):
        self.error_calls.append(msg)


class DummyRepoApi:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def create_comment(self, *, owner, repo, index, comment):
        # record call for assertions
        self.calls.append({
            "owner": owner,
            "repo": repo,
            "index": index,
            "comment": comment,
        })
        return self._response


class Resp:
    def __init__(self, id):
        self.id = id


class RespTuple(tuple):
    # tuple subclass that carries an id attribute to exercise isinstance(response, tuple)
    def __new__(cls, id):
        obj = tuple.__new__(cls, ())
        obj.id = id
        return obj


def make_provider_instance():
    # create instance without invoking constructor so tests can set needed attributes deterministically
    p = GiteaProvider.__new__(GiteaProvider)
    # set defaults expected by publish_comment
    p.enabled_issue = False
    p.enabled_pr = False
    p.issue_number = 111
    p.pr_number = 222
    p.owner = "owner"
    p.repo = "repo"
    p.max_comment_chars = 10000
    p.limit_output_characters = lambda comment, max_chars: comment
    p.temp_comments = []
    p.comments_list = []
    p.logger = DummyLogger()
    return p


def test_publish_comment_temporary_skipped_round_081(monkeypatch):
    """
    If is_temporary is True and settings.config.publish_output_progress is False,
    publish_comment should call module logger.debug and return None (skip publishing).
    """
    provider = make_provider_instance()

    # patch get_settings to return publish_output_progress False
    monkeypatch.setattr(
        gitea_provider,
        "get_settings",
        lambda: types.SimpleNamespace(config=types.SimpleNamespace(publish_output_progress=False)),
    )

    # patch module-level get_logger() to return a logger we can inspect
    module_logger = DummyLogger()
    monkeypatch.setattr(gitea_provider, "get_logger", lambda: module_logger)

    result = gitea_provider.GiteaProvider.publish_comment(provider, "somecomment", is_temporary=True)

    # Should have returned None and have logged a debug about skipping
    assert result is None
    assert any("Skipping publish_comment for temporary comment" in msg for msg in module_logger.debug_calls)


def test_publish_comment_neither_pr_nor_issue_round_081(monkeypatch):
    """
    When neither PR nor issue is enabled, should log error via self.logger and return None.
    """
    # Ensure settings allow publishing to avoid early return
    monkeypatch.setattr(
        gitea_provider,
        "get_settings",
        lambda: types.SimpleNamespace(config=types.SimpleNamespace(publish_output_progress=True)),
    )

    provider = make_provider_instance()
    provider.enabled_issue = False
    provider.enabled_pr = False

    # repo_api should not be called here; set to dummy
    provider.repo_api = DummyRepoApi(response=Resp(999))

    res = gitea_provider.GiteaProvider.publish_comment(provider, "c", is_temporary=False)

    assert res is None
    # self.logger.error should have been called once with expected message
    assert any("Neither PR nor issue URL provided." in msg for msg in provider.logger.error_calls)


def test_publish_comment_response_false_round_081(monkeypatch):
    """
    When repo_api.create_comment returns a falsy value, publish_comment should log error and return None.
    """
    monkeypatch.setattr(
        gitea_provider,
        "get_settings",
        lambda: types.SimpleNamespace(config=types.SimpleNamespace(publish_output_progress=True)),
    )

    provider = make_provider_instance()
    provider.enabled_pr = True
    provider.enabled_issue = False
    provider.pr_number = 42

    # create_comment returns False to simulate failure
    provider.repo_api = DummyRepoApi(response=False)

    res = gitea_provider.GiteaProvider.publish_comment(provider, "will fail", is_temporary=False)

    assert res is None
    assert any("Failed to publish comment" in msg for msg in provider.logger.error_calls)
    # repo_api.create_comment should have been invoked once
    assert len(provider.repo_api.calls) == 1
    call = provider.repo_api.calls[0]
    assert call["owner"] == provider.owner and call["repo"] == provider.repo and call["index"] == provider.pr_number


def test_publish_comment_success_non_temporary_round_081(monkeypatch):
    """
    Successful publish (non-temporary): response object with id should produce a comment object appended to comments_list
    and logger.info called.
    """
    monkeypatch.setattr(
        gitea_provider,
        "get_settings",
        lambda: types.SimpleNamespace(config=types.SimpleNamespace(publish_output_progress=True)),
    )

    provider = make_provider_instance()
    provider.enabled_issue = True
    provider.enabled_pr = False
    provider.issue_number = 7

    resp = Resp(12345)
    provider.repo_api = DummyRepoApi(response=resp)

    res = gitea_provider.GiteaProvider.publish_comment(provider, "a normal comment", is_temporary=False)

    # Expect a dict returned
    assert isinstance(res, dict)
    assert res["is_temporary"] is False
    assert res["comment"] == "a normal comment"
    assert res["comment_id"] == 12345
    # appended to comments_list
    assert provider.comments_list and provider.comments_list[-1] == res
    # info logged
    assert any("Comment published" in msg for msg in provider.logger.info_calls)


def test_publish_comment_success_temporary_tuple_response_round_081(monkeypatch):
    """
    Successful publish when is_temporary True should append to temp_comments and handle a tuple-subclass response
    that carries an id attribute (to exercise isinstance(response, tuple) True branch).
    """
    monkeypatch.setattr(
        gitea_provider,
        "get_settings",
        lambda: types.SimpleNamespace(config=types.SimpleNamespace(publish_output_progress=True)),
    )

    provider = make_provider_instance()
    provider.enabled_pr = True
    provider.enabled_issue = False
    provider.pr_number = 99

    resp = RespTuple(777)
    provider.repo_api = DummyRepoApi(response=resp)

    comment_text = "temp comment"
    res = gitea_provider.GiteaProvider.publish_comment(provider, comment_text, is_temporary=True)

    assert isinstance(res, dict)
    assert res["is_temporary"] is True
    assert res["comment"] == comment_text
    # ensure the id from the tuple-subclass is used
    assert res["comment_id"] == 777
    # ensure temp_comments list got the comment appended
    assert comment_text in provider.temp_comments
    # ensure also stored in comments_list
    assert provider.comments_list and provider.comments_list[-1]["comment_id"] == 777
    assert any("Comment published" in msg for msg in provider.logger.info_calls)
