# file: pr_agent/tools/pr_code_suggestions.py:648-668
# asked: {"lines": [650, 651, 652, 653, 654, 655, 656, 657, 658, 660, 661, 662, 663, 664, 665, 666, 667, 668], "branches": [[652, 653], [652, 665], [654, 655], [654, 664], [655, 654], [655, 656], [656, 657], [656, 658], [658, 654], [658, 660], [660, 654], [660, 661], [661, 660], [661, 662]]}
# gained: {"lines": [650, 651, 652, 653, 654, 655, 656, 657, 658, 660, 661, 662, 663, 664, 665, 666, 667, 668], "branches": [[652, 653], [652, 665], [654, 655], [654, 664], [655, 654], [655, 656], [656, 657], [656, 658], [658, 654], [658, 660], [660, 661], [661, 660], [661, 662]]}

import pytest

from pr_agent.tools import pr_code_suggestions as pcs_module
from pr_agent.tools.pr_code_suggestions import PRCodeSuggestions


def test_remove_line_numbers_transforms_lines():
    # Create instance without running __init__
    obj = PRCodeSuggestions.__new__(PRCodeSuggestions)
    # Prepare patches_diff_list with various cases:
    # - pure numeric line -> should become ''
    # - digits followed by a non-digit -> should strip leading digits and the first non-digit
    # - normal text -> should remain
    # - empty line -> should remain empty
    # - whitespace-only line -> should remain whitespace
    # - digits then letter then content
    input_str = "123\n123aHello\nnochange\n\n   \n45bX"
    obj.patches_diff_list = [input_str]

    result = obj.remove_line_numbers([])  # the parameter is ignored in implementation when no exception

    # Build expected result according to method logic:
    # splitlines -> ['123', '123aHello', 'nochange', '', '   ', '45bX']
    expected_lines = [
        "",         # '123' -> numeric -> ''
        "Hello",    # '123aHello' -> first non-digit at index 3 ('a'), j+1=4 -> 'Hello'
        "nochange", # unchanged
        "",         # empty line stays empty
        "   ",      # whitespace-only stays as-is
        "X",        # '45bX' -> first non-digit at index 2 ('b'), j+1=3 -> 'X'
    ]
    expected = ["\n".join(expected_lines)]
    assert result == expected
    # Also ensure the instance attribute was set accordingly
    assert hasattr(obj, "patches_diff_list_no_line_numbers")
    assert obj.patches_diff_list_no_line_numbers == expected


def test_remove_line_numbers_exception_path(monkeypatch):
    # Create instance without running __init__
    obj = PRCodeSuggestions.__new__(PRCodeSuggestions)
    # Set a value that will raise when .splitlines() is called (None has no splitlines)
    original_list = [None]
    obj.patches_diff_list = original_list.copy()

    # Replace get_logger in the module to capture the error call
    captured = {"msg": None}

    class DummyLogger:
        def error(self, msg):
            captured["msg"] = msg

    monkeypatch.setattr(pcs_module, "get_logger", lambda: DummyLogger())

    # Call with the same list as the parameter so that on exception the function returns it
    result = obj.remove_line_numbers(original_list)

    # On exception, the method should return the original patches_diff_list parameter
    assert result == original_list
    # And the logger error message should mention the operation
    assert captured["msg"] is not None
    assert "Error removing line numbers" in captured["msg"]
