"""Differential checks for shared scope bindings and static expression reads."""

import ast
from functools import partial
import importlib
import os
from types import SimpleNamespace

import pytest

from llm_dependent.python.flow import analysis, models, resolver
from python_reference import canonical, compare_analysis, reference

pytestmark = pytest.mark.skipif(
    not os.environ.get("LDH_FORMAL_ROOT"), reason="set LDH_FORMAL_ROOT"
)


@pytest.mark.parametrize("scope", ["module", "class"])
@pytest.mark.parametrize("target", [False, True])
@pytest.mark.parametrize(
    "expression",
    [
        "value",
        "value.nested.field",
        "value['field']",
        "value[index]",
        "value.call()",
        "(left, (right, agent.field))",
        "[left, right]",
        "1",
        "lambda: value",
        "value['']",
    ],
)
def test_static_refs_match_formal(scope, target, expression):
    formal = reference()
    original = formal.FlowAnalyzer.__new__(formal.FlowAnalyzer)
    expr = ast.parse(expression, mode="eval").body
    if scope == "module":
        factory = partial(models.ModuleRef, "agent")
        owner = "agent"
    else:
        factory = partial(models.ClassFieldRef, models.ClassKey("agent", "Agent"))
        owner = formal.ClassKey("agent", "Agent")
    method = f"{scope}_target_refs" if target else f"{scope}_read_refs_for_expr"
    expected = getattr(original, method)(expr, owner)
    assert canonical(analysis.static_refs(expr, factory, target=target)) == canonical(
        expected
    )


def binding_index(types):
    scope = types.ScopeKey
    function = types.FunctionKey
    klass = types.ClassKey
    env = types.NameEnv
    return SimpleNamespace(
        functions={},
        scope_envs={
            scope("main"): env(
                scope("main"), None, imports={"parent": {"external.parent"}}
            ),
            scope("main", "inner"): env(
                scope("main", "inner"),
                scope("main"),
                local_functions={"mixed": {function("b", "run"), function("a", "run")}},
                local_classes={"mixed": {klass("a", "Agent")}},
                imported_attrs={
                    "mixed": {("unused", "name")},
                    "empty": set(),
                    "alias": {("one", "item")},
                },
                imports={
                    "mixed": {"unused"},
                    "empty": {"hidden"},
                    "external": {"b.sdk", "a.sdk"},
                },
            ),
            scope("one"): env(
                scope("one"),
                None,
                imported_attrs={"item": {("two", "item"), ("leaf", "item")}},
            ),
            scope("two"): env(
                scope("two"),
                None,
                imported_attrs={"item": {("one", "item"), ("leaf", "item")}},
            ),
            scope("leaf"): env(
                scope("leaf"),
                None,
                local_functions={"item": {function("leaf", "item")}},
            ),
            scope("src.aliases"): env(
                scope("src.aliases"), None, imported_attrs={"item": {("one", "item")}}
            ),
        }
    )


@pytest.mark.parametrize(
    "name", ["mixed", "parent", "empty", "alias", "external", "missing"]
)
def test_lexical_binding_precedence_matches_formal(name):
    formal = reference()
    old = importlib.import_module(f"{formal.__package__}.resolver")
    old_models = importlib.import_module(f"{formal.__package__}.models")
    actual = resolver.resolve_name(
        name, models.ScopeKey("main", "inner"), binding_index(models)
    )
    expected = old.resolve_name(
        name, old_models.ScopeKey("main", "inner"), binding_index(old_models)
    )
    assert canonical(actual) == canonical(expected)


@pytest.mark.parametrize(
    "module,name",
    [
        ("main", "parent"),
        ("one", "item"),
        ("two", "item"),
        ("aliases", "item"),
        ("absent", "item"),
    ],
)
@pytest.mark.parametrize(
    "seen", [None, set(), {("one", "item")}, {("unrelated", "item")}]
)
def test_reexports_preserve_branch_local_cycle_tracking(module, name, seen):
    formal = reference()
    old = importlib.import_module(f"{formal.__package__}.resolver")
    old_models = importlib.import_module(f"{formal.__package__}.models")
    actual_seen = None if seen is None else set(seen)
    expected_seen = None if seen is None else set(seen)
    actual = resolver.resolve_imported_symbol(
        module, name, binding_index(models), actual_seen
    )
    expected = old.resolve_imported_symbol(
        module, name, binding_index(old_models), expected_seen
    )
    assert canonical(actual) == canonical(expected)
    assert actual_seen == expected_seen


@pytest.mark.parametrize("limit", [1, 2, 80])
def test_fixed_point_states_and_payloads_match_at_iteration_limits(
    tmp_path, monkeypatch, limit
):
    sources = {
        "provider.py": """from openai import OpenAI
client = OpenAI()
def request(text):
    return client.responses.create(input=text)
""",
        "agent.py": """from provider import request
alias = request
class Agent:
    invoke = alias
    nested = {'handler': invoke}
    def run(self, handler=invoke):
        answer = handler('test')
        if answer:
            return self.finish(answer)
    def finish(self, value):
        return value
def outer():
    worker = Agent()
    def inner():
        method = getattr(worker, 'run')
        return method()
    return inner()
""",
    }
    for file, source in sources.items():
        (tmp_path / file).write_text(source)
    monkeypatch.setattr(analysis, "MAX_ITERATIONS", limit)
    monkeypatch.setattr(reference(), "MAX_ITERATIONS", limit)
    analyzer = analysis.FlowAnalyzer(
        tmp_path, [tmp_path / name for name in sources], "fixture"
    )
    compare_analysis(analyzer, analysis.FlowAnalyzer.run_fixed_point)
