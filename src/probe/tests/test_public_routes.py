"""Independent binding checks for the lightweight public-route analysis."""

import ast
import sys
from pathlib import Path
from textwrap import indent

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from probe.python.input.public_routes import (
    collect_call_edges,
    collect_records,
    directly_calls_instance_member,
    public_target_routes,
)
from probe.python.input.call_bindings import CallBindings
from probe.python.models import TargetUnit


def edges(source):
    tree = ast.parse(source)
    records = collect_records(tree, "subject")
    by_id, _, _ = collect_call_edges(records, tree)
    return {
        (record.qualname, by_id[callee].qualname)
        for record in records
        for callee in record.calls
    }


def resolved_edges(source):
    """Check definite bindings separately from retained, uncertain candidates."""
    tree = ast.parse(source)
    bindings = CallBindings(tree)
    names = {
        record.node: record.qualname for record in collect_records(tree, "subject")
    }
    result = set()
    for call, scope in bindings.calls.items():
        while scope.node not in names and scope.parent:
            scope = scope.parent
        target = (
            bindings.resolve(call, call.func.id)
            if isinstance(call.func, ast.Name)
            else bindings.member(call)
        )
        if scope.node in names and target in names:
            result.add((names[scope.node], names[target]))
    return result


@pytest.mark.parametrize(
    "definition",
    [
        "def run(_helper): return _helper()",
        "def run(*_helper): return _helper()",
        "def run(**_helper): return _helper()",
        "def run(*, _helper): return _helper()",
        "def run(_helper, /): return _helper()",
        "def run():\n    _helper = replacement\n    return _helper()",
        "def run():\n    result = _helper()\n    _helper = replacement",
        "def run():\n    import other as _helper\n    return _helper()",
        "def run():\n    from other import _helper\n    return _helper()",
        "def run():\n    for _helper in values:\n        _helper()",
        "def run():\n    with resource() as _helper:\n        _helper()",
        "def run():\n    try:\n        work()\n    except Error as _helper:\n        _helper()",
        "def run(value):\n    match value:\n        case {'handler': _helper}:\n            _helper()",
        "def run():\n    if (_helper := replacement):\n        _helper()",
        "def run():\n    del _helper\n    return _helper()",
        "def run():\n    _helper: object\n    return _helper()",
        "def run():\n    global _helper\n    _helper = replacement\n    return _helper()",
    ],
)
def test_local_bindings_do_not_resolve_to_same_named_global(definition):
    assert ("run", "_helper") not in resolved_edges(
        "def _helper(): return 1\n" + definition
    )


@pytest.mark.parametrize(
    "expression",
    ["other._helper()", "factory()._helper()", "self._helper()", "cls._helper()"],
)
def test_unknown_receivers_remain_uncertain_candidates(expression):
    source = f"def _helper(): return 1\ndef run(other): return {expression}"
    assert not resolved_edges(source)
    assert edges(source) == {("run", "_helper")}


@pytest.mark.parametrize(
    "binding", ["_helper = replacement", "from other import _helper", "del _helper"]
)
def test_module_rebinding_blocks_static_resolution(binding):
    assert ("run", "_helper") not in resolved_edges(
        f"def _helper(): return 1\n{binding}\ndef run(): return _helper()"
    )


def test_value_free_module_annotation_preserves_the_function():
    assert edges(
        "def _helper(): return 1\n_helper: object\ndef run(): return _helper()"
    ) == {("run", "_helper")}


def test_nested_scope_respects_outer_parameter_shadowing():
    assert not resolved_edges(
        "def _helper(): return 1\n"
        "def run(_helper):\n"
        "    def inner(): return _helper()\n"
        "    return inner()\n"
    ) - {("run", "run.inner")}


def test_method_bare_names_skip_the_class_namespace():
    graph = edges(
        "def _helper(): return 1\n"
        "class Agent:\n"
        "    def _helper(self): return 2\n"
        "    def run(self): return _helper()\n"
    )
    assert ("Agent.run", "_helper") in graph
    assert ("Agent.run", "Agent._helper") not in graph


@pytest.mark.parametrize("receiver", ["self", "cls", "instance"])
@pytest.mark.parametrize("decorator", ["", "@classmethod\n"])
def test_bound_method_receiver(receiver, decorator):
    source = "class Agent:\n" + indent(
        decorator + f"def run({receiver}): return {receiver}._helper()\n"
        "def _helper(self): return 1\n",
        "    ",
    )
    assert ("Agent.run", "Agent._helper") in edges(source)
    assert directly_calls_instance_member(ast.parse(source).body[0].body[0], "_helper")


@pytest.mark.parametrize(
    "method",
    [
        "@staticmethod\ndef run(self): return self._helper()",
        "def run(self, other): return other._helper()",
        "def run(self): return cls._helper()",
        "def run(self):\n    self = other\n    return self._helper()",
        "def run(self): return [self._helper() for self in others]",
        "def run(self): return lambda self: self._helper()",
        "def run(self): return (self._helper() for self in others)",
    ],
)
def test_unbound_or_shadowed_receivers_are_not_instance_dispatch(method):
    source = "class Agent:\n" + indent(
        method + "\ndef _helper(self): return 1\n", "    "
    )
    assert ("Agent.run", "Agent._helper") not in resolved_edges(source)


def test_comprehension_binding_is_local_to_the_comprehension():
    graph = resolved_edges(
        "def _helper(): return 1\n"
        "def shadowed(values): return [_helper() for _helper in values]\n"
        "def run(values):\n"
        "    [_helper() for _helper in values]\n"
        "    return _helper()\n"
        "def outer_iterable(): return [item for item in _helper()]\n"
    )
    assert graph == {("run", "_helper"), ("outer_iterable", "_helper")}


def test_callback_and_generator_candidates_keep_their_own_bindings():
    graph = resolved_edges(
        "def _helper(): return 1\n"
        "def callback(): return lambda: _helper()\n"
        "def shadowed(): return lambda _helper: _helper()\n"
        "def consumed(values): return sum(_helper() for value in values)\n"
        "def shadowed_generator(values): return sum(_helper() for _helper in values)\n"
    )
    assert graph == {("callback", "_helper"), ("consumed", "_helper")}


def test_known_class_receiver_and_shadowing():
    graph = resolved_edges(
        "class Agent:\n"
        "    @staticmethod\n"
        "    def _helper(): return 1\n"
        "def run(): return Agent._helper()\n"
        "def shadowed(Agent): return Agent._helper()\n"
    )
    assert graph == {("run", "Agent._helper")}


def test_direct_calls_and_nested_functions_remain_available():
    graph = edges(
        "def _helper(): return 1\n"
        "def run():\n"
        "    def inner(): return _helper()\n"
        "    return inner()\n"
        "class Agent:\n"
        "    def run(self):\n"
        "        def inner(): return self._helper()\n"
        "        return inner()\n"
        "    def _helper(self): return 1\n"
    )
    assert graph == {
        ("run", "run.inner"),
        ("run.inner", "_helper"),
        ("Agent.run", "Agent.run.inner"),
        ("Agent.run.inner", "Agent._helper"),
    }


@pytest.mark.parametrize(
    "method, reachable",
    [
        ("def run(self): return self._helper()", True),
        ("@classmethod\ndef run(cls): return cls._helper()", True),
        ("def run(instance): return instance._helper()", True),
        ("@staticmethod\ndef run(self): return self._helper()", True),
        ("def run(self, other): return other._helper()", False),
        ("def run(self):\n    self = other\n    return self._helper()", True),
    ],
)
def test_inherited_entrypoint_preserves_uncertain_formal_candidates(
    tmp_path, method, reachable
):
    source = (
        "class _Base:\n" + indent(method, "    ") + "\n"
        "class Agent(_Base):\n    def _helper(self): return 1\n"
    )
    (tmp_path / "subject.py").write_text(source)
    method_node = ast.parse(source).body[1].body[0]
    target = TargetUnit(
        unit_id="helper",
        filepath="subject.py",
        qualname="Agent._helper",
        kind="function",
        start_line=method_node.lineno,
        end_line=method_node.end_lineno,
        selection_source="fixture",
    )
    result = public_target_routes(tmp_path, [target])["targets"][0]
    assert bool(result["entrypoints"]) is reachable
    assert result["accessibility"] == (
        "private_reachable" if reachable else "private_unreachable"
    )
    if reachable:
        assert result["entrypoints"][0]["call_path"] == ["Agent.run", "Agent._helper"]


@pytest.mark.parametrize(
    "source, expected_edge",
    [
        (
            "def _helper(): return 1\n"
            "def run():\n    global _helper\n    return _helper()\n",
            ("run", "_helper"),
        ),
        (
            "def run():\n"
            "    def _helper(): return 1\n"
            "    def inner():\n        nonlocal _helper\n        return _helper()\n"
            "    return inner()\n",
            ("run.inner", "run._helper"),
        ),
        (
            "class Agent:\n"
            "    def _helper(self): return 1\n"
            "    def step(self):\n"
            "        result = self._helper()\n        self = None\n        return result\n"
            "def run(): return Agent().step()\n",
            ("Agent.step", "Agent._helper"),
        ),
        (
            "def _helper(): return 1\n"
            "def public_entry(_helper): return _helper()\n"
            "def run(): return public_entry(_helper)\n",
            ("public_entry", "_helper"),
        ),
    ],
)
def test_runtime_witnessed_formal_calls_are_retained(source, expected_edge):
    namespace = {}
    exec(compile(source, "<route-retention-test>", "exec"), namespace)
    assert namespace["run"]() == 1
    assert expected_edge in edges(source)


@pytest.mark.parametrize(
    "body",
    [
        "_helper = lambda: 2\nreturn _helper()",
        "_helper: object = lambda: 2\nreturn _helper()",
        "(_helper := lambda: 2)\nreturn _helper()",
        "other = lambda: 2\n_helper = other\nreturn _helper()",
        "other = _helper = lambda: 2\nreturn _helper()",
    ],
)
def test_local_callable_replacement_does_not_keep_a_wrong_formal_edge(body):
    source = (
        "hits = []\ndef _helper():\n    hits.append('target')\n    return 1\n"
        "def run():\n" + indent(body, "    ") + "\n"
    )
    namespace = {}
    exec(compile(source, "<binding-test>", "exec"), namespace)
    assert namespace["run"]() == 2
    assert namespace["hits"] == []
    assert ("run", "_helper") not in edges(source)


@pytest.mark.parametrize("value", ["None", "False", "0", "'text'"])
def test_known_noncallable_binding_does_not_fall_back_to_a_function(value):
    source = (
        "hits = []\ndef _helper(): hits.append('target')\n"
        f"def run():\n    _helper = {value}\n    return _helper()\n"
    )
    namespace = {}
    exec(compile(source, "<binding-test>", "exec"), namespace)
    with pytest.raises(TypeError):
        namespace["run"]()
    assert namespace["hits"] == []
    assert ("run", "_helper") not in edges(source)


@pytest.mark.parametrize(
    "source",
    [
        "def _helper(): return 1\ndef run():\n    alias = _helper\n    return alias()\n",
        "def _helper(): return 1\nalias = _helper\n"
        "def run():\n    _helper = lambda: alias()\n    return _helper()\n",
        "def _helper(): return 1\ndef run():\n"
        "    alias = _helper\n    second = alias\n    return second()\n",
        "class Agent:\n    def _helper(self): return 1\n"
        "    def step(self):\n        alias = self\n        return alias._helper()\n"
        "def run(): return Agent().step()\n",
    ],
)
def test_simple_aliases_preserve_real_calls(source):
    namespace = {}
    exec(compile(source, "<binding-test>", "exec"), namespace)
    assert namespace["run"]() == 1
    expected = (
        ("Agent.step", "Agent._helper")
        if "class Agent" in source
        else ("run", "_helper")
    )
    assert expected in edges(source)


def test_alias_cycles_remain_unresolved():
    tree = ast.parse("first = second\nsecond = first\ndef run(): return first()\n")
    bindings = CallBindings(tree)
    call = next(node for node in ast.walk(tree) if isinstance(node, ast.Call))
    assert bindings.resolve(call, "first") is None


@pytest.mark.parametrize(
    "source, expected",
    [
        (
            "def _helper(): return 1\n"
            "other = lambda: 2\n"
            "def run(values):\n"
            "    [(_helper := other) for other in values]\n"
            "    return _helper()\n",
            ("run", "_helper"),
        ),
        (
            "def _helper(): return 1\n"
            "class Agent:\n"
            "    _helper = None\n"
            "    def __init__(self, callback): self._helper = callback\n"
            "    def step(self): return self._helper()\n"
            "def run(values): return Agent(values[0]).step()\n",
            ("Agent.step", "_helper"),
        ),
    ],
)
def test_runtime_values_keep_a_valid_candidate(source, expected):
    namespace = {}
    exec(compile(source, "<binding-test>", "exec"), namespace)
    assert namespace["run"]([namespace["_helper"]]) == 1
    assert expected in edges(source)


@pytest.mark.parametrize("declaration", ["", "global _helper\n"])
def test_conditional_rebinding_keeps_a_valid_candidate(declaration):
    parameters = "replace=False" if declaration else "_helper, replace=False"
    source = f"def _helper(): return 1\ndef run({parameters}):\n" + indent(
        declaration + "if replace:\n    _helper = lambda: 2\nreturn _helper()", "    "
    )
    namespace = {}
    exec(compile(source, "<binding-test>", "exec"), namespace)
    args = () if declaration else (namespace["_helper"],)
    assert namespace["run"](*args) == 1
    assert ("run", "_helper") in edges(source)


@pytest.mark.parametrize("existing_count", [2, 4])
def test_new_routes_do_not_displace_existing_entrypoints(tmp_path, existing_count):
    source = (
        "class Agent:\n"
        "    def newly_found(self):\n"
        "        def inner(): return self._helper()\n"
        "        return inner()\n"
        "    def _helper(self): return 1\n"
        "    def _bridge(self): return self._helper()\n"
        + "".join(
            f"    def entry_{index}(self): return self._bridge()\n"
            for index in range(existing_count)
        )
    )
    (tmp_path / "subject.py").write_text(source)
    method = ast.parse(source).body[0].body[1]
    target = TargetUnit(
        unit_id="helper",
        filepath="subject.py",
        qualname="Agent._helper",
        kind="function",
        start_line=method.lineno,
        end_line=method.end_lineno,
        selection_source="fixture",
    )
    routes = public_target_routes(tmp_path, [target])["targets"][0]["entrypoints"]
    assert [route["call_path"][0] for route in routes[:existing_count]] == [
        f"Agent.entry_{index}" for index in range(existing_count)
    ]
    assert len(routes) == min(4, existing_count + 1)
    if existing_count < 4:
        assert routes[-1]["call_path"][0] == "Agent.newly_found"


@pytest.mark.parametrize("existing_count", [2, 4])
def test_new_inherited_routes_keep_existing_entrypoint_priority(
    tmp_path, existing_count
):
    source = (
        "class _Base:\n"
        "    def newly_found(instance): return instance._helper()\n"
        + "".join(
            f"    def entry_{index}(self): return self._helper()\n"
            for index in range(existing_count)
        )
        + "class Agent(_Base):\n    def _helper(self): return 1\n"
    )
    (tmp_path / "subject.py").write_text(source)
    method = ast.parse(source).body[1].body[0]
    target = TargetUnit(
        unit_id="helper",
        filepath="subject.py",
        qualname="Agent._helper",
        kind="function",
        start_line=method.lineno,
        end_line=method.end_lineno,
        selection_source="fixture",
    )
    routes = public_target_routes(tmp_path, [target])["targets"][0]["entrypoints"]
    assert [route["call_path"][0] for route in routes[:existing_count]] == [
        f"Agent.entry_{index}" for index in range(existing_count)
    ]
    assert len(routes) == min(4, existing_count + 1)
