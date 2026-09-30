# file: sweagent/tools/utils.py:46-72
# asked: {"lines": [55, 56, 57, 58, 59, 60, 61, 63, 65, 66, 67, 68, 70, 71, 72], "branches": [[56, 57], [56, 72], [57, 58], [57, 65], [58, 59], [58, 72], [60, 61], [60, 63], [65, 66], [65, 71], [67, 68], [67, 70]]}
# gained: {"lines": [55, 56, 57, 58, 59, 60, 61, 63, 65, 66, 67, 68, 70, 71, 72], "branches": [[56, 57], [56, 72], [57, 58], [57, 65], [58, 59], [58, 72], [60, 61], [60, 63], [65, 66], [65, 71], [67, 68], [67, 70]]}

import pytest
from sweagent.tools.utils import get_signature


class _Arg:
    def __init__(self, name, required):
        self.name = name
        self.required = required


class _Cmd:
    def __init__(self, name, arguments=None, end_name=None):
        self.name = name
        # set attribute explicitly so it's present in __dict__ when desired
        self.arguments = arguments
        self.end_name = end_name


def test_get_signature_no_arguments_attribute():
    # No 'arguments' attribute at all -> should return just the name
    cmd = type("CmdNoArgs", (), {"name": "simple"})()
    # ensure __dict__ does not contain 'arguments'
    assert "arguments" not in cmd.__dict__
    assert get_signature(cmd) == "simple"

    # If 'arguments' exists but is None -> should also return just the name
    cmd2 = _Cmd("simple2", arguments=None)
    assert "arguments" in cmd2.__dict__
    assert cmd2.arguments is None
    assert get_signature(cmd2) == "simple2"


def test_get_signature_end_name_none_all_arguments_have_name_and_required():
    # end_name is None -> iterate over all arguments and format using .name and .required
    args = [_Arg("first", True), _Arg("second", False), _Arg("third", True)]
    cmd = _Cmd("do", arguments=args, end_name=None)
    sig = get_signature(cmd)
    # expected: name + " <first>" + " [<second>]" + " <third>"
    assert sig == "do <first> [<second>] <third>"


def test_get_signature_with_end_name_last_argument_is_dict_and_preceding_are_objs():
    # end_name provided -> iterate over all but last; last element is a dict whose first key is used
    arg1 = _Arg("x", True)
    arg2 = _Arg("y", False)
    last_dict = {"description": "details about trailing input"}
    cmd = _Cmd("run", arguments=[arg1, arg2, last_dict], end_name="END")
    sig = get_signature(cmd)
    # expected: "run <x> [<y>]\ndescription\nEND"
    assert sig == "run <x> [<y>]\ndescription\nEND"
