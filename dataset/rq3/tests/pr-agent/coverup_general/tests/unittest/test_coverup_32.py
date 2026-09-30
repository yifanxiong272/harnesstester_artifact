# file: pr_agent/git_providers/gitea_provider.py:239-275
# asked: {"lines": [241, 242, 243, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 257, 258, 261, 262, 263, 265, 266, 268, 269, 270, 271, 273, 274, 275], "branches": [[241, 242], [241, 245], [245, 246], [245, 247], [247, 248], [247, 250], [261, 262], [261, 265], [265, 266], [265, 268]]}
# gained: {"lines": [241, 242, 243, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 257, 258, 261, 262, 263, 265, 266, 268, 269, 270, 271, 273, 274, 275], "branches": [[241, 242], [241, 245], [245, 246], [245, 247], [247, 248], [247, 250], [261, 262], [261, 265], [265, 266], [265, 268]]}

import types
import pytest

from pr_agent.git_providers.gitea_provider import GiteaProvider


class DummyLogger:
    def __init__(self):
        self.debug_calls = []
        self.error_calls = []
        self.info_calls = []

    def debug(self, msg):
        self.debug_calls.append(msg)

    def error(self, msg):
        self.error_calls.append(msg)

    def info(self, msg):
        self.info_calls.append(msg)


class DummyRepoAPI:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create_comment(self, owner, repo, index, comment):
        self.calls.append({"owner": owner, "repo": repo, "index": index, "comment": comment})
        return self.response


class ResponseObj:
    def __init__(self, id_val):
        self.id = id_val


def make_settings_obj(publish_output_progress: bool):
    cfg = types.SimpleNamespace(publish_output_progress=publish_output_progress)
    return types.SimpleNamespace(config=cfg)


def make_provider_instance():
    # create instance without calling __init__
    p = object.__new__(GiteaProvider)
    return p


def setup_basic_provider(provider, logger=None):
    if logger is None:
        logger = DummyLogger()
    provider.logger = logger
    # default attributes used by publish_comment
    provider.owner = "owner"
    provider.repo = "repo"
    provider.max_comment_chars = 1000
    provider.limit_output_characters = lambda comment, max_chars: comment if comment is not None else comment
    provider.temp_comments = []
    provider.comments_list = []
    return logger


def test_publish_comment_temporary_skipped(monkeypatch):
    # patch the module-level get_settings and get_logger used by GiteaProvider
    monkeypatch.setattr("pr_agent.git_providers.gitea_provider.get_settings", lambda: make_settings_obj(False))
    dummy_logger = DummyLogger()
    monkeypatch.setattr("pr_agent.git_providers.gitea_provider.get_logger", lambda: dummy_logger)

    gp = make_provider_instance()
    # set attributes in case code paths access them after the check
    setup_basic_provider(gp, logger=dummy_logger)
    gp.enabled_issue = False
    gp.enabled_pr = False

    result = gp.publish_comment("temporary comment", is_temporary=True)

    assert result is None
    # check that the module-level get_logger().debug was called with expected message
    assert any("Skipping publish_comment for temporary comment" in m for m in dummy_logger.debug_calls)


def test_publish_comment_neither_pr_nor_issue(monkeypatch):
    # ensure publish_output_progress True so skipping does not occur
    monkeypatch.setattr("pr_agent.git_providers.gitea_provider.get_settings", lambda: make_settings_obj(True))
    # Patch get_logger used in the module so provider.logger can capture messages
    dummy_logger = DummyLogger()
    monkeypatch.setattr("pr_agent.git_providers.gitea_provider.get_logger", lambda: dummy_logger)

    gp = make_provider_instance()
    logger = setup_basic_provider(gp)
    gp.enabled_issue = False
    gp.enabled_pr = False

    result = gp.publish_comment("anything", is_temporary=False)

    assert result is None
    # logger.error should have been called with the expected message
    assert any("Neither PR nor issue URL provided." in msg for msg in logger.error_calls)


def test_publish_comment_failed_publish(monkeypatch):
    # ensure publish_output_progress True
    monkeypatch.setattr("pr_agent.git_providers.gitea_provider.get_settings", lambda: make_settings_obj(True))
    monkeypatch.setattr("pr_agent.git_providers.gitea_provider.get_logger", lambda: DummyLogger())

    gp = make_provider_instance()
    logger = setup_basic_provider(gp)
    # simulate an issue URL enabled path
    gp.enabled_issue = True
    gp.enabled_pr = False
    gp.issue_number = 7
    # repo_api returns falsy (None) to simulate failure
    gp.repo_api = DummyRepoAPI(None)

    result = gp.publish_comment("will fail", is_temporary=False)

    assert result is None
    # Check that create_comment was called with expected index and parameters
    assert gp.repo_api.calls, "create_comment should have been invoked"
    last_call = gp.repo_api.calls[-1]
    assert last_call["index"] == 7
    assert last_call["owner"] == gp.owner and last_call["repo"] == gp.repo
    assert any("Failed to publish comment" in msg for msg in logger.error_calls)


def test_publish_comment_success_temporary_and_non_temporary(monkeypatch):
    # ensure publish_output_progress True
    monkeypatch.setattr("pr_agent.git_providers.gitea_provider.get_settings", lambda: make_settings_obj(True))
    monkeypatch.setattr("pr_agent.git_providers.gitea_provider.get_logger", lambda: DummyLogger())

    gp = make_provider_instance()
    logger = setup_basic_provider(gp)
    # simulate a PR-enabled provider
    gp.enabled_issue = False
    gp.enabled_pr = True
    gp.pr_number = 9

    # First response (temporary)
    gp.repo_api = DummyRepoAPI(ResponseObj(101))

    # Publish temporary comment
    result_temp = gp.publish_comment("temp-hello", is_temporary=True)

    assert isinstance(result_temp, dict)
    assert result_temp["is_temporary"] is True
    assert result_temp["comment"] == "temp-hello"
    assert result_temp["comment_id"] == 101

    # Ensure temp_comments and comments_list were updated and logger.info called
    assert "temp-hello" in gp.temp_comments
    assert gp.comments_list and gp.comments_list[-1] == result_temp
    assert any("Comment published" in msg for msg in logger.info_calls)

    # Now publish non-temporary comment; change response id to differentiate
    gp.repo_api = DummyRepoAPI(ResponseObj(202))
    prev_temp_len = len(gp.temp_comments)
    prev_comments_len = len(gp.comments_list)

    result_perm = gp.publish_comment("perm-hello", is_temporary=False)

    assert isinstance(result_perm, dict)
    assert result_perm["is_temporary"] is False
    assert result_perm["comment"] == "perm-hello"
    assert result_perm["comment_id"] == 202

    # temp_comments should not have grown
    assert len(gp.temp_comments) == prev_temp_len
    # comments_list should have one more entry and last entry matches returned object
    assert len(gp.comments_list) == prev_comments_len + 1
    assert gp.comments_list[-1] == result_perm

    # Verify repo_api calls used the PR index
    assert gp.repo_api.calls[-1]["index"] == gp.pr_number
    assert gp.repo_api.calls[-1]["comment"] == "perm-hello"
