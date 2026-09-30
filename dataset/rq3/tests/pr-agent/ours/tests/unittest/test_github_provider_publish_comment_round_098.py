import importlib
import types
import pytest

# Import the module under test so we can patch symbols where the function resolves them
gp = importlib.import_module("pr_agent.git_providers.github_provider")
from pr_agent.git_providers.github_provider import GithubProvider


class DummyLogger:
    def __init__(self):
        self.records = {"error": [], "debug": []}

    def error(self, *args, **kwargs):
        self.records["error"].append((args, kwargs))

    def debug(self, *args, **kwargs):
        self.records["debug"].append((args, kwargs))


def make_settings(publish_output_progress: bool):
    return types.SimpleNamespace(config=types.SimpleNamespace(publish_output_progress=publish_output_progress))


def test_publish_comment_no_context_round_098(monkeypatch):
    """When both pr and issue_main are missing, an error is logged and None is returned."""
    logger = DummyLogger()
    # Patch get_logger and get_settings in the module where publish_comment resolves them
    monkeypatch.setattr(gp, "get_logger", lambda: logger)
    monkeypatch.setattr(gp, "get_settings", lambda: make_settings(True))

    fake_self = types.SimpleNamespace()
    fake_self.pr = None
    fake_self.issue_main = None
    # Call the unbound function with our fake self
    result = GithubProvider.publish_comment(fake_self, "ignored comment", is_temporary=False)

    assert result is None
    # Confirm an error was logged with the expected message fragment
    assert logger.records["error"], "Expected error log to be called"
    assert any("Cannot publish a comment" in args[0] for args, _ in logger.records["error"])


def test_publish_comment_temporary_skipped_when_disabled_round_098(monkeypatch):
    """When is_temporary is True but publish_output_progress is False, debug logged and None returned."""
    logger = DummyLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: logger)
    # publish_output_progress disabled
    monkeypatch.setattr(gp, "get_settings", lambda: make_settings(False))

    # Provide a fake pr so first check passes
    fake_pr = types.SimpleNamespace()
    fake_self = types.SimpleNamespace(pr=fake_pr, issue_main=None)

    result = GithubProvider.publish_comment(fake_self, "temp comment", is_temporary=True)

    assert result is None
    assert logger.records["debug"], "Expected debug log to be called"
    # Debug message should mention skipping temporary comment
    assert any("Skipping publish_comment for temporary comment" in args[0] for args, _ in logger.records["debug"])


def test_publish_comment_uses_issue_main_create_comment_round_098(monkeypatch):
    """If issue_main is present, publish_comment calls issue_main.create_comment and returns its value."""
    logger = DummyLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: logger)
    monkeypatch.setattr(gp, "get_settings", lambda: make_settings(True))

    created = []

    class FakeIssueMain:
        def create_comment(self, text):
            created.append(text)
            return "ISSUE_COMMENT_RETURN"

    # Fake self with an issue_main and a limit_output_characters implementation
    fake_self = types.SimpleNamespace()
    fake_self.pr = None
    fake_self.issue_main = FakeIssueMain()
    fake_self.max_comment_chars = 123

    # record that limit_output_characters is used and returns modified value
    def limiter(s, m):
        # Simulate trimming by returning a predictable transformation
        return s + "::LIMITED"

    fake_self.limit_output_characters = limiter

    result = GithubProvider.publish_comment(fake_self, "comment-body", is_temporary=False)

    assert result == "ISSUE_COMMENT_RETURN"
    # ensure limiter was applied and issue_main received transformed input
    assert created == ["comment-body::LIMITED"]


def test_publish_comment_pr_response_sets_user_and_creates_comments_list_round_098(monkeypatch):
    """When publishing to a PR response with a user.login, github_user_id is set and comments_list created."""
    monkeypatch.setattr(gp, "get_logger", lambda: DummyLogger())
    monkeypatch.setattr(gp, "get_settings", lambda: make_settings(True))

    # Build a response object that mimics what GitHub might return
    response = types.SimpleNamespace()
    response.user = types.SimpleNamespace(login="bot-login")

    # create_issue_comment should return our response object
    fake_pr = types.SimpleNamespace()
    fake_pr.create_issue_comment = lambda text: response

    fake_self = types.SimpleNamespace()
    fake_self.pr = fake_pr
    fake_self.issue_main = None
    fake_self.max_comment_chars = 200
    fake_self.limit_output_characters = lambda s, m: s  # no-op limiter
    fake_self.github_user_id = None

    result = GithubProvider.publish_comment(fake_self, "final comment", is_temporary=True)

    # The returned object should be the same response, with is_temporary set
    assert result is response
    assert getattr(response, "is_temporary") is True
    # github_user_id should be set from response.user.login
    assert fake_self.github_user_id == "bot-login"
    # comments_list should have been created and contain the response
    assert hasattr(fake_pr, "comments_list")
    assert fake_pr.comments_list == [response]


def test_publish_comment_pr_response_without_user_keeps_github_user_id_unchanged_and_appends_round_098(monkeypatch):
    """If response lacks a user/login, github_user_id is not set. Also handle existing comments_list branch."""
    monkeypatch.setattr(gp, "get_logger", lambda: DummyLogger())
    monkeypatch.setattr(gp, "get_settings", lambda: make_settings(True))

    # Response without user attribute
    response = types.SimpleNamespace()

    # pr already has a comments_list; test append branch where attribute exists
    fake_pr = types.SimpleNamespace()
    fake_pr.comments_list = ["existing"]
    fake_pr.create_issue_comment = lambda text: response

    fake_self = types.SimpleNamespace()
    fake_self.pr = fake_pr
    fake_self.issue_main = None
    fake_self.max_comment_chars = 200
    fake_self.limit_output_characters = lambda s, m: s
    fake_self.github_user_id = None

    result = GithubProvider.publish_comment(fake_self, "other comment", is_temporary=False)

    assert result is response
    # No user.login so github_user_id should remain None
    assert fake_self.github_user_id is None
    # response.is_temporary updated
    assert getattr(response, "is_temporary") is False
    # Original comments_list preserved and response appended
    assert fake_pr.comments_list[0] == "existing"
    assert fake_pr.comments_list[-1] is response
