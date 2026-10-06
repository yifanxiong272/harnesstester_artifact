"""Unpacked arguments flow only into compatible, unbound parameters."""

import ast
from types import SimpleNamespace

import pytest

from llm_dependent.python.flow import analyze_flow_project_outputs
from llm_dependent.python.flow.analysis import FlowAnalyzer
from llm_dependent.python.flow.indexing import function_params
from llm_dependent.python.flow.models import CallTarget, ExprInfo, FunctionKey


def bindings(signature, invocation, offset=0):
    node = ast.parse(f"def target({signature}): pass").body[0]
    call = ast.parse(invocation, mode="eval").body
    key = FunctionKey("fixture", "target")
    analyzer = FlowAnalyzer.__new__(FlowAnalyzer)
    analyzer.index = SimpleNamespace(
        functions={key: SimpleNamespace(node=node, params=function_params(node))}
    )
    actuals = analyzer.callee_actual_infos(
        CallTarget(key, positional_offset=offset),
        ExprInfo(strings={"receiver"}),
        [ExprInfo(strings={f"arg{idx}"}) for idx in range(len(call.args))],
        [ExprInfo(strings={f"kw{idx}"}) for idx in range(len(call.keywords))],
        call,
    )
    return {
        name: set().union(*(item.strings for item in values))
        for name, values in actuals.items()
    }


@pytest.mark.parametrize(
    "signature,invocation,expected",
    [
        ("value, *, flag=False", "target(*values)", {"value": {"arg0"}}),
        (
            "value, *rest, flag=False, **options", "target(a, **values)",
            {"value": {"arg0"}, "flag": {"kw0"}, "options": {"kw0"}},
        ),
        (
            "value, flag=False, **options", "target(value=a, flag=b, **values)",
            {"value": {"kw0"}, "flag": {"kw1"}, "options": {"kw2"}},
        ),
        (
            "value, /, *, flag=False, **options", "target(a, **values)",
            {"value": {"arg0"}, "flag": {"kw0"}, "options": {"kw0"}},
        ),
        (
            "value, *rest, flag=False, **options", "target(a, *values)",
            {"value": {"arg0"}, "rest": {"arg1"}},
        ),
        (
            "a, b, *rest", "target(*values, b=last)",
            {"a": {"arg0"}, "b": {"kw0"}, "rest": {"arg0"}},
        ),
        (
            "a, b, c, **options", "target(first, **extra)",
            {"a": {"arg0"}, "b": {"kw0"}, "c": {"kw0"}, "options": {"kw0"}},
        ),
        ("*values, **options", "target(*left, **right)",
         {"values": {"arg0"}, "options": {"kw0"}}),
        ("a, b, c", "target(a, *left, *right)",
         {"a": {"arg0"}, "b": {"arg1", "arg2"}, "c": {"arg1", "arg2"}}),
        ("*values", "target(*left, *right)", {"values": {"arg0", "arg1"}}),
    ],
)
def test_unpacked_argument_channels(signature, invocation, expected):
    assert bindings(signature, invocation) == expected


@pytest.mark.parametrize("receiver", ["self", "cls"])
def test_unpacked_arguments_preserve_implicit_receiver(receiver):
    assert bindings(
        f"{receiver}, value, *, flag=False, **options", "target(a, **extra)", 1
    ) == {
        receiver: {"receiver"}, "value": {"arg0"},
        "flag": {"kw0"}, "options": {"kw0"},
    }


@pytest.mark.parametrize(
    "signature,invocation,expected",
    [
        ("mode, *values, flag=False", "target(*response)", {"mode", "values"}),
        ("mode, *values, flag=False", "target('fixed', *response)", {"values"}),
        ("mode, *, flag=False, **values", "target('fixed', flag=False, **response)", {"values"}),
        ("mode, *, flag=False, **values", "target(**response)", {"mode", "flag", "values"}),
        ("mode, /, *, flag=False, **values", "target('fixed', **response)", {"flag", "values"}),
    ],
)
def test_unpacked_taint_and_control_blocks(tmp_path, signature, invocation, expected):
    fields = ["mode", "values", "flag"]
    body = "\n".join(f"    if {name}:\n        print('branch-{name}')" for name in fields)
    source = (
        "from litellm import completion\n\n"
        f"def target({signature}):\n{body}\n\n"
        "def run():\n    response = completion(model='fixture', messages=[])\n"
        f"    {invocation}\n"
    )
    file = tmp_path / "subject.py"
    file.write_text(source)
    payload = analyze_flow_project_outputs(tmp_path, [file], "fixture", ("none",))["none"]
    assert payload["fixed_point"]["converged"]
    lines = {row["location"]["start_line"] for row in payload["data_dependence"]}
    for number, line in enumerate(source.splitlines(), 1):
        for name in fields:
            if line.strip() in {f"if {name}:", f"print('branch-{name}')"}:
                assert (number in lines) == (name in expected), (name, number)


def test_clean_actuals_still_bind_parameters(tmp_path):
    source = """from litellm import completion
def select(mode, **options):
    return mode
def run():
    response = completion(model='fixture', messages=[])
    clean = select('fixed', **response)
    print(clean)
    derived = select(response)
    print(derived)
"""
    file = tmp_path / "subject.py"
    file.write_text(source)
    payload = analyze_flow_project_outputs(tmp_path, [file], "fixture", ("none",))["none"]
    lines = {row["location"]["start_line"] for row in payload["data_dependence"]}
    assert 7 not in lines
    assert 9 in lines
