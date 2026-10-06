"""Run the formal Python analyzer beside artifact regression fixtures."""

import ast
import dataclasses
import importlib
import importlib.util
import os
from pathlib import Path
import runpy
import sys
from types import MethodType
from unittest.mock import patch


def reference():
    name = "lci_formal_python_flow"
    if name not in sys.modules:
        root = Path(os.environ["LDH_FORMAL_ROOT"]) / "src/common/llm_dependent/python"
        spec = importlib.util.spec_from_file_location(name, root / "__init__.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return importlib.import_module(f"{name}.flow.analysis")


def canonical(value):
    """Compare independently loaded dataclasses while retaining collection order."""
    if dataclasses.is_dataclass(value):
        return type(value).__name__, tuple(
            (field.name, canonical(getattr(value, field.name)))
            for field in dataclasses.fields(value)
        )
    if isinstance(value, dict):
        return tuple((canonical(key), canonical(item)) for key, item in value.items())
    if isinstance(value, (set, frozenset)):
        return frozenset(canonical(item) for item in value)
    if isinstance(value, (tuple, list)):
        return tuple(canonical(item) for item in value)
    if isinstance(value, ast.AST):
        return ast.dump(value, include_attributes=True)
    return value


def observed_run(analyzer, run):
    events = []
    for name in ("seed_module_body_facts", "seed_class_body_facts", "analyze_function"):
        operation = getattr(analyzer, name)

        def observed(*args, name=name, operation=operation):
            events.append(
                (
                    name,
                    tuple(canonical(arg.key) for arg in args),
                    analyzer.facts.version,
                )
            )
            return operation(*args)

        setattr(analyzer, name, observed)
    return run(analyzer), events


def compare_analysis(actual, run):
    formal = reference()
    # Supply the same file universe to the formal directory-based input boundary.
    with patch.object(formal, "scan_source_files", return_value=actual.files):
        expected = formal.FlowAnalyzer(actual.project_root, [], actual.project_label)
    # Compare the remaining engine under the corrected unpacking semantics.
    expected.callee_actual_infos = MethodType(type(actual).callee_actual_infos, expected)
    assert canonical(actual.index) == canonical(expected.index)
    actual_stats, actual_events = observed_run(actual, run)
    expected_stats, expected_events = observed_run(
        expected, formal.FlowAnalyzer.run_fixed_point
    )
    assert canonical(actual_stats) == canonical(expected_stats)
    assert actual_events == expected_events
    assert canonical(vars(actual.facts)) == canonical(vars(expected.facts))
    for mode in ("none", "direct", "recursive"):
        assert actual.build_payload(actual_stats, mode) == expected.build_payload(
            expected_stats, mode
        )
    return actual_stats


if __name__ == "__main__":
    from llm_dependent.python import flow
    from llm_dependent.python.flow import analysis

    def legacy_scope(function):
        def run(*, src_roots, **kwargs):
            return function(
                source_files=reference().scan_source_files(src_roots), **kwargs
            )

        return run

    # Formal fixtures supply directory roots; normalize only their input scope.
    flow.analyze_flow_project = legacy_scope(flow.analyze_flow_project)
    flow.analyze_flow_project_outputs = legacy_scope(flow.analyze_flow_project_outputs)

    # Existing formal fixtures import this package name; route them to the artifact.
    for name, module in list(sys.modules.items()):
        if name == "llm_dependent" or name.startswith("llm_dependent."):
            sys.modules[f"common.{name}"] = module
    original_run = analysis.FlowAnalyzer.run_fixed_point
    analysis.FlowAnalyzer.run_fixed_point = lambda self: compare_analysis(
        self, original_run
    )
    runpy.run_path(sys.argv[1], run_name="__main__")
