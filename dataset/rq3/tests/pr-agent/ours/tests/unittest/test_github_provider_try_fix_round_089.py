import copy
import pr_agent.git_providers.github_provider as github_provider


def test_try_fix_invalid_inline_comments_modified_round_089():
    # comment has a suggestion block and start_line/start_side -> should be fixed and returned
    original = {
        "body": "first line\n```suggestion\nreplacement code\n```\n",
        "start_line": 42,
        "start_side": "LEFT",
    }
    original_copy = copy.deepcopy(original)

    result = github_provider.GithubProvider._try_fix_invalid_inline_comments(None, [original])

    # one fixed comment expected
    assert isinstance(result, list) and len(result) == 1
    fixed = result[0]

    # suggestion removed: split before ```suggestion
    assert fixed["body"] == original["body"].split("```suggestion")[0]

    # start_line renamed to line and removed
    assert fixed["line"] == 42
    assert "start_line" not in fixed

    # start_side renamed to side and removed
    assert fixed["side"] == "LEFT"
    assert "start_side" not in fixed

    # original comment must not be mutated
    assert original == original_copy


def test_try_fix_invalid_inline_comments_no_change_round_089():
    # comment that doesn't need modification should not be returned
    comment = {"body": "no suggestion here"}

    result = github_provider.GithubProvider._try_fix_invalid_inline_comments(None, [comment])

    assert result == []


def test_try_fix_invalid_inline_comments_exception_logs_round_089(monkeypatch):
    # make deepcopy raise to trigger the exception branch and ensure get_logger().error is called
    class DummyLogger:
        def __init__(self):
            self.messages = []

        def error(self, msg):
            self.messages.append(msg)

    dummy_logger = DummyLogger()

    # Patch the module-level copy.deepcopy used by the function to raise
    def fake_deepcopy(_):
        raise ValueError("boom")

    monkeypatch.setattr(github_provider, "copy", type("C", (), {"deepcopy": staticmethod(fake_deepcopy)})())

    # Patch get_logger to return our dummy logger
    monkeypatch.setattr(github_provider, "get_logger", lambda: dummy_logger)

    comment = {"body": "something that triggers deepcopy"}

    result = github_provider.GithubProvider._try_fix_invalid_inline_comments(None, [comment])

    # On exception, function should return an empty list and log an error containing the exception message
    assert result == []
    assert len(dummy_logger.messages) == 1
    assert "Failed to fix inline comment, error:" in dummy_logger.messages[0]
    assert "boom" in dummy_logger.messages[0]
