# file: pr_agent/tools/pr_help_docs.py:457-492
# asked: {"lines": [458, 459, 460, 461, 462, 463, 464, 466, 467, 468, 469, 470, 471, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 491, 492], "branches": [[459, 460], [459, 466], [462, 463], [462, 464], [469, 470], [469, 473], [475, 476], [475, 484], [476, 477], [476, 478], [484, 485], [484, 486]]}
# gained: {"lines": [458, 459, 460, 461, 462, 463, 466, 467, 468, 469, 470, 471, 474, 475, 476, 478, 479, 480, 481, 482, 483, 484, 486, 487, 491, 492], "branches": [[459, 460], [459, 466], [462, 463], [469, 470], [475, 476], [476, 478], [484, 486]]}

import types
from types import SimpleNamespace
import pytest

from pr_agent.tools import pr_help_docs as ph


class DummyLogger:
    def __init__(self):
        self.warnings = []
        self.debugs = []
        self.infos = []
        self.exceptions = []

    def warning(self, msg):
        self.warnings.append(msg)

    def debug(self, msg):
        self.debugs.append(msg)

    def info(self, msg):
        self.infos.append(msg)

    def exception(self, msg):
        self.exceptions.append(msg)


def make_prhelpdocs_with_token_handler(count_fn):
    # Create instance without calling __init__ to avoid heavy initialization
    pr = object.__new__(ph.PRHelpDocs)
    pr.token_handler = SimpleNamespace(count_tokens=count_fn)
    return pr


def test_only_return_if_trim_needed_triggers_and_skips_count(monkeypatch):
    # Setup: make docs_input exceed max_allowed_txt_input and ensure only_return_if_trim_needed returns True
    docs_input = "x" * 200
    max_allowed_txt_input = 100

    logger = DummyLogger()
    monkeypatch.setattr(ph, "get_logger", lambda: logger)

    # token counter should not be called; make it raise if called to ensure it isn't invoked
    def bad_count(_docs_input, force_accurate=True):
        raise AssertionError("count_tokens should not have been called")

    pr = make_prhelpdocs_with_token_handler(bad_count)

    result = pr._trim_docs_input(docs_input, max_allowed_txt_input, only_return_if_trim_needed=True)
    assert result is True
    # Ensure warning was logged
    assert any("exceeds the current returned limit" in w for w in logger.warnings)


def test_trimming_and_clipping_path_calls_clean_and_clip_and_returns_clipped(monkeypatch):
    # Setup: docs_input shorter than max_allowed_txt_input so initial length trim not triggered
    docs_input = "some large documentation text" * 100
    max_allowed_txt_input = len(docs_input) + 10  # so initial length check does nothing

    # Prepare logger
    logger = DummyLogger()
    monkeypatch.setattr(ph, "get_logger", lambda: logger)

    # Prepare token count to be very large to trigger clipping branch
    token_count = 10000

    def count_tokens(_docs_input, force_accurate=True):
        # force_accurate must be accepted
        assert force_accurate is True
        return token_count

    pr = make_prhelpdocs_with_token_handler(count_tokens)

    # Monkeypatch get_settings to provide a model that will be in MAX_TOKENS mapping
    fake_settings = SimpleNamespace(config=SimpleNamespace(model="fake-model"))
    monkeypatch.setattr(ph, "get_settings", lambda: fake_settings)

    # Monkeypatch MAX_TOKENS in the module to control max token value
    monkeypatch.setitem(ph.MAX_TOKENS, "fake-model", 8000)  # max_tokens_full = 8000

    # Prepare clean_markdown_content and clip_tokens to record calls and return values
    cleaned_called = {}
    def fake_clean_markdown_content(text):
        cleaned_called['called'] = True
        cleaned_called['text'] = text
        return "CLEANED_CONTENT"

    clip_called = {}
    def fake_clip_tokens(text, limit, num_input_tokens=None):
        clip_called['called'] = True
        clip_called['text'] = text
        clip_called['limit'] = limit
        clip_called['num_input_tokens'] = num_input_tokens
        return "CLIPPED_CONTENT"

    monkeypatch.setattr(ph, "clean_markdown_content", fake_clean_markdown_content)
    monkeypatch.setattr(ph, "clip_tokens", fake_clip_tokens)

    result = pr._trim_docs_input(docs_input, max_allowed_txt_input, only_return_if_trim_needed=False)

    # Assert we got the clipped content back
    assert result == "CLIPPED_CONTENT"

    # Assert cleaning and clipping were called
    assert cleaned_called.get('called', False) is True
    assert clip_called.get('called', False) is True

    # Validate clip was called with expected limit (max_tokens_full - delta_output)
    expected_limit = 8000 - 5000  # delta_output is 5000 in implementation
    assert clip_called['limit'] == expected_limit
    assert clip_called['num_input_tokens'] == token_count

    # Info log should mention attempting to clip
    assert any("Attempting to clip" in info for info in logger.infos)


def test_exception_path_logs_and_reraises(monkeypatch):
    # Setup: make token_handler.count_tokens raise an exception to exercise except block
    def exploding_count(_docs_input, force_accurate=True):
        raise RuntimeError("boom")

    pr = make_prhelpdocs_with_token_handler(exploding_count)

    logger = DummyLogger()
    monkeypatch.setattr(ph, "get_logger", lambda: logger)

    # Ensure get_settings is present (not necessary here but safe)
    monkeypatch.setattr(ph, "get_settings", lambda: SimpleNamespace(config=SimpleNamespace(model="whatever")))

    with pytest.raises(RuntimeError, match="boom"):
        pr._trim_docs_input("text", 1000, only_return_if_trim_needed=False)

    # Ensure logger.exception was called
    assert len(logger.exceptions) >= 1
    assert any("Unexpected exception" in e for e in logger.exceptions)
