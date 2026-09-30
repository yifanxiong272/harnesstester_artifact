# file: sweagent/tools/commands.py:101-129
# asked: {"lines": [112, 113, 116, 117, 120, 128], "branches": [[110, 116], [127, 128]]}
# gained: {"lines": [112, 113, 116, 117, 120, 128], "branches": [[110, 116], [127, 128]]}

import pytest
from pydantic import ValidationError

from sweagent.tools.commands import Command, Argument


def test_invoke_format_signature_missing_arg_raises():
    # signature includes only <aa>, but arguments require 'aa' and 'bb' -> should raise ValidationError
    args = [
        Argument(name="aa", type="string", description="arg aa", required=True),
        Argument(name="bb", type="string", description="arg bb", required=False),
    ]
    # model validation runs validators which will call invoke_format and should raise a ValueError
    with pytest.raises(ValidationError) as exc:
        Command(name="cmd", docstring="d", signature="cmd <aa>", arguments=args)
    # The wrapped validation error should contain our underlying message
    assert "Missing arguments in signature" in str(exc.value)
    assert "cmd <aa>" in str(exc.value)


def test_invoke_format_signature_replacement_and_preserve_braces():
    # signature uses <aa>, [<bb>] and {cc}. Replacement should convert to {aa} {bb} and leave {cc}
    args = [
        Argument(name="aa", type="string", description="arg aa", required=True),
        Argument(name="bb", type="string", description="arg bb", required=False),
        Argument(name="cc", type="string", description="arg cc", required=False),
    ]
    signature = "cmd <aa> [<bb>] {cc}"
    cmd = Command(name="cmd", docstring="d", signature=signature, arguments=args)
    invoke = cmd.invoke_format
    # Expect angle-bracket forms converted to {name}, bracketed angle also converted, existing {cc} preserved
    assert invoke == "cmd {aa} {bb} {cc}"


def test_invoke_format_no_signature_builds_format():
    # No signature provided: should build "name {arg1} {arg2} " with trailing space per implementation
    args = [
        Argument(name="xx", type="string", description="arg xx", required=True),
        Argument(name="yy", type="string", description="arg yy", required=False),
    ]
    cmd = Command(name="mycmd", docstring=None, signature=None, arguments=args)
    invoke = cmd.invoke_format
    assert invoke == "mycmd {xx} {yy} "
