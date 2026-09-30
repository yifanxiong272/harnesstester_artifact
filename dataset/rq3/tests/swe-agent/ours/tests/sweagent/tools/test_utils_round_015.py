from types import SimpleNamespace
from sweagent.tools.utils import get_signature


class Arg:
    def __init__(self, name, required):
        self.name = name
        self.required = required


def test_no_arguments_round_015():
    # cmd has no 'arguments' attribute -> signature should be just the name
    cmd = SimpleNamespace(name="mycmd")
    assert get_signature(cmd) == "mycmd"


def test_arguments_explicit_none_round_015():
    # 'arguments' present but explicitly None -> treated like no arguments
    cmd = SimpleNamespace(name="mycmd", arguments=None)
    # ensure attribute exists in __dict__ but is None
    assert "arguments" in cmd.__dict__ and cmd.arguments is None
    assert get_signature(cmd) == "mycmd"


def test_arguments_end_name_none_required_and_optional_round_015():
    # arguments present, end_name is None -> iterate all arguments
    a1 = Arg("required_param", True)
    a2 = Arg("optional_param", False)
    cmd = SimpleNamespace(name="run", arguments=[a1, a2], end_name=None)
    sig = get_signature(cmd)
    # expected: name then required param in <> then optional param in [<>]
    assert sig == "run <required_param> [<optional_param>]"


def test_arguments_with_end_name_mixed_round_015():
    # arguments present and end_name provided -> iterate all except last, last expected to be a mapping
    a1 = Arg("one", True)
    a2 = Arg("two", False)
    # last element is a mapping whose first key is used in output
    last_mapping = {"files": None}
    cmd = SimpleNamespace(name="cmdname", arguments=[a1, a2, last_mapping], end_name="TAIL")
    sig = get_signature(cmd)
    # expected composition: name, processed args (one required, one optional), newline, key of last mapping, newline, end_name
    assert sig == "cmdname <one> [<two>]\nfiles\nTAIL"
