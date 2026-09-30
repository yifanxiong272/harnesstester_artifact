import pytest
from types import SimpleNamespace

from sweagent.tools.utils import get_signature


def _make_cmd(name, *, with_arguments=True, arguments=None, end_name=None):
    """Helper to construct a minimal cmd-like object.

    - If with_arguments is False, the 'arguments' attribute is omitted entirely (tests the
      "arguments" not in cmd.__dict__ path).
    - If with_arguments is True, the 'arguments' attribute is set to the provided value
      (which may be None or a list).
    - end_name is always set (may be None) to avoid AttributeError when accessed.
    """
    if with_arguments:
        return SimpleNamespace(name=name, arguments=arguments, end_name=end_name)
    else:
        # omit arguments attribute entirely
        return SimpleNamespace(name=name, end_name=end_name)


def test_no_arguments_round_017():
    """If the command object does not have an 'arguments' attribute, the name alone is returned."""
    cmd = _make_cmd("solo", with_arguments=False, end_name=None)
    sig = get_signature(cmd)
    assert isinstance(sig, str)
    assert sig == "solo"


def test_arguments_explicitly_none_round_017():
    """If cmd.arguments exists but is None, function should return just the name (skip argument handling)."""
    cmd = _make_cmd("nothing", with_arguments=True, arguments=None, end_name=None)
    sig = get_signature(cmd)
    assert sig == "nothing"


def test_arguments_no_endname_round_017():
    """When end_name is None, every argument contributes inline. Test both required and optional formatting."""
    args = [
        SimpleNamespace(name="a", required=True),
        SimpleNamespace(name="b", required=False),
    ]
    cmd = _make_cmd("do", with_arguments=True, arguments=args, end_name=None)
    sig = get_signature(cmd)
    # expected: start with name, then required param as " <a>", then optional as " [<b>]"
    assert sig == "do <a> [<b>]"


def test_arguments_with_endname_round_017():
    """When end_name is provided, iterate all but last argument and then append the final-key and end_name lines.

    The last argument is intentionally a dict so that list(last.keys())[0] is used by the implementation.
    """
    args = [
        SimpleNamespace(name="x", required=False),
        {"flag": None}
    ]
    cmd = _make_cmd("run", with_arguments=True, arguments=args, end_name="END")
    sig = get_signature(cmd)
    # expected: 'run' + optional x => ' [<x>]' then a newline, the key of the last dict ('flag'), newline, and 'END'
    assert sig == "run [<x>]\nflag\nEND"
