import pytest
from types import SimpleNamespace
from urllib.parse import quote_plus

import pr_agent.git_providers.bitbucket_server_provider as provider_mod
from pr_agent.git_providers.bitbucket_server_provider import BitbucketServerProvider


def _make_provider_instance():
    # Create instance without running __init__ to avoid external side effects
    inst = BitbucketServerProvider.__new__(BitbucketServerProvider)
    return inst


def test_empty_relevant_line_round_062(monkeypatch):
    """When relevant_line is empty the method should return an empty string
    and should not call the line-finding helper."""
    p = _make_provider_instance()

    # If the helper is called, fail the test
    def _should_not_be_called(*_a, **_k):
        raise AssertionError("find_line_number_of_relevant_line_in_file should not be called when relevant_line is empty")

    monkeypatch.setattr(provider_mod, 'find_line_number_of_relevant_line_in_file', _should_not_be_called)

    suggestion = {'relevant_file': 'somefile.py', 'relevant_line': ''}

    result = BitbucketServerProvider.generate_link_to_relevant_line_number(p, suggestion)
    assert result == ""


def test_absolute_position_and_pr_set_round_062(monkeypatch):
    """When an absolute position is found and PR flag is set, a diff link is returned."""
    p = _make_provider_instance()

    # Simulate the line finder returning absolute_position 42
    monkeypatch.setattr(provider_mod, 'find_line_number_of_relevant_line_in_file', lambda df, rf, rl: (None, 42))

    # Provide a diff file list (content not used by stub)
    p.get_diff_files = lambda: ["irrelevant"]

    p.pr = True
    p.pr_url = 'http://example.com/pr'

    # include backticks and trailing spaces to exercise stripping logic
    raw_file = "`path/to/some file.py`  "
    suggestion = {'relevant_file': raw_file, 'relevant_line': '15\n'}

    result = BitbucketServerProvider.generate_link_to_relevant_line_number(p, suggestion)

    # replicate the same stripping/quoting used in the implementation
    expected_file = raw_file.strip('`').strip("'").rstrip()
    expected = f"{p.pr_url}/diff#{quote_plus(expected_file)}?t=42"
    assert result == expected


def test_absolute_position_no_pr_logs_round_062(monkeypatch):
    """When absolute position is found but PR flag is False and verbosity>=2,
    logger.info should be called and function returns empty string."""
    p = _make_provider_instance()

    monkeypatch.setattr(provider_mod, 'find_line_number_of_relevant_line_in_file', lambda df, rf, rl: (0, 11))
    p.get_diff_files = lambda: []
    p.pr = False
    p.pr_url = None

    # Provide settings with high verbosity
    monkeypatch.setattr(provider_mod, 'get_settings', lambda: SimpleNamespace(config=SimpleNamespace(verbosity_level=2)))

    logged = []

    class FakeLogger:
        def info(self, msg):
            logged.append(msg)

    monkeypatch.setattr(provider_mod, 'get_logger', lambda: FakeLogger())

    suggestion = {'relevant_file': "fileX.py", 'relevant_line': '1'}

    result = BitbucketServerProvider.generate_link_to_relevant_line_number(p, suggestion)

    assert result == ""
    # ensure a log entry was made mentioning the relevant file and PR not set
    assert any("Failed adding line link to 'fileX.py'" in m and 'PR not set' in m for m in logged)


def test_position_not_found_logs_round_062(monkeypatch):
    """When position is not found (absolute_position == -1) and verbosity>=2,
    logger.info should be called with position-not-found message."""
    p = _make_provider_instance()

    monkeypatch.setattr(provider_mod, 'find_line_number_of_relevant_line_in_file', lambda df, rf, rl: (None, -1))
    p.get_diff_files = lambda: []
    p.pr = False
    p.pr_url = None

    monkeypatch.setattr(provider_mod, 'get_settings', lambda: SimpleNamespace(config=SimpleNamespace(verbosity_level=2)))

    logs = []

    class FakeLogger2:
        def info(self, msg):
            logs.append(msg)

    monkeypatch.setattr(provider_mod, 'get_logger', lambda: FakeLogger2())

    suggestion = {'relevant_file': "some/other.py", 'relevant_line': '42'}

    result = BitbucketServerProvider.generate_link_to_relevant_line_number(p, suggestion)

    assert result == ""
    assert any("since position not found" in m for m in logs)


def test_exception_logs_round_062(monkeypatch):
    """If the helper raises an exception, the exception is caught and logged (verbosity>=2). Function returns empty string."""
    p = _make_provider_instance()

    def _raiser(*_a, **_k):
        raise ValueError("boom-error")

    monkeypatch.setattr(provider_mod, 'find_line_number_of_relevant_line_in_file', _raiser)
    p.get_diff_files = lambda: []
    p.pr = False
    p.pr_url = None

    monkeypatch.setattr(provider_mod, 'get_settings', lambda: SimpleNamespace(config=SimpleNamespace(verbosity_level=2)))

    captured = []

    class FakeLogger3:
        def info(self, msg):
            captured.append(msg)

    monkeypatch.setattr(provider_mod, 'get_logger', lambda: FakeLogger3())

    suggestion = {'relevant_file': "err/file.py", 'relevant_line': 'x'}

    result = BitbucketServerProvider.generate_link_to_relevant_line_number(p, suggestion)

    assert result == ""
    # log must mention the relevant file and the error message
    assert any("Failed adding line link to 'err/file.py', error:" in m and 'boom-error' in m for m in captured)
