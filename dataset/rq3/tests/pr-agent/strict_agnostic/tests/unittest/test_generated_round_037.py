import pytest
from pr_agent.git_providers import bitbucket_server_provider as bb


def _make_provider():
    # Create instance without running __init__ so tests remain fast and isolated
    return object.__new__(bb.BitbucketServerProvider)


def test_publish_code_suggestions_with_multi_line_suggestion_round_037():
    provider = _make_provider()

    captured = {}

    def fake_publish(post_parameters_list):
        # capture what would be sent to the publish helper
        captured['posted'] = post_parameters_list

    # attach fake publish method to the instance
    provider.publish_inline_comments = fake_publish

    # suggestion contains an original_suggestion to trigger diff creation
    suggestion = {
        "body": "Intro\n```suggestion\nold line\n```\nFooter",
        "original_suggestion": {
            "existing_code": "line1\nline2\nline3",
            "improved_code": "line1\nLINE2_CHANGED\nline3",
        },
        "relevant_file": "path/to/file.py",
        "relevant_lines_start": 2,
        "relevant_lines_end": 5,
    }

    result = bb.BitbucketServerProvider.publish_code_suggestions(provider, [suggestion])

    # publish_inline_comments should be called with a list containing a multi-line post
    assert result is True
    assert 'posted' in captured
    posted = captured['posted']
    assert isinstance(posted, list) and len(posted) == 1
    post = posted[0]
    assert post['path'] == 'path/to/file.py'
    # multi-line branch uses start_line and line keys
    assert post['start_line'] == 2
    assert post['line'] == 5
    # body should contain a diff block when original_suggestion is present
    assert '```diff' in post['body']


def test_publish_code_suggestions_single_line_and_invalid_start_round_037():
    provider = _make_provider()

    captured = {}

    def fake_publish(post_parameters_list):
        captured['posted'] = post_parameters_list

    provider.publish_inline_comments = fake_publish

    # First suggestion has invalid start (None) -> should be skipped
    # Second suggestion has end < start -> should be skipped
    # Third suggestion is a valid single-line suggestion -> should be published
    suggestions = [
        {
            "body": "no start",
            "relevant_file": "f1.py",
            "relevant_lines_start": None,
            "relevant_lines_end": 1,
        },
        {
            "body": "end before start",
            "relevant_file": "f2.py",
            "relevant_lines_start": 10,
            "relevant_lines_end": 5,
        },
        {
            "body": "single line body",
            "relevant_file": "single.py",
            "relevant_lines_start": 4,
            "relevant_lines_end": 4,
        },
    ]

    result = bb.BitbucketServerProvider.publish_code_suggestions(provider, suggestions)

    assert result is True
    assert 'posted' in captured
    posted = captured['posted']
    # Only the valid single-line suggestion should be published
    assert isinstance(posted, list) and len(posted) == 1
    p = posted[0]
    assert p['path'] == 'single.py'
    # single-line branch uses 'line' and 'side'
    assert p['line'] == 4
    assert p['side'] == 'RIGHT'
    assert p['body'] == 'single line body'


def test_publish_code_suggestions_publish_failure_logs_round_037(monkeypatch):
    provider = _make_provider()

    def raising_publish(post_parameters_list):
        raise RuntimeError("boom")

    provider.publish_inline_comments = raising_publish

    # Patch get_settings to supply verbosity_level >= 2 so code logs error when publish fails
    class Cfg:
        pass

    cfg = Cfg()
    cfg.config = Cfg()
    cfg.config.verbosity_level = 2

    monkeypatch.setattr(bb, 'get_settings', lambda: cfg)

    # capture error logger calls
    captured = {}

    class FakeLogger:
        def error(self, msg):
            # record the message for assertions
            captured['error_msg'] = msg

    monkeypatch.setattr(bb, 'get_logger', lambda: FakeLogger())

    suggestion = {
        "body": "body",
        "relevant_file": "f.py",
        "relevant_lines_start": 1,
        "relevant_lines_end": 1,
    }

    result = bb.BitbucketServerProvider.publish_code_suggestions(provider, [suggestion])

    # publish failed -> should return False and logger.error should be called with context
    assert result is False
    assert 'error_msg' in captured
    assert 'Failed to publish code suggestion' in captured['error_msg']


def test_publish_code_suggestions_original_suggestion_exception_round_037(monkeypatch):
    provider = _make_provider()

    captured = {}

    def fake_publish(post_parameters_list):
        captured['posted'] = post_parameters_list

    provider.publish_inline_comments = fake_publish

    # Make get_logger.exception visible so we can assert it was called
    exc_called = {}

    class FakeLogger:
        def exception(self, msg):
            exc_called['msg'] = msg

        def warning(self, msg):
            # silence warnings during test
            pass

    monkeypatch.setattr(bb, 'get_logger', lambda: FakeLogger())

    # Use a truthy original_suggestion that will raise inside the try block
    # (None has no rstrip, causing an AttributeError inside the try)
    suggestion = {
        "body": "something\n```suggestion\nold\n```",
        "original_suggestion": {"existing_code": None, "improved_code": None},
        "relevant_file": "skip.py",
        "relevant_lines_start": 2,
        "relevant_lines_end": 2,
    }

    result = bb.BitbucketServerProvider.publish_code_suggestions(provider, [suggestion])

    # The original_suggestion triggered an exception inside the diff-creation block,
    # so the suggestion should be skipped and no post parameters produced.
    assert result is True
    assert 'posted' in captured
    assert captured['posted'] == []
    # logger.exception should have been called
    assert 'msg' in exc_called
