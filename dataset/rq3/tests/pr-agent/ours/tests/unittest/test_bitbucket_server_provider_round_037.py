import re
import types
import pytest

import pr_agent.git_providers.bitbucket_server_provider as bb_mod
from pr_agent.git_providers.bitbucket_server_provider import BitbucketServerProvider


class LoggerStub:
    def __init__(self):
        self.warnings = []
        self.errors = []
        self.exceptions = []

    def warning(self, msg):
        self.warnings.append(str(msg))

    def error(self, msg):
        self.errors.append(str(msg))

    def exception(self, msg):
        self.exceptions.append(str(msg))


class SettingsStub:
    class Config:
        def __init__(self, verbosity_level=0):
            self.verbosity_level = verbosity_level

    def __init__(self, verbosity_level=0):
        self.config = SettingsStub.Config(verbosity_level=verbosity_level)


def make_provider_instance():
    # avoid running __init__ logic; publish_code_suggestions only needs publish_inline_comments attr
    provider = BitbucketServerProvider.__new__(BitbucketServerProvider)
    return provider


def test_multiline_suggestion_round_037(monkeypatch):
    """Exercise branch where original_suggestion exists and relevant_lines_end > relevant_lines_start
    Ensure the suggestion block is replaced with a diff-like code block and publish_inline_comments receives
    the expected multi-line-shaped payload.
    """
    logger = LoggerStub()
    monkeypatch.setattr(bb_mod, "get_logger", lambda: logger)
    monkeypatch.setattr(bb_mod, "get_settings", lambda: SettingsStub(verbosity_level=0))

    provider = make_provider_instance()

    captured = {}

    def fake_publish(params):
        # capture for assertion
        captured['params'] = params
        return None

    provider.publish_inline_comments = fake_publish

    body = "Intro\n```suggestion\nold line\n```\nOutro"
    suggestion = {
        "body": body,
        "original_suggestion": {
            # make several lines so difflib produces context; exact diff content isn't important
            "existing_code": "a\nb\nc\nd\ne\n",
            "improved_code": "a\nb\nC\nd\ne\n",
        },
        "relevant_file": "some/file.py",
        "relevant_lines_start": 1,
        "relevant_lines_end": 3,
    }

    res = provider.publish_code_suggestions([suggestion])

    assert res is True
    # publish_inline_comments should be called and captured
    assert 'params' in captured
    assert isinstance(captured['params'], list) and len(captured['params']) == 1
    p = captured['params'][0]
    # Multi-line branch uses keys start_line, start_side and line==relevant_lines_end
    assert p['path'] == 'some/file.py'
    assert p['start_line'] == 1
    assert p['line'] == 3
    assert p['start_side'] == 'RIGHT'
    # body should have had the ```suggestion block replaced (no literal '```suggestion' remains)
    assert '```suggestion' not in p['body']
    assert p['body'].startswith('Intro') and p['body'].endswith('Outro')


def test_single_line_suggestion_round_037(monkeypatch):
    """Exercise the single-line branch where relevant_lines_end == relevant_lines_start.
    Confirm that the payload uses the single-line API shape (line + side) and returns True.
    """
    logger = LoggerStub()
    monkeypatch.setattr(bb_mod, "get_logger", lambda: logger)
    monkeypatch.setattr(bb_mod, "get_settings", lambda: SettingsStub(verbosity_level=0))

    provider = make_provider_instance()

    captured = {}

    def fake_publish(params):
        captured['params'] = params
        return None

    provider.publish_inline_comments = fake_publish

    suggestion = {
        "body": "just a body",
        "relevant_file": "single/file.py",
        "relevant_lines_start": 5,
        "relevant_lines_end": 5,
    }

    res = provider.publish_code_suggestions([suggestion])

    assert res is True
    assert 'params' in captured
    assert isinstance(captured['params'], list) and len(captured['params']) == 1
    p = captured['params'][0]
    # Single-line branch uses 'line' and 'side'
    assert p['path'] == 'single/file.py'
    assert p['line'] == 5
    assert p['side'] == 'RIGHT'
    assert p['body'] == 'just a body'


def test_publish_failure_logs_error_round_037(monkeypatch):
    """If publish_inline_comments raises, and verbosity_level >=2, ensure an error is logged and False is returned.
    """
    logger = LoggerStub()
    monkeypatch.setattr(bb_mod, "get_logger", lambda: logger)
    # verbosity_level >= 2 triggers error logging path
    monkeypatch.setattr(bb_mod, "get_settings", lambda: SettingsStub(verbosity_level=2))

    provider = make_provider_instance()

    def raising_publish(params):
        raise RuntimeError("boom")

    provider.publish_inline_comments = raising_publish

    suggestion = {
        "body": "body",
        "relevant_file": "f.py",
        "relevant_lines_start": 2,
        "relevant_lines_end": 2,
    }

    res = provider.publish_code_suggestions([suggestion])

    assert res is False
    # an error should have been logged
    assert any('Failed to publish code suggestion' in e for e in logger.errors)


def test_skip_on_invalid_start_and_invalid_end_round_037(monkeypatch):
    """Ensure suggestions with invalid starts or end<start are skipped and warnings are logged.
    Also verify that when nothing valid is appended, publish_inline_comments receives an empty list.
    """
    logger = LoggerStub()
    monkeypatch.setattr(bb_mod, "get_logger", lambda: logger)
    monkeypatch.setattr(bb_mod, "get_settings", lambda: SettingsStub(verbosity_level=0))

    provider = make_provider_instance()

    received = {}

    def fake_publish(params):
        received['params'] = params
        return None

    provider.publish_inline_comments = fake_publish

    suggestions = [
        {  # start is None -> skip
            "body": "b",
            "relevant_file": "a.py",
            "relevant_lines_start": None,
            "relevant_lines_end": 1,
        },
        {  # end < start -> skip
            "body": "b2",
            "relevant_file": "a.py",
            "relevant_lines_start": 10,
            "relevant_lines_end": 5,
        },
    ]

    res = provider.publish_code_suggestions(suggestions)

    assert res is True
    # publish_inline_comments should still be invoked with an empty list
    assert 'params' in received
    assert received['params'] == []
    # two warnings should have been emitted (one per skipped suggestion)
    assert len(logger.warnings) >= 2
