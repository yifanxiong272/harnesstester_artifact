#!/usr/bin/env python3
"""Lexical, type, and call resolution for Python flow analysis."""

from __future__ import annotations

import ast

from .facts import FactStore
from .models import (
    CallTarget,
    ClassFieldRef,
    ClassKey,
    FunctionContext,
    FunctionInfo,
    FunctionKey,
    LocalRef,
    ModuleRef,
    NameEnv,
    ProjectIndex,
    ResolvedName,
    ScopeKey,
    ValueRef,
)


def expr_path(expr: ast.AST | None) -> str | None:
    """Convert simple read/write expressions to dotted paths.

    Supported shapes are intentionally basic: names, attributes, literal-key
    subscripts, dynamic subscripts via their base path, and call receivers.
    """

    if expr is None:
        return None
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        base = expr_path(expr.value)
        return f"{base}.{expr.attr}" if base else expr.attr
    if isinstance(expr, ast.Subscript):
        base = expr_path(expr.value)
        key = literal_string(expr.slice)
        if not base:
            return None
        return f"{base}.{key}" if key else base
    if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute):
        return expr_path(expr.func.value)
    return None


def literal_string(expr: ast.AST | None) -> str | None:
    """Return the value of a literal string AST node."""

    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    return None


def resolve_expr_name(expr: ast.AST, scope: ScopeKey, index: ProjectIndex) -> list[ResolvedName]:
    """Resolve a name or dotted attribute expression from `scope`."""

    path = expr_path(expr)
    if not path:
        return []
    parts = path.split(".")
    roots = resolve_name(parts[0], scope, index)
    if len(parts) == 1:
        return roots
    rest = parts[1:]
    out: list[ResolvedName] = []
    for root in roots:
        if root.kind == "external":
            full_name = ".".join([root.full_name, *rest])
            out.extend(resolve_full_project_name(full_name, index))
        elif root.kind == "class":
            out.append(
                ResolvedName(
                    kind="external",
                    full_name=".".join([root.class_key.module, root.class_key.qualname, *rest])
                    if root.class_key
                    else ".".join(rest),
                )
            )
        elif root.kind == "function":
            out.append(
                ResolvedName(
                    kind="external",
                    full_name=".".join([root.function.module, root.function.qualname, *rest])
                    if root.function
                    else ".".join(rest),
                )
            )
    return out


def resolve_full_project_name(full_name: str, index: ProjectIndex) -> list[ResolvedName]:
    """Resolve `module.attr` when `module` is part of the indexed project."""

    parts = full_name.split(".")
    for split in range(len(parts) - 1, 0, -1):
        module = ".".join(parts[:split])
        attr_parts = parts[split:]
        candidates = project_module_candidates(module, index)
        if not candidates:
            continue
        candidate = candidates[0]
        if len(attr_parts) == 1:
            resolved = resolve_imported_symbol(candidate, attr_parts[0], index)
            filtered = [
                item
                for item in resolved
                if not (item.kind == "external" and item.full_name == full_name)
            ]
            if filtered:
                return dedupe_resolved_names(filtered)
        break
    return [ResolvedName(kind="external", full_name=full_name)]


def resolve_name(name: str, scope: ScopeKey, index: ProjectIndex) -> list[ResolvedName]:
    """Resolve `name` using lexical scope lookup."""

    current: ScopeKey | None = scope
    while current is not None:
        env = index.scope_envs[current]
        results = scope_bindings(name, env, index)
        if results is not None:
            return results
        current = env.parent
    return []


def resolve_imported_symbol(
    module: str,
    name: str,
    index: ProjectIndex,
    seen: set[tuple[str, str]] | None = None,
) -> list[ResolvedName]:
    """Resolve an imported attribute through project modules and re-exports."""

    seen = seen or set()
    key = (module, name)
    if key in seen:
        return []
    seen.add(key)

    for candidate in project_module_candidates(module, index):
        module_scope = ScopeKey(candidate)
        env = index.scope_envs[module_scope]
        results = scope_bindings(name, env, index, seen)
        if results is not None:
            return results

    return [ResolvedName(kind="external", full_name=f"{module}.{name}")]


def scope_bindings(
    name: str,
    env: NameEnv,
    index: ProjectIndex,
    seen: set[tuple[str, str]] | None = None,
) -> list[ResolvedName] | None:
    """Resolve one scope's binding; None permits lookup in the parent scope."""

    results = [
        ResolvedName(
            kind="function", full_name=f"{key.module}.{key.qualname}", function=key
        )
        for key in sorted(env.local_functions.get(name, set()))
    ]
    results.extend(
        ResolvedName(
            kind="class", full_name=f"{key.module}.{key.qualname}", class_key=key
        )
        for key in sorted(env.local_classes.get(name, set()))
    )
    if results:
        return results
    if name in env.imported_attrs:
        imported_results = []
        for module, imported in sorted(env.imported_attrs[name]):
            imported_results.extend(
                resolve_imported_symbol(
                    module, imported, index, set(seen) if seen is not None else None
                )
            )
        return dedupe_resolved_names(imported_results)
    if name in env.imports:
        return [
            ResolvedName(kind="external", full_name=target)
            for target in sorted(env.imports[name])
        ]
    function = index.functions.get(FunctionKey(env.scope.module, env.scope.qualname))
    if function is not None and name in function.params:
        return []
    return None


def project_module_candidates(module: str, index: ProjectIndex) -> list[str]:
    """Return project module aliases, including common `src/` layout imports."""

    if ScopeKey(module) in index.scope_envs:
        return [module]
    src_module = f"src.{module}"
    if ScopeKey(src_module) in index.scope_envs:
        return [src_module]
    return []


def own_scope_names(scope: ScopeKey, index: ProjectIndex) -> set[str]:
    """Return names bound directly in one lexical scope."""

    env = index.scope_envs[scope]
    return (
        set(env.imports)
        | set(env.imported_attrs)
        | set(env.local_functions)
        | set(env.local_classes)
    )


def name_is_local_to_function(name: str, info: FunctionInfo, index: ProjectIndex) -> bool:
    """Return whether `name` should be read from the current function only."""

    return (
        name in info.params
        or name in info.assigned_names
        or name in own_scope_names(info.scope, index)
    )


def refs_for_read_expr(
    expr: ast.AST,
    ctx: FunctionContext,
    facts: FactStore,
    index: ProjectIndex,
    *,
    include_prefixes: bool = True,
) -> list[ValueRef]:
    """Return fact-table refs that may describe an expression read."""

    path = expr_path(expr)
    if not path:
        return []
    return refs_for_path(path, ctx, facts, index, include_prefixes=include_prefixes)


def refs_for_path(
    path: str,
    ctx: FunctionContext,
    facts: FactStore,
    index: ProjectIndex,
    *,
    include_prefixes: bool = True,
) -> list[ValueRef]:
    """Return fact refs for a dotted path in the current function context."""

    parts = path.split(".")
    paths = (
        [".".join(parts[:idx]) for idx in range(1, len(parts) + 1)]
        if include_prefixes
        else [path]
    )
    refs: list[ValueRef] = []
    seen: set[ValueRef] = set()
    for current_path in paths:
        for ref in direct_refs_for_path(current_path, ctx, index):
            if ref not in seen:
                refs.append(ref)
                seen.add(ref)
        split_parts = current_path.split(".")
        for idx in range(1, len(split_parts)):
            prefix = ".".join(split_parts[:idx])
            suffix = ".".join(split_parts[idx:])
            for class_key in classes_for_path(prefix, ctx, facts, index):
                ref = ClassFieldRef(class_key, suffix)
                if ref not in seen:
                    refs.append(ref)
                    seen.add(ref)
    return refs


def direct_refs_for_path(path: str, ctx: FunctionContext, index: ProjectIndex) -> list[ValueRef]:
    """Return local or direct `self`/`cls` refs for `path` without type chasing."""

    parts = path.split(".")
    root = parts[0]
    suffix = ".".join(parts[1:])
    info = ctx.info
    refs: list[ValueRef] = []
    if root in {"self", "cls"} and suffix and info.class_key:
        for class_key in [info.class_key, *sorted(transitive_bases(info.class_key, index))]:
            refs.append(ClassFieldRef(class_key, suffix))
        return refs

    refs.append(LocalRef(info.key, path))
    if not name_is_local_to_function(root, info, index):
        enclosing_has_binding = False
        for enclosing in reversed(info.enclosing_functions):
            refs.append(LocalRef(enclosing, path))
            enclosing_info = index.functions.get(enclosing)
            if enclosing_info is not None and name_is_local_to_function(
                root,
                enclosing_info,
                index,
            ):
                enclosing_has_binding = True
                break
        if not enclosing_has_binding:
            refs.append(ModuleRef(info.module, path))
    return refs


def imported_refs_for_path(path: str, scope: ScopeKey, index: ProjectIndex) -> list[ModuleRef]:
    """Return project-module refs reached through imported module attributes."""

    parts = path.split(".")
    root = parts[0]
    suffix = parts[1:]
    current: ScopeKey | None = scope
    while current is not None:
        env = index.scope_envs[current]
        refs: list[ModuleRef] = []
        for module, imported in sorted(env.imported_attrs.get(root, set())):
            refs.extend(imported_symbol_refs(module, imported, suffix, index))
        for target in sorted(env.imports.get(root, set())):
            if ScopeKey(target) in index.scope_envs and suffix:
                refs.append(ModuleRef(target, ".".join(suffix)))
        if refs:
            return refs
        if scope_bindings(root, env, index) is not None:
            return []
        current = env.parent
    return []


def imported_symbol_refs(
    module: str,
    name: str,
    suffix: list[str],
    index: ProjectIndex,
    seen: set[tuple[str, str]] | None = None,
) -> list[ModuleRef]:
    """Return source module refs for a possibly re-exported imported symbol."""

    seen = seen or set()
    key = (module, name)
    if key in seen:
        return []
    seen.add(key)

    module_scope = ScopeKey(module)
    if module_scope in index.scope_envs:
        env = index.scope_envs[module_scope]
        refs: list[ModuleRef] = []
        for imported_module, imported_name in sorted(env.imported_attrs.get(name, set())):
            refs.extend(
                imported_symbol_refs(
                    imported_module,
                    imported_name,
                    suffix,
                    index,
                    set(seen),
                )
            )
        if refs:
            return refs

    return [ModuleRef(module, ".".join([name, *suffix]))]


def classes_for_path(
    path: str,
    ctx: FunctionContext,
    facts: FactStore,
    index: ProjectIndex,
    memo: dict[str, set[ClassKey]] | None = None,
) -> set[ClassKey]:
    """Resolve known class types for a path, including class-field chains."""

    memo = memo if memo is not None else {}
    if path in memo:
        return set(memo[path])

    parts = path.split(".")
    out: set[ClassKey] = set()
    if path in {"self", "cls"} and ctx.info.class_key:
        out.add(ctx.info.class_key)
    for ref in direct_refs_for_path(path, ctx, index):
        out.update(facts.type_of(ref))
    for idx in range(1, len(parts)):
        prefix = ".".join(parts[:idx])
        suffix = ".".join(parts[idx:])
        for class_key in classes_for_path(prefix, ctx, facts, index, memo):
            out.update(facts.type_of(ClassFieldRef(class_key, suffix)))
    memo[path] = out
    return set(out)


def receiver_classes(
    expr: ast.AST,
    ctx: FunctionContext,
    facts: FactStore,
    index: ProjectIndex,
) -> set[ClassKey]:
    """Return known classes for a call receiver expression."""

    path = expr_path(expr)
    if not path:
        return set()
    return classes_for_path(path, ctx, facts, index)


def class_object_classes(
    expr: ast.AST,
    ctx: FunctionContext,
    facts: FactStore,
    index: ProjectIndex,
) -> set[ClassKey]:
    """Return project classes carried as class objects by an expression."""

    classes: set[ClassKey] = set()
    for ref in refs_for_read_expr(expr, ctx, facts, index, include_prefixes=False):
        classes.update(facts.constructor_of(ref))
    for resolved in resolve_expr_name(expr, ctx.info.scope, index):
        if resolved.class_key:
            classes.add(resolved.class_key)
    return classes


def target_refs(
    target: ast.AST,
    ctx: FunctionContext,
    facts: FactStore,
    index: ProjectIndex,
) -> list[ValueRef]:
    """Convert assignment targets into refs that should receive facts."""

    if isinstance(target, ast.Name):
        return [LocalRef(ctx.info.key, target.id)]
    if isinstance(target, (ast.Tuple, ast.List)):
        refs: list[ValueRef] = []
        for item in target.elts:
            refs.extend(target_refs(item, ctx, facts, index))
        return refs

    path = expr_path(target)
    if not path:
        return []
    return target_refs_for_path(path, ctx, facts, index)


def target_refs_for_path(
    path: str,
    ctx: FunctionContext,
    facts: FactStore,
    index: ProjectIndex,
) -> list[ValueRef]:
    """Convert one assignment target path into refs that should receive facts."""

    parts = path.split(".")
    if parts[0] in {"self", "cls"} and len(parts) > 1 and ctx.info.class_key:
        return [ClassFieldRef(ctx.info.class_key, ".".join(parts[1:]))]

    refs: list[ValueRef] = [LocalRef(ctx.info.key, path)]
    if len(parts) > 1:
        base = ".".join(parts[:-1])
        suffix = parts[-1]
        for class_key in classes_for_path(base, ctx, facts, index):
            refs.append(ClassFieldRef(class_key, suffix))
    return refs


def resolve_constructor(
    call: ast.Call,
    ctx: FunctionContext,
    facts: FactStore,
    index: ProjectIndex,
) -> set[ClassKey]:
    """Resolve statically known class construction for a call expression."""

    classes: set[ClassKey] = set()
    for ref in refs_for_read_expr(call.func, ctx, facts, index, include_prefixes=False):
        classes.update(facts.constructor_of(ref))
    for resolved in resolve_expr_name(call.func, ctx.info.scope, index):
        if resolved.class_key:
            classes.add(resolved.class_key)
    return classes


def resolve_call(
    call: ast.Call,
    ctx: FunctionContext,
    facts: FactStore,
    index: ProjectIndex,
    *,
    include_class_object_methods: bool = True,
) -> list[CallTarget]:
    """Resolve a call expression to project-local function targets."""

    targets: list[CallTarget] = []
    for ref in refs_for_read_expr(call.func, ctx, facts, index, include_prefixes=False):
        for alias in sorted(facts.alias_of(ref)):
            targets.append(CallTarget(alias))
        for class_key in sorted(facts.constructor_of(ref)):
            targets.extend(constructor_targets(class_key, index))
        for class_key in sorted(facts.type_of(ref)):
            targets.extend(callable_instance_targets(class_key, index))

    for resolved in resolve_expr_name(call.func, ctx.info.scope, index):
        if resolved.function:
            targets.append(CallTarget(resolved.function))
        if resolved.class_key:
            targets.extend(constructor_targets(resolved.class_key, index))

    if isinstance(call.func, ast.Attribute):
        attr = call.func.attr
        if include_class_object_methods:
            for class_key in sorted(class_object_classes(call.func.value, ctx, facts, index)):
                targets.extend(
                    method_targets(
                        class_key,
                        attr,
                        index,
                        receiver_kind="class",
                    )
                )
        for class_key in sorted(receiver_classes(call.func.value, ctx, facts, index)):
            targets.extend(
                method_targets(
                    class_key,
                    attr,
                    index,
                    receiver_kind="instance",
                )
            )

    return dedupe_call_targets(targets)


def callable_instance_targets(class_key: ClassKey, index: ProjectIndex) -> list[CallTarget]:
    """Return `__call__` targets for a known callable object instance."""

    return [
        CallTarget(target.key, positional_offset=1)
        for target in method_infos(class_key, "__call__", index)
    ]


def constructor_targets(class_key: ClassKey, index: ProjectIndex) -> list[CallTarget]:
    """Return `__init__` targets for class construction."""

    return [
        CallTarget(target.key, positional_offset=1)
        for target in method_infos(class_key, "__init__", index)
    ]


def method_targets(
    class_key: ClassKey,
    method_name: str,
    index: ProjectIndex,
    *,
    receiver_kind: str,
) -> list[CallTarget]:
    """Return method targets for a known receiver class."""

    return [
        CallTarget(target.key, positional_offset=method_positional_offset(target, receiver_kind))
        for target in method_infos(class_key, method_name, index)
        if receiver_kind != "class" or target.method_kind in {"class", "static"}
    ]


def method_positional_offset(info: FunctionInfo, receiver_kind: str) -> int:
    """Return how many formal parameters are supplied by the receiver."""

    if receiver_kind == "class":
        return 1 if info.method_kind == "class" else 0
    return 0 if info.method_kind == "static" else 1


def method_infos(
    class_key: ClassKey,
    method_name: str,
    index: ProjectIndex,
) -> list[FunctionInfo]:
    """Return possible method implementations for a class.

    Exact class methods, inherited base methods, and known subclass overrides
    are all included. This intentionally over-approximates dynamic dispatch so
    static flow does not miss calls through base-typed receivers.
    """

    keys: set[FunctionKey] = set(index.class_methods.get((class_key, method_name), set()))
    for base in transitive_bases(class_key, index):
        keys.update(index.class_methods.get((base, method_name), set()))
    for subclass in transitive_subclasses(class_key, index):
        keys.update(index.class_methods.get((subclass, method_name), set()))
    return [index.functions[key] for key in sorted(keys) if key in index.functions]


def transitive_bases(class_key: ClassKey, index: ProjectIndex) -> set[ClassKey]:
    """Return all known base classes for `class_key`."""

    out: set[ClassKey] = set()
    queue = list(index.class_bases.get(class_key, set()))
    while queue:
        item = queue.pop()
        if item in out:
            continue
        out.add(item)
        queue.extend(index.class_bases.get(item, set()))
    return out


def transitive_subclasses(class_key: ClassKey, index: ProjectIndex) -> set[ClassKey]:
    """Return all known subclasses for `class_key`."""

    out: set[ClassKey] = set()
    queue = list(index.class_subclasses.get(class_key, set()))
    while queue:
        item = queue.pop()
        if item in out:
            continue
        out.add(item)
        queue.extend(index.class_subclasses.get(item, set()))
    return out


def dedupe_call_targets(targets: list[CallTarget]) -> list[CallTarget]:
    """Deduplicate call targets while preserving resolver order."""

    out: list[CallTarget] = []
    seen: set[CallTarget] = set()
    for target in targets:
        if target in seen:
            continue
        seen.add(target)
        out.append(target)
    return out


def dedupe_resolved_names(items: list[ResolvedName]) -> list[ResolvedName]:
    """Deduplicate name-resolution candidates while preserving order."""

    out: list[ResolvedName] = []
    seen: set[tuple[str, str, FunctionKey | None, ClassKey | None]] = set()
    for item in items:
        key = (item.kind, item.full_name, item.function, item.class_key)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def full_names_for_expr(expr: ast.AST, ctx: FunctionContext, index: ProjectIndex) -> set[str]:
    """Return all resolved full names for provider-rule matching."""

    resolved = resolve_expr_name(expr, ctx.info.scope, index)
    return {item.full_name for item in resolved}
