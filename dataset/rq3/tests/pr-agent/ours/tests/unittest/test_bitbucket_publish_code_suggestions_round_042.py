import types
import re
import pytest

import pr_agent.git_providers.bitbucket_provider as bb_mod

# Simple logger stub to capture messages deterministically
class DummyLogger:
    def __init__(self):
        self.exception_calls = []
        self.error_calls = []

    def exception(self, msg):
        # store stringified message for assertions
        self.exception_calls.append(str(msg))

    def error(self, msg):
        self.error_calls.append(str(msg))


def _call_publish(self_obj, suggestions):
    # call the unbound function from the class to avoid full instantiation
    return bb_mod.BitbucketProvider.publish_code_suggestions(self_obj, suggestions)


def test_publish_code_suggestions_multi_line_with_diff_round_042(monkeypatch):
    logger = DummyLogger()
    # patch module-level get_logger to return our dummy logger
    monkeypatch.setattr(bb_mod, "get_logger", lambda: logger)

    captured = {}

    # prepare a self object that captures the argument passed to publish_inline_comments
    def publish_inline_comments(payload):
        captured['payload'] = payload

    self_obj = types.SimpleNamespace(publish_inline_comments=publish_inline_comments)

    # body contains a suggestion block that should be replaced by a diff
    suggestions = [
        {
            "body": "Intro\n```suggestion\nold line\n```\nOutro",
            "original_suggestion": {
                # provide strings that produce a non-empty diff
                "existing_code": "line1\nline2\n",
                "improved_code": "line1\nline2\nline3\n",
            },
            "relevant_file": "some/file.py",
            "relevant_lines_start": 1,
            "relevant_lines_end": 3,
        }
    ]

    result = _call_publish(self_obj, suggestions)

    # publish_inline_comments should be called and the payload contain the diff wrapper
    assert result is True
    assert 'payload' in captured
    assert isinstance(captured['payload'], list)
    assert len(captured['payload']) == 1
    post_params = captured['payload'][0]
    # multi-line branch: start_line and start_side expected
    assert post_params['start_line'] == 1
    assert post_params['start_side'] == 'RIGHT'
    # body should now contain a diff fenced block
    assert '```diff' in post_params['body']


def test_publish_code_suggestions_original_suggestion_error_round_042(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(bb_mod, "get_logger", lambda: logger)

    captured = {}

    def publish_inline_comments(payload):
        captured['payload'] = payload

    self_obj = types.SimpleNamespace(publish_inline_comments=publish_inline_comments)

    # cause an exception inside the original_suggestion processing by providing a non-string
    suggestions = [
        {
            "body": "Intro\n```suggestion\nbad\n```",
            "original_suggestion": {
                "existing_code": None,  # None.rstrip() will raise
                "improved_code": "x",
            },
            "relevant_file": "f.py",
            "relevant_lines_start": 1,
            "relevant_lines_end": 2,
        }
    ]

    result = _call_publish(self_obj, suggestions)

    # the problematic suggestion should be skipped, but publish_inline_comments still called with empty list
    assert result is True
    assert 'payload' in captured
    assert captured['payload'] == []
    # logger.exception should have been called with an error about diff code
    assert any('Bitbucket failed to get diff code for publishing' in s for s in logger.exception_calls)


def test_publish_code_suggestions_invalid_relevant_lines_start_round_042(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(bb_mod, "get_logger", lambda: logger)

    captured = {}

    def publish_inline_comments(payload):
        captured['payload'] = payload

    self_obj = types.SimpleNamespace(publish_inline_comments=publish_inline_comments)

    # relevant_lines_start is -1 -> trigger early continue and log
    suggestions = [
        {
            "body": "no-op",
            "relevant_file": "g.py",
            "relevant_lines_start": -1,
            "relevant_lines_end": 10,
        }
    ]

    result = _call_publish(self_obj, suggestions)

    assert result is True
    assert 'payload' in captured
    assert captured['payload'] == []
    assert any('Failed to publish code suggestion, relevant_lines_start is -1' in s for s in logger.exception_calls)


def test_publish_code_suggestions_relevant_lines_end_less_than_start_round_042(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(bb_mod, "get_logger", lambda: logger)

    captured = {}

    def publish_inline_comments(payload):
        captured['payload'] = payload

    self_obj = types.SimpleNamespace(publish_inline_comments=publish_inline_comments)

    # end < start -> log and continue
    suggestions = [
        {
            "body": "no-op",
            "relevant_file": "h.py",
            "relevant_lines_start": 10,
            "relevant_lines_end": 5,
        }
    ]

    result = _call_publish(self_obj, suggestions)

    assert result is True
    assert 'payload' in captured
    assert captured['payload'] == []
    assert any('Failed to publish code suggestion, ' in s for s in logger.exception_calls)


def test_publish_code_suggestions_single_line_comment_round_042(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(bb_mod, "get_logger", lambda: logger)

    captured = {}

    def publish_inline_comments(payload):
        captured['payload'] = payload

    self_obj = types.SimpleNamespace(publish_inline_comments=publish_inline_comments)

    # equal start and end should take the single-line branch
    suggestions = [
        {
            "body": "single",
            "relevant_file": "single.py",
            "relevant_lines_start": 7,
            "relevant_lines_end": 7,
        }
    ]

    result = _call_publish(self_obj, suggestions)

    assert result is True
    assert 'payload' in captured
    assert len(captured['payload']) == 1
    post_params = captured['payload'][0]
    # single-line branch uses 'line' and 'side'
    assert post_params['line'] == 7
    assert post_params['side'] == 'RIGHT'


def test_publish_code_suggestions_publish_inline_comments_raises_round_042(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(bb_mod, "get_logger", lambda: logger)

    # make publish_inline_comments raise to hit the final except
    def publish_inline_comments(payload):
        raise RuntimeError('boom')

    self_obj = types.SimpleNamespace(publish_inline_comments=publish_inline_comments)

    suggestions = [
        {
            "body": "ok",
            "relevant_file": "z.py",
            "relevant_lines_start": 1,
            "relevant_lines_end": 1,
        }
    ]

    result = _call_publish(self_obj, suggestions)

    # should return False and log an error
    assert result is False
    assert any('Bitbucket failed to publish code suggestion' in s for s in logger.error_calls)
