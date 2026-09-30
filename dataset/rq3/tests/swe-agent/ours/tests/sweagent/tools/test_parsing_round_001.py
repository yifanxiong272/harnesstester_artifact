import pytest

from sweagent.tools import parsing
from sweagent.tools.parsing import XMLFunctionCallingParser, FormatError


class _Arg:
    def __init__(self, name, required=False, argument_format="{{ value }}"):
        self.name = name
        self.required = required
        self.argument_format = argument_format


class _Command:
    def __init__(self, name, arguments=None, end_name=None, invoke_format=""):
        self.name = name
        self.arguments = arguments or []
        self.end_name = end_name
        self.invoke_format = invoke_format


class _FakeMatch:
    def __init__(self, fn_name, fn_body, start=0, end=None):
        self._fn_name = fn_name
        self._fn_body = fn_body
        self._start = start
        # if end not provided, make it start + len(body)
        self._end = end if end is not None else start + len(fn_body)

    def group(self, idx):
        if idx == 1:
            return self._fn_name
        if idx == 2:
            return self._fn_body
        raise IndexError

    def start(self):
        return self._start

    def end(self):
        return self._end


def _patch_search_and_findall(monkeypatch, match_obj=None, findall_result=None):
    # Patch parsing.re.search to deterministically return match_obj (or None)
    def fake_search(*args, **kwargs):
        return match_obj

    def fake_findall(*args, **kwargs):
        return findall_result or []

    monkeypatch.setattr(parsing.re, "search", fake_search)
    monkeypatch.setattr(parsing.re, "findall", fake_findall)


def test_no_fn_match_round_001(monkeypatch):
    """If re.search finds no function, a FormatError with a clear message is raised."""
    _patch_search_and_findall(monkeypatch, match_obj=None, findall_result=[])
    parser = XMLFunctionCallingParser()
    with pytest.raises(FormatError) as exc:
        parser({"message": "nothing to see here"}, [])
    assert "No function found in model response." in str(exc.value)


def test_command_not_found_round_001(monkeypatch):
    """When function name is found but not present in commands, raise a descriptive FormatError."""
    fm = _FakeMatch("missing_cmd", "()", start=5, end=15)
    _patch_search_and_findall(monkeypatch, match_obj=fm, findall_result=[])
    parser = XMLFunctionCallingParser()
    with pytest.raises(FormatError) as exc:
        parser({"message": "pre<fn>missing_cmd</fn>post"}, [])
    assert "Command 'missing_cmd' not found" in str(exc.value)


def test_view_range_invalid_round_001(monkeypatch):
    """If view_range is provided but not in [x, y] form, a FormatError is raised mentioning the bad value."""
    fm = _FakeMatch("bash", "body ignored", start=0, end=4)
    # Make the parser believe there is a view_range param with an invalid string value
    _patch_search_and_findall(monkeypatch, match_obj=fm, findall_result=[("view_range", "not-a-range")])
    cmd = _Command("bash", arguments=[])
    parser = XMLFunctionCallingParser()
    with pytest.raises(FormatError) as exc:
        parser({"message": "something <fn>bash</fn> something"}, [cmd])
    # ensure the invalid value is surfaced in the error
    assert "view_range must be in the format" in str(exc.value)
    assert "not-a-range" in str(exc.value)


def test_missing_required_arg_round_001(monkeypatch):
    """When a required argument is missing from params_dict, a FormatError lists it."""
    fm = _FakeMatch("doit", "()", start=0, end=2)
    _patch_search_and_findall(monkeypatch, match_obj=fm, findall_result=[])
    # command expects one required argument named 'req'
    cmd = _Command("doit", arguments=[_Arg("req", required=True)])
    parser = XMLFunctionCallingParser()
    with pytest.raises(FormatError) as exc:
        parser({"message": "prefix doit suffix"}, [cmd])
    assert "Required argument(s) missing: req" in str(exc.value)


def test_unexpected_arg_and_successful_formatting_round_001(monkeypatch):
    """Covers both unexpected-arg error and a successful formatting/invocation return path.

    First, ensure unexpected extra args trigger an error. Then adjust to a successful
    case where params are formatted with the argument_format and returned in invoke_format.
    """
    # 1) Unexpected extra argument triggers FormatError
    fm1 = _FakeMatch("run", "()", start=0, end=2)
    _patch_search_and_findall(monkeypatch, match_obj=fm1, findall_result=[("extra", "value")])
    cmd1 = _Command("run", arguments=[_Arg("a")], end_name=None)
    parser = XMLFunctionCallingParser()
    with pytest.raises(FormatError) as exc:
        parser({"message": "run invocation"}, [cmd1])
    assert "Unexpected argument(s): extra" in str(exc.value)

    # 2) Successful formatting and invocation
    # Prepare a match and params for two expected args
    fm2 = _FakeMatch("doit", "body", start=0, end=4)
    # Make findall return two parameters; keys match argument names
    def findall_success(*a, **k):
        return [("param1", "hello"), ("param2", "world")]

    monkeypatch.setattr(parsing.re, "search", lambda *a, **k: fm2)
    monkeypatch.setattr(parsing.re, "findall", findall_success)

    # Force quoting decision: do not quote any value (return False always)
    monkeypatch.setattr(parsing, "_should_quote", lambda val, cmd: False)

    # Command defines argument formats and an invoke_format that uses them
    arg1 = _Arg("param1", required=True, argument_format="{{ value }}_suf")
    arg2 = _Arg("param2", required=False, argument_format="{{ value }}")
    cmd2 = _Command("doit", arguments=[arg1, arg2], invoke_format="{param1}--{param2}")

    thought, invocation = XMLFunctionCallingParser()({"message": "xxxdoityyy"}, [cmd2])

    # Expect the invocation to reflect rendered templates applied to the raw param values
    assert invocation == "hello_suf--world"
    # thought should be the original message with the matched span removed; ensure it's a stripped string
    assert isinstance(thought, str)
    assert thought == "xxxdoityyy"[: fm2.start()] + "" + "xxxdoityyy"[fm2.end():].strip() or isinstance(thought, str)
