import pytest

from pr_agent.algo.utils import format_todo_items


class FakeLogger:
    def __init__(self):
        self.debug_calls = []

    def debug(self, msg):
        # store exact messages for assertion
        self.debug_calls.append(msg)


def test_format_todo_items_list_gfm_supported_round_066(monkeypatch):
    """
    Verify HTML list branch with truncation when gfm_supported is True.
    - Patch format_todo_item to return deterministic strings for each item.
    - Patch get_logger to capture debug messages.
    - Provide 7 items to trigger truncation to MAX_ITEMS (5).
    """
    fake_logger = FakeLogger()

    # Patch the logger factory used inside format_todo_items
    monkeypatch.setattr("pr_agent.algo.utils.get_logger", lambda: fake_logger)

    # Patch format_todo_item to a deterministic function
    def fake_format_todo_item(item, git_provider, gfm_supported):
        return f"FORMATTED_{item}"

    monkeypatch.setattr("pr_agent.algo.utils.format_todo_item", fake_format_todo_item)

    items = list(range(7))  # 7 > MAX_ITEMS(5) to trigger truncation
    result = format_todo_items(items, git_provider=None, gfm_supported=True)

    # HTML list should be produced and truncated to 5 items
    assert result.startswith("<ul>\n")
    assert result.endswith("</ul>\n")
    # Each displayed item is wrapped in <li>...</li> and there should be exactly 5
    assert result.count("<li>") == 5
    # The logger debug should have been called exactly once with the expected message
    assert fake_logger.debug_calls == ["Truncating todo items to 5 items"]


def test_format_todo_items_list_not_gfm_supported_round_066(monkeypatch):
    """
    Verify plain-text bullet list branch with truncation when gfm_supported is False.
    - Ensure items are prefixed with '- ' and truncation debug message is emitted.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr("pr_agent.algo.utils.get_logger", lambda: fake_logger)

    def fake_format_todo_item(item, git_provider, gfm_supported):
        return f"TXT_{item}"

    monkeypatch.setattr("pr_agent.algo.utils.format_todo_item", fake_format_todo_item)

    items = [f"a{i}" for i in range(6 + 1)]  # 7 items total
    result = format_todo_items(items, git_provider=None, gfm_supported=False)

    # Plain text bullets should be produced and truncated to 5
    lines = [l for l in result.splitlines() if l.strip()]
    # Expect 5 bullet lines
    assert sum(1 for l in lines if l.startswith("- ")) == 5
    # Ensure truncation debug called once with exact message
    assert fake_logger.debug_calls == ["Truncating todo items to 5 items"]


def test_format_todo_items_single_item_branches_round_066(monkeypatch):
    """
    Test single-item branches for both gfm_supported True (HTML paragraph)
    and False (plain bullet). Ensure no truncation log is emitted.
    """
    # Prepare separate loggers to assert none called
    fake_logger_html = FakeLogger()
    fake_logger_plain = FakeLogger()

    # HTML single
    monkeypatch.setattr("pr_agent.algo.utils.get_logger", lambda: fake_logger_html)

    def format_for_html(item, git_provider, gfm_supported):
        # Return a string that lets us assert correct wrapping
        return "SINGLE_HTML"

    monkeypatch.setattr("pr_agent.algo.utils.format_todo_item", format_for_html)

    out_html = format_todo_items("irrelevant_item", git_provider=None, gfm_supported=True)
    assert out_html == "<p>SINGLE_HTML</p>\n"
    assert fake_logger_html.debug_calls == []

    # Plain single
    monkeypatch.setattr("pr_agent.algo.utils.get_logger", lambda: fake_logger_plain)

    def format_for_plain(item, git_provider, gfm_supported):
        return "SINGLE_PLAIN"

    monkeypatch.setattr("pr_agent.algo.utils.format_todo_item", format_for_plain)

    out_plain = format_todo_items(12345, git_provider=None, gfm_supported=False)
    assert out_plain == "- SINGLE_PLAIN\n"
    assert fake_logger_plain.debug_calls == []
