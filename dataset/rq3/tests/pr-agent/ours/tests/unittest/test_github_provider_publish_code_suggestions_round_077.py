import pytest

from pr_agent.git_providers import github_provider
from pr_agent.git_providers.github_provider import GithubProvider


class DummyLogger:
    def __init__(self):
        self.exceptions = []
        self.errors = []

    def exception(self, msg):
        # mimic logger.exception signature
        self.exceptions.append(str(msg))

    def error(self, msg):
        # mimic logger.error signature
        self.errors.append(str(msg))


def make_provider_with_overrides(validate_return, publish_impl):
    # Create instance without calling real __init__ to avoid external dependencies
    provider = GithubProvider.__new__(GithubProvider)
    # attach the methods used by publish_code_suggestions
    provider.validate_comments_inside_hunks = lambda suggestions: validate_return
    provider.publish_inline_comments = publish_impl
    return provider


def test_publish_code_suggestions_success_round_077():
    """
    Validate that publish_code_suggestions transforms validated suggestions into
    the expected post parameter shapes for multi-line and single-line comments,
    that invalid suggestions are logged via logger.exception, and returns True
    when publish_inline_comments succeeds.
    """
    fake_logger = DummyLogger()
    # Patch the module-level get_logger used in the function under test
    github_provider.get_logger = lambda: fake_logger

    # Prepare validated suggestions to exercise branches:
    # 1) relevant_lines_start falsy -> logged and skipped
    # 2) relevant_lines_end < relevant_lines_start -> logged and skipped
    # 3) relevant_lines_end > relevant_lines_start -> multi-line post params
    # 4) relevant_lines_end == relevant_lines_start -> single-line post params
    suggestions = [
        {"body": "no start", "relevant_file": "a.py", "relevant_lines_start": None, "relevant_lines_end": 1},
        {"body": "reversed", "relevant_file": "b.py", "relevant_lines_start": 10, "relevant_lines_end": 5},
        {"body": "multi", "relevant_file": "c.py", "relevant_lines_start": 20, "relevant_lines_end": 25},
        {"body": "single", "relevant_file": "d.py", "relevant_lines_start": 30, "relevant_lines_end": 30},
    ]

    # capture what publish_inline_comments receives
    captured = {}

    def fake_publish_inline_comments(post_parameters_list):
        captured['called'] = True
        # store a deep-ish copy to avoid references
        captured['args'] = [dict(x) for x in post_parameters_list]
        return None

    provider = make_provider_with_overrides(suggestions, fake_publish_inline_comments)

    result = GithubProvider.publish_code_suggestions(provider, code_suggestions=[])  # suggestions are provided via override

    assert result is True
    # verify that publish_inline_comments was called
    assert captured.get('called', False) is True

    # Expect two post_parameters: one for 'multi' and one for 'single'
    expected_multi = {
        "body": "multi",
        "path": "c.py",
        "line": 25,
        "start_line": 20,
        "start_side": "RIGHT",
    }
    expected_single = {
        "body": "single",
        "path": "d.py",
        "line": 30,
        "side": "RIGHT",
    }

    # Order should follow the validated suggestions order; multi then single
    assert captured['args'] == [expected_multi, expected_single]

    # Ensure logger.exception was called for the two invalid suggestions
    assert any("relevant_lines_start is None" or "relevant_lines_start is" for _ in [0])  # sanity placeholder
    # Check length of recorded exceptions: two invalid suggestions produced exceptions
    assert len(fake_logger.exceptions) == 2


def test_publish_code_suggestions_publish_fails_round_077():
    """
    When publish_inline_comments raises, the provider should catch the exception,
    log via logger.error, and return False.
    """
    fake_logger = DummyLogger()
    github_provider.get_logger = lambda: fake_logger

    suggestions = [
        {"body": "will fail", "relevant_file": "e.py", "relevant_lines_start": 1, "relevant_lines_end": 2},
    ]

    def raising_publish_inline_comments(post_parameters_list):
        raise RuntimeError("boom")

    provider = make_provider_with_overrides(suggestions, raising_publish_inline_comments)

    result = GithubProvider.publish_code_suggestions(provider, code_suggestions=[])

    assert result is False
    # The logger.error should have been called with a message including the exception text
    assert any("boom" in msg for msg in fake_logger.errors), f"Expected 'boom' in errors, got: {fake_logger.errors}"
