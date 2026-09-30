# file: sweagent/tools/utils.py:46-72
# asked: {"lines": [55, 56, 57, 58, 59, 60, 61, 63, 65, 66, 67, 68, 70, 71, 72], "branches": [[56, 57], [56, 72], [57, 58], [57, 65], [58, 59], [58, 72], [60, 61], [60, 63], [65, 66], [65, 71], [67, 68], [67, 70]]}
# gained: {"lines": [55, 56, 57, 58, 59, 60, 61, 63, 65, 66, 67, 68, 71, 72], "branches": [[56, 57], [56, 72], [57, 58], [57, 65], [58, 59], [58, 72], [60, 61], [60, 63], [65, 66], [65, 71], [67, 68]]}

import pytest
from sweagent.tools.utils import get_signature


class _ArgObj:
    def __init__(self, name, required):
        self.name = name
        self.required = required


class _Cmd:
    def __init__(self, name, arguments=None, end_name=None):
        self.name = name
        # ensure arguments is set in __dict__ even if None
        self.arguments = arguments
        self.end_name = end_name


def test_get_signature_without_end_name():
    # Prepare a command with two arguments: one required, one optional
    args = [_ArgObj("first", True), _ArgObj("second", False)]
    cmd = _Cmd("mycmd", arguments=args, end_name=None)

    sig = get_signature(cmd)

    # Expected: name followed by required and optional params
    assert sig == "mycmd <first> [<second>]", "Signature did not match expected formatting"


def test_get_signature_with_end_name():
    # Prepare a command where the last argument is a dict (used for end block)
    # First argument is a regular argument object (required)
    first_arg = _ArgObj("item", True)
    last_arg = {"extra": "description"}
    cmd = _Cmd("othercmd", arguments=[first_arg, last_arg], end_name="This is the end")

    sig = get_signature(cmd)

    # Expected:
    # - starts with name and the required first param
    # - then a newline, the key of the last argument dict, another newline, and the end_name
    expected = "othercmd <item>\nextra\nThis is the end"
    assert sig == expected, f"Unexpected signature for end_name case: {sig!r}"


def test_get_signature_with_arguments_none():
    # When arguments attribute exists but is None, signature should just be the name
    cmd = _Cmd("simple", arguments=None, end_name=None)

    sig = get_signature(cmd)

    assert sig == "simple", "When arguments is None, signature should equal command name"
