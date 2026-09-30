#!/usr/bin/env python3
"""Discover candidate public call routes from buggy-side Python source."""

from __future__ import annotations

import ast
import hashlib
import json
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from common.utils.python.paths import safe_project_path, safe_relative_path
from probe.python.input.call_bindings import CallBindings
from probe.python.input.module_contracts import explicit_all, module_names, read_module
from probe.python.models import TargetUnit

MAX_ROUTES_PER_TARGET = 4


@dataclass
class CallableRecord:
    record_id: str
    qualname: str
    local_name: str
    kind: str
    scope: str
    node: ast.AST
    start_line: int
    end_line: int
    entrypoints: list[dict[str, Any]] = field(default_factory=list)
    calls: set[str] = field(default_factory=set)


def public_target_routes(
    project_root: Path,
    units: list[TargetUnit],
    *,
    import_roots: tuple[str, ...] = (),
) -> dict[str, Any]:
    grouped: dict[str, list[TargetUnit]] = {}
    for unit in units:
        safe_relative_path(unit.filepath)
        filepath = unit.filepath
        grouped.setdefault(filepath, []).append(unit)

    targets = []
    for filepath, file_units in sorted(grouped.items()):
        path = safe_project_path(project_root, filepath)
        tree = read_module(path)[1] if path.exists() else None
        if tree is None:
            targets.extend(unreachable(unit) for unit in file_units)
            continue
        targets.extend(
            analyze_file(
                project_root,
                filepath,
                tree,
                file_units,
                import_roots=import_roots,
            )
        )
    return {
        "source": "buggy-side Python AST public reachability",
        "available": True,
        "targets": targets,
        "unreachable_target_unit_ids": [
            target["target_unit_id"]
            for target in targets
            if target["accessibility"] == "private_unreachable"
        ],
    }


def analyze_file(
    project_root: Path,
    filepath: str,
    tree: ast.Module,
    units: list[TargetUnit],
    *,
    import_roots: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    modules = module_names(filepath, import_roots=import_roots)
    if not modules:
        return [unreachable(unit) for unit in units]
    module = modules[0]
    records = collect_records(tree, module)
    by_id, callers, previous_callers = collect_call_edges(records, tree)
    result = []
    for unit in units:
        if unit.kind in {"file", "module"}:
            entrypoint = module_entrypoint(filepath, module, unit)
            result.append(
                {
                    "target_unit_id": unit.unit_id,
                    "accessibility": "public",
                    "entrypoints": [entrypoint],
                }
            )
            continue
        target = target_record(unit, records)
        if target is None:
            result.append(unreachable(unit))
            continue
        routes = routes_to_target(
            filepath, module, by_id, previous_callers, target, unit
        )
        if not routes:
            routes = inherited_routes_to_target(
                project_root,
                filepath,
                module,
                tree,
                target,
                unit,
            )
        # Preserve existing entrypoints before filling spare slots with new routes.
        if len(routes) < MAX_ROUTES_PER_TARGET:
            seen = {tuple(route["call_path"]) for route in routes}
            for route in routes_to_target(
                filepath, module, by_id, callers, target, unit
            ):
                if tuple(route["call_path"]) not in seen:
                    routes.append(route)
                    seen.add(tuple(route["call_path"]))
                if len(routes) == MAX_ROUTES_PER_TARGET:
                    break
        result.append(
            {
                "target_unit_id": unit.unit_id,
                "accessibility": (
                    "public"
                    if target.entrypoints
                    else "private_reachable"
                    if routes
                    else "private_unreachable"
                ),
                "entrypoints": routes,
            }
        )
    return result


def collect_records(tree: ast.Module, module: str) -> list[CallableRecord]:
    explicit = explicit_all(tree)
    records: list[CallableRecord] = []

    def add(
        node: ast.AST,
        *,
        qualname: str,
        kind: str,
        entrypoints: list[dict[str, Any]] | None = None,
    ) -> CallableRecord:
        record = CallableRecord(
            record_id=f"callable-{len(records) + 1:04d}",
            qualname=qualname,
            local_name=node.name,
            kind=kind,
            scope=qualname.rpartition(".")[0] or "<module>",
            node=node,
            start_line=node_start(node),
            end_line=int(getattr(node, "end_lineno", getattr(node, "lineno", 0)) or 0),
            entrypoints=entrypoints or [],
        )
        records.append(record)
        return record

    def public_name(name: str) -> bool:
        return not name.startswith("_") and (explicit is None or name in explicit)

    def public_method_name(name: str) -> bool:
        return not name.startswith("_") or (
            name.startswith("__") and name.endswith("__")
        )

    def entrypoints(symbol: str, members: list[str], invocation: str, public: bool):
        return (
            [
                {
                    "symbol": symbol,
                    "member_path": members,
                    "invocation_kind": invocation,
                    "module": module,
                }
            ]
            if public
            else []
        )

    def visit_nested(body: list[ast.stmt], parents: list[str]) -> None:
        for node in body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            add(
                node,
                qualname=".".join([*parents, node.name]),
                kind="nested_function",
            )
            visit_nested(node.body, [*parents, node.name])

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        is_class = isinstance(node, ast.ClassDef)
        public = public_name(node.name)
        add(
            node,
            qualname=node.name,
            kind="class" if is_class else "function",
            entrypoints=entrypoints(
                node.name,
                [],
                "constructor" if is_class else "function",
                public,
            ),
        )
        if not is_class:
            visit_nested(node.body, [node.name])
            continue
        for member in node.body:
            if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            add(
                member,
                qualname=f"{node.name}.{member.name}",
                kind="class_method",
                entrypoints=entrypoints(
                    node.name,
                    [] if member.name == "__init__" else [member.name],
                    method_invocation(member),
                    public and public_method_name(member.name),
                ),
            )
            visit_nested(member.body, [node.name, member.name])
    return records


def calls_in_scope(root: ast.AST) -> Iterator[ast.Call]:
    """Visit calls in AST order, excluding nested def/class declarations."""
    pending = [root]
    while pending:
        node = pending.pop()
        if node is not root and isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        if isinstance(node, ast.Call):
            yield node
        pending.extend(reversed(list(ast.iter_child_nodes(node))))


def collect_call_edges(
    records: list[CallableRecord],
    tree: ast.Module,
) -> tuple[dict[str, CallableRecord], dict[str, list[str]], dict[str, list[str]]]:
    """Index callers once per file, preserving source-order traversal."""
    bindings = CallBindings(tree)
    definitions = {record.node: record for record in records}
    names: dict[str, list[CallableRecord]] = {}
    for record in records:
        keys = {record.qualname, f"{record.scope}.{record.local_name}"}
        if record.scope == "<module>":
            keys.add(record.local_name)
        for key in keys:
            names.setdefault(key, []).append(record)
    callers: dict[str, list[str]] = {}
    previous_callers: dict[str, list[str]] = {}

    for record in records:
        record.calls.clear()
        previous_calls: set[str] = set()
        for node in calls_in_scope(record.node):
            previous = None
            for key in call_keys(node.func, record):
                candidates = [item for item in names.get(key, []) if item is not record]
                if len(candidates) == 1:
                    previous = candidates[0]
                    break
            target = (
                bindings.resolve(node, node.func.id)
                if isinstance(node.func, ast.Name)
                else bindings.member(node)
            )
            # A known local replacement is not the same-named function. Member
            # values remain candidates because instances can override class state.
            if isinstance(node.func, ast.Name) and isinstance(
                target, (ast.Lambda, ast.Constant)
            ):
                continue
            callee = definitions.get(target, previous)
            if callee is not None and callee is not record:
                record.calls.add(callee.record_id)
                if callee is previous:
                    previous_calls.add(callee.record_id)
        for callee in record.calls:
            callers.setdefault(callee, []).append(record.record_id)
        for callee in previous_calls:
            previous_callers.setdefault(callee, []).append(record.record_id)
    return {record.record_id: record for record in records}, callers, previous_callers


def call_keys(node: ast.expr, record: CallableRecord) -> list[str]:
    """List name-based candidates for unresolved calls."""
    if isinstance(node, ast.Name):
        return [f"{record.qualname}.{node.id}", f"{record.scope}.{node.id}", node.id]
    if not isinstance(node, ast.Attribute):
        return []
    if isinstance(node.value, ast.Name) and node.value.id in {"self", "cls"}:
        return [f"{record.scope}.{node.attr}", node.attr]
    if isinstance(node.value, ast.Name):
        return [f"{node.value.id}.{node.attr}", node.attr]
    return [node.attr]


def routes_to_target(
    filepath: str,
    module: str,
    by_id: dict[str, CallableRecord],
    callers: dict[str, list[str]],
    target: CallableRecord,
    unit: TargetUnit,
) -> list[dict[str, Any]]:
    queue = deque([(target.record_id, [target.record_id])])
    visited = {target.record_id}
    routes = []
    while queue and len(routes) < MAX_ROUTES_PER_TARGET:
        current_id, reverse_path = queue.popleft()
        current = by_id[current_id]
        for entrypoint in current.entrypoints:
            call_path = [by_id[item].qualname for item in reversed(reverse_path)]
            routes.append(
                route_payload(
                    filepath,
                    module,
                    unit,
                    current,
                    entrypoint,
                    call_path,
                    len(routes),
                )
            )
        for caller_id in callers.get(current_id, []):
            if caller_id not in visited:
                visited.add(caller_id)
                queue.append((caller_id, [*reverse_path, caller_id]))
    return routes


def inherited_routes_to_target(
    project_root: Path,
    filepath: str,
    module: str,
    tree: ast.Module,
    target: CallableRecord,
    unit: TargetUnit,
) -> list[dict[str, Any]]:
    """Find explicit inherited public methods that dispatch to an override."""

    subclass = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == target.scope
        ),
        None,
    )
    exported = explicit_all(tree)
    if (
        subclass is None
        or target.kind != "class_method"
        or subclass.name.startswith("_")
        or (exported is not None and subclass.name not in exported)
    ):
        return []

    overridden = {
        node.name
        for node in subclass.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    resolved_methods: set[str] = set()
    routes = []
    additional_routes = []
    for base in subclass.bases:
        base_class = resolve_base_class(
            project_root,
            filepath,
            module,
            tree,
            base,
        )
        if base_class is None:
            continue
        methods = [
            node
            for node in base_class.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        for method in methods:
            if method.name in resolved_methods:
                continue
            resolved_methods.add(method.name)
            if (
                method.name in overridden
                or (method.name != "__init__" and method.name.startswith("_"))
                or not directly_calls_instance_member(method, target.local_name)
            ):
                continue
            inherited = CallableRecord(
                record_id=f"inherited-{subclass.name}-{method.name}",
                qualname=f"{subclass.name}.{method.name}",
                local_name=method.name,
                kind="class_method",
                scope=subclass.name,
                node=method,
                start_line=node_start(method),
                end_line=int(
                    getattr(method, "end_lineno", getattr(method, "lineno", 0)) or 0
                ),
            )
            destination = (
                routes
                if named_instance_call(method, target.local_name)
                else additional_routes
            )
            destination.append(
                route_payload(
                    filepath,
                    module,
                    unit,
                    inherited,
                    {
                        "symbol": subclass.name,
                        "member_path": []
                        if method.name == "__init__"
                        else [method.name],
                        "invocation_kind": method_invocation(method),
                    },
                    [inherited.qualname, target.qualname],
                    len(destination),
                )
            )
            if len(routes) >= MAX_ROUTES_PER_TARGET:
                return routes
    return (routes + additional_routes)[:MAX_ROUTES_PER_TARGET]


def resolve_base_class(
    project_root: Path,
    filepath: str,
    module: str,
    tree: ast.Module,
    base: ast.expr,
) -> ast.ClassDef | None:
    local_classes = {
        node.name: node for node in tree.body if isinstance(node, ast.ClassDef)
    }
    if isinstance(base, ast.Name) and base.id in local_classes:
        return local_classes[base.id]

    imported = imported_class(tree, module, base)
    if imported is None:
        return None
    imported_module, class_name = imported
    path = module_source_path(project_root, filepath, imported_module)
    if path is None:
        return None
    _, imported_tree = read_module(path)
    if imported_tree is None:
        return None
    return next(
        (
            node
            for node in imported_tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        ),
        None,
    )


def imported_class(
    tree: ast.Module,
    module: str,
    base: ast.expr,
) -> tuple[str, str] | None:
    if isinstance(base, ast.Name):
        for node in tree.body:
            if not isinstance(node, ast.ImportFrom):
                continue
            imported_module = absolute_import_module(module, node)
            for alias in node.names:
                if (alias.asname or alias.name) == base.id:
                    return imported_module, alias.name
        return None

    chain = attribute_chain(base)
    if len(chain) < 2:
        return None
    root, *members = chain
    for node in tree.body:
        if not isinstance(node, ast.Import):
            continue
        for alias in node.names:
            local = alias.asname or alias.name.split(".", 1)[0]
            if local != root:
                continue
            module_parts = alias.name.split(".")
            module_parts.extend(members[:-1])
            return ".".join(module_parts), members[-1]
    return None


def absolute_import_module(module: str, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    package = module.split(".")[:-1]
    ascend = node.level - 1
    if ascend > len(package):
        return ""
    prefix = package[: len(package) - ascend]
    if node.module:
        prefix.extend(node.module.split("."))
    return ".".join(prefix)


def module_source_path(
    project_root: Path,
    filepath: str,
    module: str,
) -> Path | None:
    if not module:
        return None
    module_parts = module.split(".")
    relative_module = Path(*module_parts)
    prefixes = [Path()]
    filepath_parts = Path(filepath).parts
    if module_parts[0] in filepath_parts[:-1]:
        package_index = filepath_parts.index(module_parts[0])
        prefixes.append(Path(*filepath_parts[:package_index]))

    seen: set[str] = set()
    for prefix in prefixes:
        for relative in (
            prefix / relative_module.with_suffix(".py"),
            prefix / relative_module / "__init__.py",
        ):
            value = str(relative)
            if value in seen:
                continue
            seen.add(value)
            path = safe_project_path(project_root, value)
            if path.is_file():
                return path
    return None


def attribute_chain(node: ast.expr) -> list[str]:
    parts = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return []
    return [current.id, *reversed(parts)]


def named_instance_call(
    method: ast.FunctionDef | ast.AsyncFunctionDef,
    member_name: str,
) -> bool:
    """Recognize calls to the named member through self or cls."""
    return any(
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in {"self", "cls"}
        and node.func.attr == member_name
        for node in calls_in_scope(method)
    )


def directly_calls_instance_member(
    method: ast.FunctionDef | ast.AsyncFunctionDef,
    member_name: str,
) -> bool:
    if named_instance_call(method, member_name):
        return True
    owner = ast.ClassDef(
        name="Owner", bases=[], keywords=[], body=[method], decorator_list=[]
    )
    bindings = CallBindings(ast.Module(body=[owner], type_ignores=[]))
    return any(
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and bindings.receivers.get(bindings.resolve(node, node.func.value.id)) is owner
        and node.func.attr == member_name
        for node in calls_in_scope(method)
    )


def route_payload(
    filepath: str,
    module: str,
    unit: TargetUnit,
    record: CallableRecord,
    entrypoint: dict[str, Any],
    call_path: list[str],
    index: int,
) -> dict[str, Any]:
    identity = json.dumps(
        [filepath, unit.unit_id, entrypoint, call_path, index],
        sort_keys=True,
    )
    return {
        "entrypoint_id": f"entrypoint-{hashlib.sha1(identity.encode()).hexdigest()[:12]}",
        "filepath": filepath,
        "module": module,
        "symbol": entrypoint["symbol"],
        "member_path": entrypoint["member_path"],
        "invocation_kind": entrypoint["invocation_kind"],
        "qualname": record.qualname,
        "call_path": call_path,
        "signature": callable_signature(record.node),
    }


def module_entrypoint(
    filepath: str,
    module: str,
    unit: TargetUnit,
) -> dict[str, Any]:
    identity = json.dumps([filepath, unit.unit_id, module], sort_keys=True)
    return {
        "entrypoint_id": f"entrypoint-{hashlib.sha1(identity.encode()).hexdigest()[:12]}",
        "filepath": filepath,
        "module": module,
        "symbol": "",
        "member_path": [],
        "invocation_kind": "module_import",
        "qualname": unit.qualname,
        "call_path": [unit.qualname],
        "signature": f"import {module}",
    }


def target_record(
    unit: TargetUnit, records: list[CallableRecord]
) -> CallableRecord | None:
    exact = next(
        (
            record
            for record in records
            if record.start_line == unit.start_line
            and record.end_line == unit.end_line
            and record.qualname == unit.qualname
        ),
        None,
    )
    if exact:
        return exact
    containing = [
        record
        for record in records
        if record.start_line <= unit.start_line and unit.end_line <= record.end_line
    ]
    return min(
        containing,
        key=lambda record: (record.end_line - record.start_line, record.start_line),
        default=None,
    )


def callable_signature(node: ast.AST) -> str:
    if isinstance(node, ast.ClassDef):
        init = next(
            (
                child
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and child.name == "__init__"
            ),
            None,
        )
        return f"class {node.name}({argument_signature(init.args) if init else ''})"
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        signature = f"{prefix} {node.name}({argument_signature(node.args)})"
        if node.returns is not None:
            signature += f" -> {ast.unparse(node.returns)}"
        return signature[:4000]
    return ""


def argument_signature(arguments: ast.arguments) -> str:
    rendered = ast.unparse(arguments)
    parts = rendered.split(", ")
    if parts and parts[0].split(":", 1)[0].strip() in {"self", "cls"}:
        rendered = ", ".join(parts[1:])
    return rendered


def method_invocation(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    if node.name == "__init__":
        return "constructor"
    for decorator, invocation in (
        ("staticmethod", "static_method"),
        ("classmethod", "class_method"),
    ):
        if has_decorator(node, decorator):
            return invocation
    return "instance_method"


def has_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    return any(
        (isinstance(decorator, ast.Name) and decorator.id == name)
        or (isinstance(decorator, ast.Attribute) and decorator.attr == name)
        for decorator in node.decorator_list
    )


def node_start(node: ast.AST) -> int:
    decorator_list = getattr(node, "decorator_list", [])
    return min(
        [
            int(getattr(node, "lineno", 0) or 0),
            *[int(item.lineno) for item in decorator_list],
        ]
    )


def unreachable(unit: TargetUnit) -> dict[str, Any]:
    return {
        "target_unit_id": unit.unit_id,
        "accessibility": "private_unreachable",
        "entrypoints": [],
    }
