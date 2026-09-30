import pytest

from browser_use.agent.message_manager import service as svc


def test_last_message_with_good_break_and_truncated_rest_round_099(monkeypatch):
    """When is_last_message is True and there is a good break point, the first
    line should contain the part before the break and the second line should be
    indented and contain the truncated remainder.
    """
    # Arrange
    emoji = "🙂"
    terminal_width = 20  # content_width = 10
    # Compose content so rfind(' ', 0, content_width) returns index 8 (> 0.7*10 -> 7)
    first_part = "ABCDEFGH"  # length 8
    rest = "RESTOFVERYLONG"  # length 14 -> will be truncated to 10
    content = first_part + " " + rest

    # Patch emoji provider to be deterministic
    monkeypatch.setattr(svc, "_log_get_message_emoji", lambda message: emoji)

    # Act
    out = svc._log_format_message_line(message=None, content=content, is_last_message=True, terminal_width=terminal_width)

    # Assert
    expected_prefix = f"{emoji}[??? (TODO)]: "
    assert out[0] == expected_prefix + first_part
    # second line should be indented by 10 spaces and contain rest truncated to 10 chars
    assert out[1] == " " * 10 + rest[: terminal_width - 10]


def test_last_message_with_no_good_break_round_099(monkeypatch):
    """When is_last_message is True but there's no good break point in the
    allowed width, the first line is the truncated content and the remainder
    (if any) is placed on the indented second line untrimmed if short.
    """
    emoji = "🙂"
    terminal_width = 20  # content_width = 10
    # No spaces in the first 10 characters -> rfind will be -1
    # content[:10] == 'ABCDEFGHIJ', rest will be appended
    content = "ABCDEFGHIJK LATER"

    monkeypatch.setattr(svc, "_log_get_message_emoji", lambda message: emoji)

    out = svc._log_format_message_line(message=None, content=content, is_last_message=True, terminal_width=terminal_width)

    expected_prefix = f"{emoji}[??? (TODO)]: "
    assert out[0] == expected_prefix + content[: terminal_width - 10]
    # remainder should appear indented (no further truncation because it's short)
    assert out[1] == " " * 10 + content[terminal_width - 10 :]


def test_not_last_message_truncation_round_099(monkeypatch):
    """When is_last_message is False and content is too long, the content is
    truncated to content_width and returned as a single prefixed line.
    """
    emoji = "🙂"
    terminal_width = 20  # content_width = 10
    content = "12345678901"  # 11 chars -> truncated to 10

    monkeypatch.setattr(svc, "_log_get_message_emoji", lambda message: emoji)

    out = svc._log_format_message_line(message=None, content=content, is_last_message=False, terminal_width=terminal_width)

    expected_prefix = f"{emoji}[??? (TODO)]: "
    assert out == [expected_prefix + content[: terminal_width - 10]]


def test_exception_path_returns_fallback_round_099(monkeypatch):
    """If an exception occurs while formatting, the function should log a
    warning and return the fallback error line.
    """
    # Make the emoji resolver raise to exercise the except branch
    def raising_emoji(_):
        raise ValueError("boom")

    monkeypatch.setattr(svc, "_log_get_message_emoji", raising_emoji)

    out = svc._log_format_message_line(message=None, content="irrelevant", is_last_message=False, terminal_width=80)

    assert out == ["\u2753[   ?]: [Error formatting message]"]
