import pytest

from backend.report_type.detailed_report.detailed_report import DetailedReport

# Create instances without invoking __init__ because __init__ may require many args.
# _hashable_context does not use instance attributes, so this is safe.

def _make_report_instance():
    return object.__new__(DetailedReport)


def test_hashable_context_dict_full_round_105():
    dr = _make_report_instance()
    input_context = [
        {"title": "Report Title", "body": "Detailed body text."},
        {"content": "Only content provided."}
    ]

    result = dr._hashable_context(input_context)

    assert isinstance(result, list)
    # exact formatting asserted to cover conversion branch where dict has title and body
    assert result[0] == "Title: Report Title\nContent: Detailed body text."
    # dict missing title uses default; content used when body missing
    assert result[1] == "Title: No title\nContent: Only content provided."


def test_hashable_context_non_dicts_round_105():
    dr = _make_report_instance()
    input_context = ["a string", 123, None]

    result = dr._hashable_context(input_context)

    # Non-dict items should be converted via str()
    assert result == ["a string", "123", "None"]


def test_hashable_context_dict_missing_fields_round_105():
    dr = _make_report_instance()
    input_context = [{"other": "x"}]

    result = dr._hashable_context(input_context)

    # Missing title => 'No title'; missing body and content => empty string
    assert result == ["Title: No title\nContent: "]
