import pytest
from types import SimpleNamespace
import pr_agent.tools.pr_help_docs as phm
from pr_agent.tools.pr_help_docs import PRHelpDocs

# Helpers to create a bare PRHelpDocs instance without running its __init__
def _make_prhelpdocs_with_token_handler(count_fn):
    obj = PRHelpDocs.__new__(PRHelpDocs)
    # token_handler must have a count_tokens method
    obj.token_handler = SimpleNamespace(count_tokens=count_fn)
    return obj


def test_trim_docs_input_length_only_return_round_061(monkeypatch):
    """
    If the input length >= max_allowed_txt_input and only_return_if_trim_needed is True,
    the method should return True immediately (line ~462-464 branch).
    """
    docs = "abcdefghij"
    max_allowed = 5

    # token_handler should not be invoked in this branch, but provide a deterministic stub
    def count_tokens_stub(s, force_accurate=False):
        pytest.fail("count_tokens should not be called in this branch")

    pd = _make_prhelpdocs_with_token_handler(count_tokens_stub)

    # Ensure get_settings is present but not relevant here
    monkeypatch.setattr(phm, "get_settings", lambda: SimpleNamespace(config=SimpleNamespace(model="irrelevant_model")))

    res = phm.PRHelpDocs._trim_docs_input(pd, docs, max_allowed, only_return_if_trim_needed=True)
    assert res is True


def test_trim_docs_input_length_trim_then_return_content_round_061(monkeypatch):
    """
    If input length >= max_allowed_txt_input and only_return_if_trim_needed is False,
    it should first slice the string to max_allowed_txt_input and then proceed.
    When token_count is well below threshold, it should return the sliced content.
    """
    docs = "0123456789"  # length 10
    max_allowed = 5

    # token_count small so it does not trigger the later trimming branch
    def count_tokens_stub(s, force_accurate=False):
        # Expect to get the sliced string of length 5 here
        assert len(s) == 5
        return 10

    pd = _make_prhelpdocs_with_token_handler(count_tokens_stub)

    # Provide a model that is not present in MAX_TOKENS to force get_max_tokens path
    monkeypatch.setattr(phm, "get_settings", lambda: SimpleNamespace(config=SimpleNamespace(model="nonexistent_model")))
    monkeypatch.setattr(phm, "get_max_tokens", lambda model: 10000)

    res = phm.PRHelpDocs._trim_docs_input(pd, docs, max_allowed, only_return_if_trim_needed=False)
    # Should be the sliced input
    assert res == docs[:max_allowed]
    assert len(res) == 5


def test_trim_docs_input_second_trim_only_return_round_061(monkeypatch):
    """
    When token_count exceeds the allowed threshold and only_return_if_trim_needed is True,
    the method should return True at the second check (line ~475-477 branch).
    """
    docs = "X" * 10000
    max_allowed = 20000  # avoid initial length-based slicing

    # token_count large to trigger > max_tokens_full - delta_output
    def count_tokens_stub(s, force_accurate=False):
        return 8000

    pd = _make_prhelpdocs_with_token_handler(count_tokens_stub)

    # Ensure model is present in MAX_TOKENS and provides a known max_tokens_full
    # Use monkeypatch.setitem to ensure determinism even if MAX_TOKENS contents vary
    monkeypatch.setitem(phm.MAX_TOKENS, "mymodel_round_061", 7000)
    monkeypatch.setattr(phm, "get_settings", lambda: SimpleNamespace(config=SimpleNamespace(model="mymodel_round_061")))

    res = phm.PRHelpDocs._trim_docs_input(pd, docs, max_allowed, only_return_if_trim_needed=True)
    assert res is True


def test_trim_docs_input_clean_and_clip_round_061(monkeypatch):
    """
    When token_count exceeds the threshold and only_return_if_trim_needed is False,
    the function should call clean_markdown_content and clip_tokens and return the clipped result.
    This validates branches around lines ~475-486.
    """
    docs = "LONGCONTENT" * 1000
    max_allowed = 20000

    def count_tokens_stub(s, force_accurate=False):
        return 9000

    pd = _make_prhelpdocs_with_token_handler(count_tokens_stub)

    # Set model to a known max token value via MAX_TOKENS
    monkeypatch.setitem(phm.MAX_TOKENS, "clipmodel_round_061", 7000)
    monkeypatch.setattr(phm, "get_settings", lambda: SimpleNamespace(config=SimpleNamespace(model="clipmodel_round_061")))

    # Replace clean_markdown_content and clip_tokens with deterministic stubs
    called = {}

    def fake_clean_markdown_content(s):
        called['clean'] = True
        # pretend it reduces content a bit
        return s.replace("LONGCONTENT", "LC")

    def fake_clip_tokens(s, max_tokens, num_input_tokens=None):
        called['clip'] = (max_tokens, num_input_tokens)
        # return a clearly identifiable clipped string
        return "CLIPPED_CONTENT_ROUND_061"

    monkeypatch.setattr(phm, "clean_markdown_content", fake_clean_markdown_content)
    monkeypatch.setattr(phm, "clip_tokens", fake_clip_tokens)

    res = phm.PRHelpDocs._trim_docs_input(pd, docs, max_allowed, only_return_if_trim_needed=False)
    assert called.get('clean', False) is True
    assert 'clip' in called
    # Should return whatever clip_tokens returned
    assert res == "CLIPPED_CONTENT_ROUND_061"


def test_trim_docs_input_count_tokens_raises_round_061(monkeypatch):
    """
    If token_handler.count_tokens raises an unexpected exception, it should be propagated (lines ~487-492).
    """
    docs = "abc"
    max_allowed = 10

    def count_tokens_stub(s, force_accurate=False):
        raise ValueError("token counting exploded")

    pd = _make_prhelpdocs_with_token_handler(count_tokens_stub)

    monkeypatch.setattr(phm, "get_settings", lambda: SimpleNamespace(config=SimpleNamespace(model="irrelevant")))

    with pytest.raises(ValueError, match="token counting exploded"):
        phm.PRHelpDocs._trim_docs_input(pd, docs, max_allowed, only_return_if_trim_needed=False)
