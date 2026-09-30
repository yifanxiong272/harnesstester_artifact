#!/usr/bin/env python3
"""Parse project files and index lexical scopes for name and call resolution."""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path
from typing import Any

from common.utils.python.paths import rel_path

from ..source_rules import PY_LIKE_EXTENSIONS
from .models import (
    ClassInfo,
    ClassKey,
    FunctionInfo,
    FunctionKey,
    NameEnv,
    ProjectIndex,
    ScopeKey,
)
from .resolver import expr_path, resolve_expr_name


def module_name_for_file(path: Path, project_root: Path) -> str:
    """Return the import module name for one project file.

    Package `__init__.py` files map to the package name.
    """

    rel = path.resolve().relative_to(project_root.resolve()).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def build_project_index(files: list[Path], project_root: Path) -> ProjectIndex:
    """Index modules, imports, lexical scopes, functions, and class inheritance.

    The index is reused across fixed-point iterations.
    """

    module_files: dict[str, Path] = {}
    module_is_package: dict[str, bool] = {}
    module_bodies: dict[str, list[ast.stmt]] = {}
    module_trees: dict[str, ast.Module] = {}
    scope_envs: dict[ScopeKey, NameEnv] = {}
    functions: dict[FunctionKey, FunctionInfo] = {}
    classes: dict[ClassKey, ClassInfo] = {}
    class_methods: dict[tuple[ClassKey, str], set[FunctionKey]] = defaultdict(set)

    for path in files:
        if path.suffix not in PY_LIKE_EXTENSIONS:
            continue
        module = module_name_for_file(path, project_root)
        module_files[module] = path
        module_is_package[module] = path.name == "__init__.py"
        module_trees[module] = ast.parse(path.read_text(encoding="utf-8"))
        module_bodies[module] = module_trees[module].body
        module_scope = ScopeKey(module)
        scope_envs[module_scope] = NameEnv(scope=module_scope, parent=None)

    for module, tree in module_trees.items():
        module_scope = ScopeKey(module)
        module_file = rel_path(module_files[module], project_root)
        scope_stack = [module_scope]
        qual_stack: list[str] = []
        class_stack: list[ClassKey] = []
        function_stack: list[FunctionKey] = []

        class Visitor(ast.NodeVisitor):
            """Index named scopes while preserving lexical parents."""

            def current_scope(self) -> ScopeKey:
                return scope_stack[-1]

            def current_env(self) -> NameEnv:
                return scope_envs[self.current_scope()]

            def visit_Import(self, node: ast.Import) -> Any:
                record_import_node(node, self.current_env(), module, module_is_package[module])

            def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
                record_import_node(node, self.current_env(), module, module_is_package[module])

            def visit_ClassDef(self, node: ast.ClassDef) -> Any:
                qualname = ".".join([*qual_stack, node.name])
                class_key = ClassKey(module=module, qualname=qualname)
                class_scope = ScopeKey(module=module, qualname=qualname)
                parent_scope = self.current_scope()

                self.current_env().local_classes.setdefault(node.name, set()).add(class_key)
                scope_envs[class_scope] = NameEnv(scope=class_scope, parent=parent_scope)
                classes[class_key] = ClassInfo(
                    key=class_key,
                    file=module_file,
                    module=module,
                    qualname=qualname,
                    name=node.name,
                    scope=class_scope,
                    parent_scope=parent_scope,
                    node=node,
                )

                qual_stack.append(node.name)
                class_stack.append(class_key)
                scope_stack.append(class_scope)
                self.generic_visit(node)
                scope_stack.pop()
                class_stack.pop()
                qual_stack.pop()

            def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
                self._visit_function(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
                self._visit_function(node)

            def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
                qualname = ".".join([*qual_stack, node.name])
                function_key = FunctionKey(module=module, qualname=qualname)
                function_scope = ScopeKey(module=module, qualname=qualname)
                parent_scope = self.current_scope()

                self.current_env().local_functions.setdefault(node.name, set()).add(function_key)
                scope_envs[function_scope] = NameEnv(scope=function_scope, parent=parent_scope)
                functions[function_key] = FunctionInfo(
                    key=function_key,
                    file=module_file,
                    module=module,
                    qualname=qualname,
                    name=node.name,
                    scope=function_scope,
                    parent_scope=parent_scope,
                    node=node,
                    params=function_params(node),
                    assigned_names=assigned_names_in_function(node),
                    enclosing_functions=tuple(function_stack),
                    class_key=class_stack[-1] if class_stack else None,
                    method_kind=method_kind(node, bool(class_stack)),
                )
                if class_stack:
                    class_methods[(class_stack[-1], node.name)].add(function_key)

                qual_stack.append(node.name)
                function_stack.append(function_key)
                scope_stack.append(function_scope)
                self.generic_visit(node)
                scope_stack.pop()
                function_stack.pop()
                qual_stack.pop()

        Visitor().visit(tree)

    class_bases = build_class_bases(classes, scope_envs, functions)
    class_subclasses: dict[ClassKey, set[ClassKey]] = defaultdict(set)
    for class_key, bases in class_bases.items():
        for base in bases:
            class_subclasses[base].add(class_key)
    for class_key, bases in class_bases.items():
        classes[class_key].bases = tuple(sorted(bases))

    index = ProjectIndex(
        project_root=project_root,
        module_files=module_files,
        module_is_package=module_is_package,
        module_bodies=module_bodies,
        scope_envs=scope_envs,
        functions=functions,
        classes=classes,
        class_methods=class_methods,
        class_bases=class_bases,
        class_subclasses=class_subclasses,
    )
    for info in functions.values():
        info.param_types = parameter_types(info, index)
        info.return_types = return_types(info, index)
    return index


def record_import_node(
    node: ast.Import | ast.ImportFrom,
    env: NameEnv,
    current_module: str,
    current_is_package: bool,
) -> None:
    """Record one import statement in a lexical environment.

    Imports are path-insensitive: a binding may be used anywhere in its scope.
    """

    if isinstance(node, ast.Import):
        for alias in node.names:
            local = alias.asname or alias.name.split(".")[0]
            target = alias.name if alias.asname else alias.name.split(".")[0]
            env.imports.setdefault(local, set()).add(target)
        return

    module = absolute_import_module(
        current_module=current_module,
        current_is_package=current_is_package,
        level=node.level,
        module=node.module,
    )
    if not module:
        return
    for alias in node.names:
        # Star imports need __all__ and transitive export expansion; keep the
        # resolver tied to explicit bindings.
        if alias.name == "*":
            continue
        local = alias.asname or alias.name
        env.imported_attrs.setdefault(local, set()).add((module, alias.name))


def absolute_import_module(
    *,
    current_module: str,
    current_is_package: bool,
    level: int,
    module: str | None,
) -> str | None:
    """Resolve an `ImportFrom` module relative to the current package."""

    if level == 0:
        return module
    anchor = (
        current_module.split(".")
        if current_is_package
        else current_module.split(".")[:-1]
    )
    keep = len(anchor) - (level - 1)
    if keep < 0:
        return module
    parts = anchor[:keep]
    if module:
        parts.extend(module.split("."))
    return ".".join(parts) if parts else module


def function_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...]:
    """Return parameter names in the order used by call-argument mapping."""

    params = [
        arg.arg
        for arg in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        )
    ]
    if node.args.vararg:
        params.append(node.args.vararg.arg)
    if node.args.kwarg:
        params.append(node.args.kwarg.arg)
    return tuple(params)


def method_kind(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    in_class: bool,
) -> str:
    """Return how Python binds a method when reached through a class or instance."""

    if not in_class:
        return "function"
    decorators = {
        path.split(".")[-1]
        for decorator in node.decorator_list
        if (path := expr_path(decorator))
    }
    if "classmethod" in decorators:
        return "class"
    if "staticmethod" in decorators:
        return "static"
    return "instance"


def assigned_names_in_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    """Collect local names assigned inside one function.

    `build_project_index` stores this on `FunctionInfo`; resolver later uses it
    to distinguish local variable reads from closure reads.
    """

    names: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_Name(self, child: ast.Name) -> Any:
            if isinstance(child.ctx, ast.Store):
                names.add(child.id)

        def visit_FunctionDef(self, child: ast.FunctionDef) -> Any:
            if child is node:
                self.generic_visit(child)

        def visit_AsyncFunctionDef(self, child: ast.AsyncFunctionDef) -> Any:
            if child is node:
                self.generic_visit(child)

        def visit_ClassDef(self, child: ast.ClassDef) -> Any:
            return None

        def visit_Lambda(self, child: ast.Lambda) -> Any:
            return None

    for stmt in node.body:
        Visitor().visit(stmt)
    return frozenset(names)


def build_class_bases(
    classes: dict[ClassKey, ClassInfo],
    scope_envs: dict[ScopeKey, NameEnv],
    functions: dict[FunctionKey, FunctionInfo],
) -> dict[ClassKey, set[ClassKey]]:
    """Resolve base classes after all named classes have been indexed."""

    index_stub = ProjectIndex(
        project_root=Path("."),
        module_files={},
        module_is_package={},
        module_bodies={},
        scope_envs=scope_envs,
        functions=functions,
        classes=classes,
        class_methods={},
        class_bases={},
        class_subclasses={},
    )
    out: dict[ClassKey, set[ClassKey]] = defaultdict(set)
    for class_key, info in classes.items():
        for base in info.node.bases:
            for resolved in resolve_expr_name(base, info.parent_scope, index_stub):
                if resolved.class_key:
                    out[class_key].add(resolved.class_key)
    return out


def parameter_types(info: FunctionInfo, index: ProjectIndex) -> dict[str, set[ClassKey]]:
    """Resolve project-class annotations on function parameters."""

    args = [
        *info.node.args.posonlyargs,
        *info.node.args.args,
        *info.node.args.kwonlyargs,
    ]
    if info.node.args.vararg:
        args.append(info.node.args.vararg)
    if info.node.args.kwarg:
        args.append(info.node.args.kwarg)

    out: dict[str, set[ClassKey]] = {}
    for arg in args:
        if arg.annotation is None:
            continue
        classes = annotation_class_keys(arg.annotation, info.parent_scope, index)
        if classes:
            out[arg.arg] = classes
    return out


def return_types(info: FunctionInfo, index: ProjectIndex) -> set[ClassKey]:
    """Resolve project-class annotations on a function return type."""

    if info.node.returns is None:
        return set()
    return annotation_class_keys(info.node.returns, info.parent_scope, index)


def annotation_class_keys(
    annotation: ast.AST,
    scope: ScopeKey,
    index: ProjectIndex,
) -> set[ClassKey]:
    """Resolve project classes mentioned anywhere in a type annotation.

    This covers direct annotations (`LLM`), generics (`list[Action]`), unions
    (`LLM | None`), and string annotations from postponed annotation handling.
    """

    exprs = [annotation]
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        try:
            exprs.append(ast.parse(annotation.value, mode="eval").body)
        except SyntaxError:
            return set()

    classes: set[ClassKey] = set()
    for expr in exprs:
        for node in ast.walk(expr):
            if not isinstance(node, (ast.Name, ast.Attribute)):
                continue
            for resolved in resolve_expr_name(node, scope, index):
                if resolved.class_key is not None:
                    classes.add(resolved.class_key)
    return classes
