import pytest

from sweagent.tools.parsing import ThoughtActionParser, FormatError


def test_thought_action_parser_nested_round_129():
    # Build a message with a nested code block structure:
    # prefix + ```python\n<outer_content>```\n + suffix
    # outer_content itself contains an inner code block.
    prefix = "prefix_text\n"
    suffix = "\nsuffix_text"

    outer_content = (
        "outer_line1\n"
        "```bash\n"
        "inner_line\n"
        "```\n"
        "outer_line2\n"
    )

    message = prefix + "```python\n" + outer_content + "```\n" + suffix

    parser = ThoughtActionParser()

    thought, action = parser({"message": message}, [])

    # The parser should return the content of the selected (outer) code block as the action.
    assert action == outer_content
    # The parser's slicing behavior can remove a leading newline from the suffix
    # when concatenating; reflect that in the expected thought.
    expected_thought = prefix + suffix.lstrip("\n")
    assert thought == expected_thought


def test_thought_action_parser_no_action_round_129():
    parser = ThoughtActionParser()
    # Message without any triple-backtick blocks should raise FormatError
    with pytest.raises(FormatError) as exc:
        parser({"message": "there is no code block here"}, [])
    assert "No action found in model response." in str(exc.value)
