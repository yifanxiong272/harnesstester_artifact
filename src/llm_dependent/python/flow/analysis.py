#!/usr/bin/env python3
"""Fixed-point Python LLM-dependent flow analysis."""

from __future__ import annotations

import ast
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

from common.utils.python.paths import rel_path

from ..common import RegionSpan, normalize_span
from .facts import FactStore
from .models import (
    AnalysisStats,
    CallFact,
    CallTarget,
    ClassFieldRef,
    ClassKey,
    ControlCallFact,
    ControlDependenceRegion,
    ExprInfo,
    FunctionContext,
    FunctionInfo,
    FunctionKey,
    LocalRef,
    ModuleRef,
    ParamDep,
    ReturnRef,
    ScopeKey,
    ValueRef,
)
from .payload import build_payload
from .providers import (
    attr_proxy_kind,
    attr_proxy_provider,
    dynamic_import_module_kind,
    provider_callable_value_kind,
    provider_client_constructor_kind,
    provider_service_client_kind,
    provider_module_value_kind,
    provider_modules,
    provider_request_callable_from_path,
    provider_request_callable_kind,
    provider_request_call,
    provider_value_kind,
)
from .indexing import build_project_index
from .resolver import (
    expr_path,
    imported_refs_for_path,
    literal_string,
    method_infos,
    name_is_local_to_function,
    refs_for_path,
    refs_for_read_expr,
    resolve_call,
    resolve_constructor,
    resolve_expr_name,
    target_refs,
)


MAX_ITERATIONS = 80
CONTROL_MODES = {"none", "direct", "recursive"}


def static_refs(
    expr: ast.AST, make_ref: Callable[[str], ValueRef], *, target: bool = False
) -> list[ValueRef]:
    """Resolve module/class reads by prefix and assignment targets by exact path."""

    if target and isinstance(expr, (ast.Tuple, ast.List)):
        return [
            ref for item in expr.elts
            for ref in static_refs(item, make_ref, target=True)
        ]
    path = expr_path(expr)
    if not path:
        return []
    parts = path.split(".")
    paths = [path] if target else [".".join(parts[:i]) for i in range(1, len(parts) + 1)]
    return [make_ref(value) for value in paths]


def analyze_flow_project(
    project_root: Path,
    source_files: list[Path],
    project_label: str,
    control_mode: str = "none",
) -> dict[str, Any]:
    """Public common entry for Python source-rooted flow extraction."""

    return analyze_flow_project_outputs(
        project_root=project_root,
        source_files=source_files,
        project_label=project_label,
        control_modes=(control_mode,),
    )[control_mode]


def analyze_flow_project_outputs(
    project_root: Path,
    source_files: list[Path],
    project_label: str,
    control_modes: tuple[str, ...] = ("none",),
) -> dict[str, dict[str, Any]]:
    """Run analysis once and build payloads for the requested output modes."""

    analyzer = FlowAnalyzer(
        project_root=project_root,
        source_files=source_files,
        project_label=project_label,
    )
    stats = analyzer.run_fixed_point()
    return {
        mode: analyzer.build_payload(stats, mode)
        for mode in control_modes
    }


class FlowAnalyzer:
    """Run the source-rooted, interprocedural data-flow analysis."""

    def __init__(
        self,
        project_root: Path,
        source_files: list[Path],
        project_label: str,
    ) -> None:
        self.project_root = project_root
        self.project_label = project_label
        self.files = sorted(source_files)
        self.index = build_project_index(self.files, project_root)
        self.facts = FactStore()

    def build_payload(self, stats: AnalysisStats, control_mode: str) -> dict[str, Any]:
        """Serialize current facts using the requested control-dependence mode."""

        if control_mode not in CONTROL_MODES:
            raise ValueError(f"unknown control_mode: {control_mode}")
        control_regions = (
            None
            if control_mode == "none"
            else self.build_control_regions(control_mode)
        )
        return build_payload(
            self.project_label,
            self.facts,
            stats,
            control_regions=control_regions,
        )

    def run_fixed_point(self) -> AnalysisStats:
        """Scan every function until a full pass adds no facts."""

        iterations = 0
        converged = False
        for iteration in range(1, MAX_ITERATIONS + 1):
            iterations = iteration
            before = self.facts.version
            self.seed_module_body_facts()
            self.seed_class_body_facts()
            for info in sorted(
                self.index.functions.values(),
                key=lambda item: (item.file, item.qualname),
            ):
                self.analyze_function(info)
            if self.facts.version == before:
                converged = True
                break
        return AnalysisStats(
            converged=converged,
            iterations=iterations,
            max_iterations=MAX_ITERATIONS,
        )

    def seed_module_body_facts(self) -> None:
        """Seed simple module-level value facts."""

        for module, statements in self.index.module_bodies.items():
            self.seed_static_assignment_facts(
                statements,
                ScopeKey(module),
                partial(ModuleRef, module),
                lambda stmt, current_module=module: self.module_span(current_module, stmt),
            )

    def seed_class_body_facts(self) -> None:
        """Seed simple class-level assignment facts."""

        for class_info in self.index.classes.values():
            self.seed_static_assignment_facts(
                class_info.node.body,
                class_info.scope,
                partial(ClassFieldRef, class_info.key),
                lambda stmt, info=class_info: self.static_span(info.file, stmt),
            )

    def seed_static_assignment_facts(
        self,
        statements: list[ast.stmt],
        scope: ScopeKey,
        make_ref: Callable[[str], ValueRef],
        span_for_stmt: Callable[[ast.stmt], RegionSpan],
    ) -> None:
        """Seed reusable value facts from assignments in a non-function scope."""

        for stmt in statements:
            if not isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                continue
            value_info = self.eval_static_expr(
                stmt.value, scope, partial(static_refs, make_ref=make_ref)
            )
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            span = span_for_stmt(stmt)
            for target in targets:
                for ref in static_refs(target, make_ref, target=True):
                    self.add_info_to_ref(ref, value_info, span, taint=True)

    def eval_static_expr(
        self,
        expr: ast.AST | None,
        scope: ScopeKey,
        read_refs_for_expr: Callable[[ast.AST], list[ValueRef]],
    ) -> ExprInfo:
        """Evaluate a module/class-level expression for reusable value facts."""

        if expr is None or isinstance(expr, ast.Lambda):
            return ExprInfo()
        if isinstance(expr, (ast.DictComp, ast.GeneratorExp, ast.ListComp, ast.SetComp)):
            return self.eval_static_comprehension(expr, scope, read_refs_for_expr)

        info = ExprInfo()
        literal = literal_string(expr)
        if literal is not None:
            info.strings.add(literal)
        read_refs = read_refs_for_expr(expr)
        self.read_ref_facts(info, read_refs, include_strings=True)
        path = expr_path(expr)
        if path:
            for ref in read_refs:
                if getattr(ref, "path", None) == path:
                    info.constructors.update(self.facts.constructor_of(ref))

        resolved_expr = resolve_expr_name(expr, scope, self.index)
        for resolved in resolved_expr:
            if resolved.function:
                info.aliases.add(resolved.function)
            if resolved.class_key:
                info.types.add(resolved.class_key)
                info.constructors.add(resolved.class_key)
                info.providers.update(
                    self.class_attr_proxy_provider_kinds(resolved.class_key)
                )
        info.providers.update(
            provider_module_value_kind(item.full_name for item in resolved_expr)
        )
        info.providers.update(
            provider_callable_value_kind(item.full_name for item in resolved_expr)
        )

        if isinstance(expr, ast.Call):
            call_names = {
                item.full_name for item in resolve_expr_name(expr.func, scope, self.index)
            }
            if self.is_static_getattr_call(expr):
                base_info = self.eval_static_expr(
                    expr.args[0],
                    scope,
                    read_refs_for_expr,
                )
                info.origins.update(base_info.origins)
                literal_attr = literal_string(expr.args[1])
                if literal_attr:
                    info.providers.update(
                        provider_request_callable_kind(
                            base_info.providers,
                            literal_attr,
                        )
                    )
            if "functools.partial" in call_names and expr.args:
                partial_info = self.eval_static_expr(
                    expr.args[0],
                    scope,
                    read_refs_for_expr,
                )
                info.providers.update(partial_info.providers)
            for keyword in expr.keywords:
                info.merge(
                    self.eval_static_expr(
                        keyword.value,
                        scope,
                        read_refs_for_expr,
                    )
                )
            info.providers.update(dynamic_import_module_kind(expr, call_names))
            info.providers.update(provider_client_constructor_kind(call_names))
            info.providers.update(provider_service_client_kind(expr, call_names))
            for resolved in resolve_expr_name(expr.func, scope, self.index):
                if resolved.function:
                    info.merge(self.facts.info_of(ReturnRef(resolved.function)))
                if resolved.class_key:
                    info.types.add(resolved.class_key)
                    info.constructors.add(resolved.class_key)
                    info.providers.update(
                        self.class_attr_proxy_provider_kinds(resolved.class_key)
                    )

        if isinstance(expr, (ast.Name, ast.Attribute, ast.Subscript)):
            return info
        for child in ast.iter_child_nodes(expr):
            if isinstance(child, ast.expr):
                info.merge(self.eval_static_expr(child, scope, read_refs_for_expr))
        return info

    def eval_static_comprehension(
        self,
        expr: ast.DictComp | ast.GeneratorExp | ast.ListComp | ast.SetComp,
        scope: ScopeKey,
        read_refs_for_expr: Callable[[ast.AST], list[ValueRef]],
    ) -> ExprInfo:
        """Evaluate module/class-level comprehension facts conservatively."""

        info = ExprInfo()
        for generator in expr.generators:
            info.merge(self.eval_static_expr(generator.iter, scope, read_refs_for_expr))
            for condition in generator.ifs:
                info.merge(self.eval_static_expr(condition, scope, read_refs_for_expr))
        if isinstance(expr, ast.DictComp):
            info.merge(self.eval_static_expr(expr.key, scope, read_refs_for_expr))
            info.merge(self.eval_static_expr(expr.value, scope, read_refs_for_expr))
        else:
            info.merge(self.eval_static_expr(expr.elt, scope, read_refs_for_expr))
        return info

    def is_static_getattr_call(self, expr: ast.Call) -> bool:
        """Return true for an unqualified getattr call in static scopes."""

        return (
            isinstance(expr.func, ast.Name)
            and expr.func.id == "getattr"
            and len(expr.args) >= 2
        )

    def module_span(self, module: str, stmt: ast.stmt) -> RegionSpan:
        """Convert a module statement location to a span."""

        path = self.index.module_files[module]
        return self.static_span(rel_path(path, self.project_root), stmt)

    def static_span(self, file: str, stmt: ast.stmt) -> RegionSpan:
        """Convert a module or class statement location to a span."""

        return normalize_span(
            file,
            getattr(stmt, "lineno", 0),
            getattr(stmt, "end_lineno", getattr(stmt, "lineno", 0)),
            "statement",
        )

    def analyze_function(self, info: FunctionInfo) -> None:
        """Analyze one function body in its own lexical/function context."""

        for param, class_keys in info.param_types.items():
            self.facts.add_type(LocalRef(info.key, param), set(class_keys))
        for param in info.params:
            if info.class_key is not None and param in {"self", "cls"}:
                continue
            self.facts.add_param_dep(
                LocalRef(info.key, param),
                {ParamDep(info.key, param)},
            )
        self.facts.add_type(ReturnRef(info.key), set(info.return_types))
        self.seed_default_argument_facts(info)
        self.analyze_block(info.node.body, self.make_context(info))

    def seed_default_argument_facts(self, info: FunctionInfo) -> None:
        """Seed facts from Python default values into their formal parameters."""

        def read_refs(expr: ast.AST) -> list[ValueRef]:
            return self.definition_scope_read_refs(expr, info.parent_scope)

        for param, default in self.default_argument_pairs(info.node):
            default_info = self.eval_static_expr(
                default,
                info.parent_scope,
                read_refs,
            )
            if not self.has_value_facts(default_info):
                continue
            self.add_info_to_ref(
                LocalRef(info.key, param),
                default_info,
                self.default_argument_span(info, default),
                taint=True,
            )

    def default_argument_pairs(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[tuple[str, ast.AST]]:
        """Return default expressions aligned to parameter names."""

        positional = [*node.args.posonlyargs, *node.args.args]
        defaults = list(node.args.defaults)
        start = len(positional) - len(defaults)
        pairs = [
            (arg.arg, default)
            for arg, default in zip(positional[start:], defaults, strict=False)
        ]
        pairs.extend(
            (arg.arg, default)
            for arg, default in zip(
                node.args.kwonlyargs,
                node.args.kw_defaults,
                strict=False,
            )
            if default is not None
        )
        return pairs

    def definition_scope_read_refs(
        self,
        expr: ast.AST,
        scope: ScopeKey,
        seen: set[ScopeKey] | None = None,
    ) -> list[ValueRef]:
        """Return value refs visible while evaluating a definition-time value."""

        seen = seen if seen is not None else set()
        if scope in seen:
            return []
        seen.add(scope)

        if not scope.qualname:
            return static_refs(expr, partial(ModuleRef, scope.module))

        class_key = ClassKey(scope.module, scope.qualname)
        if class_key in self.index.classes:
            class_info = self.index.classes[class_key]
            refs = static_refs(expr, partial(ClassFieldRef, class_key))
            refs.extend(
                self.definition_scope_read_refs(expr, class_info.parent_scope, seen)
            )
            return list(dict.fromkeys(refs))

        function_key = FunctionKey(scope.module, scope.qualname)
        function_info = self.index.functions.get(function_key)
        if function_info is None:
            return []
        return refs_for_read_expr(
            expr,
            self.make_context(function_info),
            self.facts,
            self.index,
            include_prefixes=True,
        )

    def default_argument_span(
        self,
        info: FunctionInfo,
        expr: ast.AST,
    ) -> RegionSpan:
        """Return a stable span for facts produced by a default expression."""

        return normalize_span(
            info.file,
            getattr(expr, "lineno", getattr(info.node, "lineno", 0)),
            getattr(
                expr,
                "end_lineno",
                getattr(expr, "lineno", getattr(info.node, "lineno", 0)),
            ),
            "statement",
            qualname=info.qualname,
        )

    def make_context(
        self,
        info: FunctionInfo,
        control_origin: RegionSpan | None = None,
    ) -> FunctionContext:
        """Create the context object passed through statement analysis."""

        return FunctionContext(info=info, control_origin=control_origin)

    def analyze_block(self, statements: list[ast.stmt], ctx: FunctionContext) -> None:
        """Analyze a sequence of statements in source order."""

        for stmt in statements:
            self.analyze_stmt(stmt, ctx)

    def analyze_stmt(self, stmt: ast.stmt, ctx: FunctionContext) -> None:
        """Dispatch one statement.

        Nested named functions/classes are separate analysis units, so their
        bodies are skipped here and scanned through their own FunctionInfo.
        """

        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return

        span = self.mark_span(stmt, ctx)
        if ctx.control_origin is not None:
            self.facts.add_data_edge(span, {ctx.control_origin}, "control")

        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            self.handle_assignment(stmt, ctx, span)
        elif isinstance(stmt, ast.AugAssign):
            self.handle_aug_assignment(stmt, ctx, span)
        elif isinstance(stmt, ast.Return):
            self.handle_return(stmt, ctx, span)
        elif isinstance(stmt, ast.Expr):
            self.handle_expr_stmt(stmt, ctx, span)
        elif isinstance(stmt, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.Match)):
            self.handle_control_stmt(stmt, ctx, span)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            self.handle_with(stmt, ctx, span)
        elif isinstance(stmt, ast.Try):
            self.handle_try(stmt, ctx, span)
        elif isinstance(stmt, (ast.Assert, ast.Raise)):
            self.handle_assert_or_raise(stmt, ctx, span)
        else:
            # Fallback keeps simple expression reads inside uncommon statements
            # visible without modeling statement-specific semantics.
            for child in ast.iter_child_nodes(stmt):
                if isinstance(child, ast.expr):
                    self.eval_expr(child, ctx, span)

    def mark_span(self, stmt: ast.stmt, ctx: FunctionContext) -> RegionSpan:
        """Convert an AST statement location to the internal span type."""

        return normalize_span(
            ctx.info.file,
            getattr(stmt, "lineno", 0),
            getattr(stmt, "end_lineno", getattr(stmt, "lineno", 0)),
            "statement",
            qualname=ctx.info.qualname,
        )

    def eval_expr(
        self,
        expr: ast.AST | None,
        ctx: FunctionContext,
        span: RegionSpan,
    ) -> ExprInfo:
        """Read expression facts and recursively inspect child expressions."""

        if expr is None:
            return ExprInfo()
        if isinstance(expr, ast.Await):
            return self.value_result_info(expr.value, ctx, span)
        if isinstance(expr, ast.Call):
            return self.handle_call(expr, ctx, span)
        if isinstance(expr, (ast.DictComp, ast.GeneratorExp, ast.ListComp, ast.SetComp)):
            return self.handle_comprehension(expr, ctx, span)
        if isinstance(expr, ast.Lambda):
            return ExprInfo()

        info = ExprInfo()
        literal = literal_string(expr)
        if literal is not None:
            info.strings.add(literal)
        refs = refs_for_read_expr(
            expr,
            ctx,
            self.facts,
            self.index,
            include_prefixes=True,
        )
        self.read_ref_facts(info, refs, include_strings=True)
        path = expr_path(expr)
        if path:
            for ref in refs_for_path(
                path,
                ctx,
                self.facts,
                self.index,
                include_prefixes=False,
            ):
                info.constructors.update(self.facts.constructor_of(ref))
            for ref in imported_refs_for_path(path, ctx.info.scope, self.index):
                info.constructors.update(self.facts.constructor_of(ref))
        for resolved in resolve_expr_name(expr, ctx.info.scope, self.index):
            if resolved.function:
                info.aliases.add(resolved.function)
            if resolved.class_key:
                info.types.add(resolved.class_key)
                info.constructors.add(resolved.class_key)
        info.providers.update(provider_value_kind(expr, ctx, self.facts, self.index))

        if isinstance(expr, (ast.Name, ast.Attribute, ast.Subscript)):
            return info
        for child in ast.iter_child_nodes(expr):
            if isinstance(child, ast.expr):
                info.merge(self.eval_expr(child, ctx, span))
        return info

    def handle_assignment(
        self,
        stmt: ast.Assign | ast.AnnAssign,
        ctx: FunctionContext,
        span: RegionSpan,
    ) -> None:
        """Propagate facts from an assignment RHS to all assignment targets."""

        value_info = self.value_result_info(stmt.value, ctx, span)
        targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        for target in targets:
            target_info = value_info
            # Container slots carry values, not class-object registries.
            if isinstance(target, ast.Subscript):
                target_info = self.without_constructors(value_info)
            for ref in target_refs(target, ctx, self.facts, self.index):
                self.add_info_to_ref(ref, target_info, span, taint=True)

        if value_info.origins and not self.is_direct_source_only(value_info):
            self.facts.add_data_edge(span, value_info.origins, "assignment")

    def without_constructors(self, info: ExprInfo) -> ExprInfo:
        """Copy expression facts except class-object constructor capabilities."""

        return ExprInfo(
            origins=set(info.origins),
            param_origins=set(info.param_origins),
            direct_sources=set(info.direct_sources),
            providers=set(info.providers),
            types=set(info.types),
            aliases=set(info.aliases),
            param_deps=set(info.param_deps),
            strings=set(info.strings),
        )

    def handle_aug_assignment(
        self,
        stmt: ast.AugAssign,
        ctx: FunctionContext,
        span: RegionSpan,
    ) -> None:
        """Handle augmented assignment as read plus write to the same target."""

        target_info = self.eval_expr(stmt.target, ctx, span)
        value_info = self.value_result_info(stmt.value, ctx, span)
        origins = target_info.origins | value_info.origins
        param_origins = target_info.param_origins | value_info.param_origins
        for ref in target_refs(stmt.target, ctx, self.facts, self.index):
            info = ExprInfo(
                origins=origins,
                param_origins=param_origins,
                providers=target_info.providers | value_info.providers,
                types=target_info.types | value_info.types,
                constructors=target_info.constructors | value_info.constructors,
                param_deps=target_info.param_deps | value_info.param_deps,
                strings=target_info.strings | value_info.strings,
            )
            self.add_info_to_ref(ref, info, span, taint=True)
        self.facts.add_data_edge(span, origins, "assignment")

    def handle_return(self, stmt: ast.Return, ctx: FunctionContext, span: RegionSpan) -> None:
        """Record tainted, provider-backed, and typed function returns."""

        value_info = self.value_result_info(stmt.value, ctx, span)
        current_deps = self.current_param_deps(value_info, ctx.info.key)
        if value_info.origins and not self.is_param_only_value(value_info, current_deps):
            self.facts.add_return(ctx.info.key, {span})
        if current_deps and self.is_param_only_value(value_info, current_deps):
            self.facts.add_return_param_deps(ctx.info.key, current_deps, span)
        if value_info.origins:
            if not self.is_direct_source_only(value_info):
                self.facts.add_data_edge(span, value_info.origins, "return")
        self.facts.add_provider(ReturnRef(ctx.info.key), value_info.providers)
        self.facts.add_type(ReturnRef(ctx.info.key), value_info.types)
        self.facts.add_constructor(ReturnRef(ctx.info.key), value_info.constructors)
        self.facts.add_alias(ReturnRef(ctx.info.key), value_info.aliases)
        self.facts.add_string(ReturnRef(ctx.info.key), value_info.strings)

    def handle_expr_stmt(self, stmt: ast.Expr, ctx: FunctionContext, span: RegionSpan) -> None:
        """Handle a bare expression statement."""

        info = self.eval_expr(stmt.value, ctx, span)
        if info.origins and not self.is_direct_source_only(info):
            self.facts.add_data_edge(span, info.origins, "access")

    def handle_comprehension(
        self,
        expr: ast.DictComp | ast.GeneratorExp | ast.ListComp | ast.SetComp,
        ctx: FunctionContext,
        span: RegionSpan,
    ) -> ExprInfo:
        """Evaluate comprehension flows by binding each generator target."""

        result = ExprInfo()
        for generator in expr.generators:
            iter_info = self.value_result_info(generator.iter, ctx, span)
            result.merge(iter_info)
            for ref in target_refs(generator.target, ctx, self.facts, self.index):
                self.add_preserved_info_to_ref(ref, iter_info)
            for condition in generator.ifs:
                result.merge(self.eval_expr(condition, ctx, span))

        if isinstance(expr, ast.DictComp):
            result.merge(self.eval_expr(expr.key, ctx, span))
            result.merge(self.eval_expr(expr.value, ctx, span))
        else:
            result.merge(self.eval_expr(expr.elt, ctx, span))
        return result

    def add_info_to_ref(
        self,
        ref: ValueRef,
        info: ExprInfo,
        span: RegionSpan,
        *,
        taint: bool,
    ) -> None:
        """Copy expression facts onto one value ref."""

        self.facts.add_provider(ref, info.providers)
        self.facts.add_type(ref, info.types)
        self.facts.add_constructor(ref, info.constructors)
        self.facts.add_alias(ref, info.aliases)
        self.facts.add_param_dep(ref, info.param_deps)
        self.facts.add_string(ref, info.strings)
        if taint and info.origins:
            self.facts.add_taint(ref, {span})
            if self.is_param_only_value(info, info.param_deps):
                self.facts.add_param_taint(ref, {span})

    def add_preserved_info_to_ref(self, ref: ValueRef, info: ExprInfo) -> None:
        """Copy expression facts onto an expression-local binding."""

        self.facts.add_provider(ref, info.providers)
        self.facts.add_type(ref, info.types)
        self.facts.add_constructor(ref, info.constructors)
        self.facts.add_alias(ref, info.aliases)
        self.facts.add_param_dep(ref, info.param_deps)
        self.facts.add_string(ref, info.strings)
        self.facts.add_taint(ref, info.origins)
        self.facts.add_param_taint(ref, info.param_origins)

    def handle_call(
        self,
        call: ast.Call,
        ctx: FunctionContext,
        span: RegionSpan,
    ) -> ExprInfo:
        """Handle provider sources and project-local call propagation."""

        result = ExprInfo()
        source_providers = provider_request_call(call, ctx, self.facts, self.index)
        if source_providers:
            self.facts.add_source(span)
            result.origins.add(span)
            result.direct_sources.add(span)

        getattr_info = self.handle_getattr_call(call, ctx, span)
        if getattr_info is not None:
            result.merge(getattr_info)
            return result

        callback_info = self.handle_builtin_callback_call(call, ctx, span)
        if callback_info is not None:
            result.merge(callback_info)
            return result

        receiver_info = ExprInfo()
        if isinstance(call.func, ast.Attribute):
            receiver_info = self.eval_expr(call.func.value, ctx, span)
        arg_infos = [self.value_result_info(arg, ctx, span) for arg in call.args]
        kw_infos = [self.value_result_info(keyword.value, ctx, span) for keyword in call.keywords]
        input_origins = set(receiver_info.origins)
        for item in [*arg_infos, *kw_infos]:
            input_origins.update(item.origins)

        self.handle_container_mutation(call, ctx, span, input_origins)

        targets = resolve_call(
            call,
            ctx,
            self.facts,
            self.index,
            include_class_object_methods=True,
        )
        if source_providers:
            targets = self.expand_source_callable_targets(targets)
        if targets:
            if input_origins:
                self.facts.add_data_edge(span, input_origins, "caller")
            elif ctx.control_origin is not None:
                for target in targets:
                    self.facts.add_control_call(
                        ControlCallFact(
                            caller=ctx.info.key,
                            callee=target.key,
                            span=span,
                            control_span=ctx.control_origin,
                        )
                    )
            for target in targets:
                self.facts.add_call(CallFact(caller=ctx.info.key, callee=target.key, span=span))
                actual_infos = self.callee_actual_infos(
                    target,
                    receiver_info,
                    arg_infos,
                    kw_infos,
                    call,
                )
                self.seed_callee_arguments(
                    target,
                    actual_infos,
                    span,
                )
                if not source_providers:
                    result.merge(self.facts.info_of(ReturnRef(target.key)))
                    result.merge(
                        self.instantiate_return_param_deps(target, actual_infos)
                    )
        elif input_origins:
            self.facts.add_data_edge(span, input_origins, "access")
        if self.container_read_returns_taint(call) and receiver_info.origins:
            result.origins.add(span)
        if self.container_read_returns_taint(call):
            result.constructors.update(receiver_info.constructors)

        if not source_providers:
            result.providers.update(
                provider_value_kind(call, ctx, self.facts, self.index)
            )
            constructor_types = resolve_constructor(call, ctx, self.facts, self.index)
            result.types.update(constructor_types)
            for class_key in constructor_types:
                result.providers.update(self.class_attr_proxy_provider_kinds(class_key))
            if constructor_types and input_origins:
                # Constructed project objects often carry tainted inputs as payload.
                result.origins.add(span)
        return result

    def value_result_info(
        self,
        expr: ast.AST | None,
        ctx: FunctionContext,
        span: RegionSpan,
    ) -> ExprInfo:
        """Evaluate expression facts that are preserved by its produced value."""

        if expr is None:
            return ExprInfo()
        if isinstance(expr, ast.Await):
            return self.value_result_info(expr.value, ctx, span)
        info = self.eval_expr(expr, ctx, span)
        async_info = self.async_call_result_info(expr, ctx, span)
        if async_info is not None:
            info.merge(async_info)
            return info
        info.merge(self.preserved_call_result_info(expr, ctx, span))
        info.merge(self.external_call_result_info(expr, ctx, span))
        return info

    def async_call_result_info(
        self,
        expr: ast.AST | None,
        ctx: FunctionContext,
        span: RegionSpan,
    ) -> ExprInfo | None:
        """Return value facts for async calls that transparently return an awaitable."""

        if not isinstance(expr, ast.Call) or not expr.args:
            return None
        call_names = {
            item.full_name for item in resolve_expr_name(expr.func, ctx.info.scope, self.index)
        }
        if call_names & {"asyncio.wait_for", "asyncio.tasks.wait_for"}:
            return self.value_result_info(expr.args[0], ctx, span)
        return None

    def expand_source_callable_targets(self, targets: list[CallTarget]) -> list[CallTarget]:
        """Follow callable aliases returned by source-certified local wrappers."""

        out = list(targets)
        seen = set(out)
        for target in targets:
            for alias in sorted(self.facts.alias_of(ReturnRef(target.key))):
                candidate = CallTarget(alias)
                if candidate in seen:
                    continue
                out.append(candidate)
                seen.add(candidate)
        return out

    def handle_getattr_call(
        self,
        call: ast.Call,
        ctx: FunctionContext,
        span: RegionSpan,
    ) -> ExprInfo | None:
        """Handle literal and transparent dynamic attribute reads."""

        if self.builtin_call_name(call, ctx) != "getattr" or len(call.args) < 2:
            return None

        base_expr = call.args[0]
        attr_expr = call.args[1]
        base_info = self.value_result_info(base_expr, ctx, span)
        attr_info = self.value_result_info(attr_expr, ctx, span)

        result = ExprInfo(
            origins=set(base_info.origins) | set(attr_info.origins),
            param_origins=set(base_info.param_origins) | set(attr_info.param_origins),
            param_deps=set(base_info.param_deps) | set(attr_info.param_deps),
        )
        if len(call.args) >= 3:
            result.merge(self.value_result_info(call.args[2], ctx, span))

        literal_attr = literal_string(attr_expr)
        if literal_attr:
            base_path = expr_path(base_expr)
            if base_path:
                dynamic_path = f"{base_path}.{literal_attr}"
                result.merge(self.info_for_path(dynamic_path, ctx))
                result.providers.update(
                    provider_request_callable_from_path(
                        dynamic_path,
                        ctx,
                        self.facts,
                        self.index,
                    )
                )
            result.providers.update(
                provider_request_callable_kind(base_info.providers, literal_attr)
            )

        if self.is_getattr_forwarding_attr_param(attr_info, ctx):
            for module in provider_modules(base_info.providers):
                result.providers.add(attr_proxy_kind(module))

        if result.origins:
            self.facts.add_data_edge(span, result.origins, "access")
        return result

    def info_for_path(self, path: str, ctx: FunctionContext) -> ExprInfo:
        """Read facts for a synthetic dotted path in the current context."""

        info = ExprInfo()
        refs = refs_for_path(
            path,
            ctx,
            self.facts,
            self.index,
            include_prefixes=True,
        )
        self.read_ref_facts(info, refs)
        for ref in refs_for_path(
            path,
            ctx,
            self.facts,
            self.index,
            include_prefixes=False,
        ):
            info.constructors.update(self.facts.constructor_of(ref))
        for ref in imported_refs_for_path(path, ctx.info.scope, self.index):
            info.constructors.update(self.facts.constructor_of(ref))
        return info

    def read_ref_facts(
        self, info: ExprInfo, refs: list[ValueRef], *, include_strings: bool = False
    ) -> None:
        """Merge read facts; callers resolve exact-path constructors separately."""

        for ref in refs:
            info.origins.update(self.facts.taint_of(ref))
            info.param_origins.update(self.facts.param_taint_of(ref))
            info.providers.update(self.facts.provider_of(ref))
            info.types.update(self.facts.type_of(ref))
            info.aliases.update(self.facts.alias_of(ref))
            info.param_deps.update(self.facts.param_dep_of(ref))
            if include_strings:
                info.strings.update(self.facts.string_of(ref))

    def is_getattr_forwarding_attr_param(
        self,
        attr_info: ExprInfo,
        ctx: FunctionContext,
    ) -> bool:
        """Return true when `getattr` uses the current __getattr__ attr name."""

        if ctx.info.name != "__getattr__" or ctx.info.class_key is None:
            return False
        if len(ctx.info.params) < 2:
            return False
        attr_param = ctx.info.params[1]
        return ParamDep(ctx.info.key, attr_param) in attr_info.param_deps

    def class_attr_proxy_provider_kinds(self, class_key: ClassKey) -> set[str]:
        """Return provider attr-proxy facts exposed by a class __getattr__."""

        out: set[str] = set()
        for info in method_infos(class_key, "__getattr__", self.index):
            for kind in self.facts.provider_of(ReturnRef(info.key)):
                provider = attr_proxy_provider(kind)
                if provider:
                    out.add(attr_proxy_kind(provider))
        return out

    def external_call_result_info(
        self,
        expr: ast.AST | None,
        ctx: FunctionContext,
        span: RegionSpan,
    ) -> ExprInfo:
        """Return tainted input facts for unresolved call results used as values."""

        if not isinstance(expr, ast.Call):
            return ExprInfo()
        if provider_request_call(expr, ctx, self.facts, self.index):
            return ExprInfo()
        if resolve_call(
            expr,
            ctx,
            self.facts,
            self.index,
            include_class_object_methods=True,
        ):
            return ExprInfo()
        if not self.is_external_value_call(expr, ctx) and not isinstance(
            expr.func,
            ast.Attribute,
        ):
            return ExprInfo()

        result = ExprInfo()
        if isinstance(expr.func, ast.Attribute):
            result.merge(self.eval_expr(expr.func.value, ctx, span))
        for arg in expr.args:
            result.merge(self.eval_expr(arg, ctx, span))
        for keyword in expr.keywords:
            result.merge(self.eval_expr(keyword.value, ctx, span))
        return ExprInfo(
            origins=result.origins,
            param_origins=result.param_origins,
            param_deps=result.param_deps,
            strings=result.strings,
        )

    def preserved_call_result_info(
        self,
        expr: ast.AST | None,
        ctx: FunctionContext,
        span: RegionSpan,
    ) -> ExprInfo:
        """Return facts preserved by calls that copy or cast the same value."""

        if not isinstance(expr, ast.Call):
            return ExprInfo()
        if isinstance(expr.func, ast.Attribute) and expr.func.attr in {"copy", "model_copy"}:
            return self.eval_expr(expr.func.value, ctx, span)

        call_names = {
            item.full_name for item in resolve_expr_name(expr.func, ctx.info.scope, self.index)
        }
        if call_names & {"copy.copy", "copy.deepcopy"} and expr.args:
            return self.eval_expr(expr.args[0], ctx, span)
        if (
            call_names & {"typing.cast", "typing_extensions.cast"}
            and len(expr.args) >= 2
        ):
            return self.eval_expr(expr.args[1], ctx, span)
        return ExprInfo()

    def is_external_value_call(self, call: ast.Call, ctx: FunctionContext) -> bool:
        """Return true for unresolved calls that should conservatively preserve inputs."""

        if self.builtin_call_name(call, ctx):
            return True
        return any(
            resolved.kind == "external"
            for resolved in resolve_expr_name(call.func, ctx.info.scope, self.index)
        )

    def handle_builtin_callback_call(
        self,
        call: ast.Call,
        ctx: FunctionContext,
        span: RegionSpan,
    ) -> ExprInfo | None:
        """Handle small, statically known builtin callback forms."""

        name = self.builtin_call_name(call, ctx)
        if name in {"list", "tuple", "set", "dict"}:
            result = ExprInfo()
            for arg in call.args:
                result.merge(self.eval_expr(arg, ctx, span))
            for keyword in call.keywords:
                result.merge(self.eval_expr(keyword.value, ctx, span))
            return result

        if name == "map" and call.args and isinstance(call.args[0], ast.Lambda):
            iter_infos = [self.eval_expr(arg, ctx, span) for arg in call.args[1:]]
            return self.eval_lambda_callback(call.args[0], iter_infos, ctx, span)

        if name == "filter" and len(call.args) >= 2 and isinstance(call.args[0], ast.Lambda):
            iter_info = self.eval_expr(call.args[1], ctx, span)
            result = self.eval_lambda_callback(call.args[0], [iter_info], ctx, span)
            result.merge(iter_info)
            return result

        if name in {"sorted", "min", "max"}:
            key_lambda = self.keyword_lambda(call, "key")
            if key_lambda is None or not call.args:
                return None
            iter_infos = [self.eval_expr(arg, ctx, span) for arg in call.args]
            item_info = ExprInfo()
            for info in iter_infos:
                item_info.merge(info)
            result = self.eval_lambda_callback(key_lambda, [item_info], ctx, span)
            result.merge(item_info)
            for keyword in call.keywords:
                if keyword.arg != "key":
                    result.merge(self.eval_expr(keyword.value, ctx, span))
            return result

        return None

    def eval_lambda_callback(
        self,
        expr: ast.Lambda,
        arg_infos: list[ExprInfo],
        ctx: FunctionContext,
        span: RegionSpan,
    ) -> ExprInfo:
        """Bind lambda parameters to known callback inputs and read its body."""

        params = self.lambda_positional_params(expr)
        for param, info in zip(params, arg_infos, strict=False):
            if self.has_value_facts(info):
                self.add_preserved_info_to_ref(LocalRef(ctx.info.key, param), info)
        if expr.args.vararg:
            rest = ExprInfo()
            for info in arg_infos[len(params) :]:
                rest.merge(info)
            if self.has_value_facts(rest):
                self.add_preserved_info_to_ref(
                    LocalRef(ctx.info.key, expr.args.vararg.arg),
                    rest,
                )
        return self.value_result_info(expr.body, ctx, span)

    def lambda_positional_params(self, expr: ast.Lambda) -> list[str]:
        """Return lambda positional parameter names in call binding order."""

        return [arg.arg for arg in (*expr.args.posonlyargs, *expr.args.args)]

    def keyword_lambda(self, call: ast.Call, name: str) -> ast.Lambda | None:
        """Return a named lambda keyword value, if present."""

        for keyword in call.keywords:
            if keyword.arg == name and isinstance(keyword.value, ast.Lambda):
                return keyword.value
        return None

    def builtin_call_name(self, call: ast.Call, ctx: FunctionContext) -> str | None:
        """Return the builtin function name for unshadowed simple calls."""

        if not isinstance(call.func, ast.Name):
            return None
        name = call.func.id
        if name_is_local_to_function(name, ctx.info, self.index):
            return None
        if resolve_expr_name(call.func, ctx.info.scope, self.index):
            return None
        return name

    def handle_container_mutation(
        self,
        call: ast.Call,
        ctx: FunctionContext,
        span: RegionSpan,
        input_origins: set[RegionSpan],
    ) -> None:
        """Propagate tainted values written through common container mutators."""

        if not input_origins or not isinstance(call.func, ast.Attribute):
            return
        if call.func.attr not in {"append", "extend", "insert", "add", "update", "setdefault"}:
            return
        for ref in refs_for_read_expr(
            call.func.value,
            ctx,
            self.facts,
            self.index,
            include_prefixes=False,
        ):
            self.facts.add_taint(ref, {span})
        self.facts.add_data_edge(span, input_origins, "assignment")

    def container_read_returns_taint(self, call: ast.Call) -> bool:
        """Return true for common container reads that produce stored values."""

        return isinstance(call.func, ast.Attribute) and call.func.attr in {
            "get",
            "pop",
            "popleft",
            "popitem",
        }

    def callee_actual_infos(
        self,
        target: CallTarget,
        receiver_info: ExprInfo,
        arg_infos: list[ExprInfo],
        kw_infos: list[ExprInfo],
        call: ast.Call,
    ) -> dict[str, list[ExprInfo]]:
        """Map callee parameter names to actual expression facts."""

        callee = self.index.functions.get(target.key)
        if callee is None:
            return {}
        params = list(callee.params)
        if not params:
            return {}

        actuals: dict[str, list[ExprInfo]] = {}
        if target.positional_offset and self.has_value_facts(receiver_info):
            actuals.setdefault(params[0], []).append(receiver_info)

        args = callee.node.args
        positional = [arg.arg for arg in (*args.posonlyargs, *args.args)]
        explicit_keywords = {keyword.arg for keyword in call.keywords if keyword.arg}
        positional_count = target.positional_offset + sum(
            not isinstance(arg, ast.Starred) for arg in call.args
        )
        # Keyword expansion cannot bind positional-only or already-bound parameters.
        keyword_params = {arg.arg for arg in (*args.args, *args.kwonlyargs)}
        keyword_params.difference_update(positional[:positional_count])
        keyword_params.difference_update(explicit_keywords)
        if args.kwarg:
            keyword_params.add(args.kwarg.arg)

        for idx, arg_info in enumerate(arg_infos):
            if not self.has_value_facts(arg_info):
                continue
            if idx < len(call.args) and isinstance(call.args[idx], ast.Starred):
                start = target.positional_offset + sum(
                    not isinstance(arg, ast.Starred) for arg in call.args[:idx]
                )
                candidates = positional[start:]
                if args.vararg:
                    candidates.append(args.vararg.arg)
                for param in candidates:
                    if param not in explicit_keywords:
                        actuals.setdefault(param, []).append(arg_info)
                continue
            param_idx = idx + target.positional_offset
            if param_idx < len(params):
                actuals.setdefault(params[param_idx], []).append(arg_info)

        for keyword, kw_info in zip(call.keywords, kw_infos, strict=False):
            if not self.has_value_facts(kw_info):
                continue
            if keyword.arg is None:
                for param in sorted(keyword_params):
                    actuals.setdefault(param, []).append(kw_info)
            elif keyword.arg in params:
                actuals.setdefault(keyword.arg, []).append(kw_info)
        return actuals

    def seed_callee_arguments(
        self,
        target: CallTarget,
        actual_infos: dict[str, list[ExprInfo]],
        span: RegionSpan,
    ) -> None:
        """Map actual input facts to callee parameter refs."""

        for param, infos in actual_infos.items():
            for info in infos:
                dep = ParamDep(target.key, param)
                param_deps = set(info.param_deps)
                if info.origins or info.param_deps:
                    param_deps.add(dep)
                formal_info = ExprInfo(
                    origins=set(info.origins),
                    param_origins=set(info.origins),
                    providers=set(info.providers),
                    types=set(info.types),
                    constructors=set(info.constructors),
                    aliases=set(info.aliases),
                    param_deps=param_deps,
                    strings=set(info.strings),
                )
                self.add_info_to_ref(
                    LocalRef(target.key, param),
                    formal_info,
                    span,
                    taint=True,
                )

    def instantiate_return_param_deps(
        self,
        target: CallTarget,
        actual_infos: dict[str, list[ExprInfo]],
    ) -> ExprInfo:
        """Instantiate callee return dependencies with call-site actual facts."""

        result = ExprInfo()
        for dep, spans in self.facts.return_param_deps_of(target.key).items():
            if dep.function != target.key:
                continue
            for actual_info in actual_infos.get(dep.name, []):
                if actual_info.param_deps:
                    result.param_deps.update(actual_info.param_deps)
                if not actual_info.origins:
                    continue
                result.origins.update(spans)
                if actual_info.param_deps and actual_info.origins <= actual_info.param_origins:
                    result.param_origins.update(spans)
        return result

    def handle_control_stmt(
        self,
        stmt: ast.stmt,
        ctx: FunctionContext,
        span: RegionSpan,
    ) -> None:
        """Handle control-flow statements and tainted control blocks."""

        if isinstance(stmt, ast.If):
            control_info = self.eval_expr(stmt.test, ctx, span)
            self.enter_control_blocks(control_info, span, ctx, stmt.body, stmt.orelse)
        elif isinstance(stmt, ast.While):
            control_info = self.eval_expr(stmt.test, ctx, span)
            self.enter_control_blocks(control_info, span, ctx, stmt.body, stmt.orelse)
        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            control_info = self.eval_expr(stmt.iter, ctx, span)
            control_info.merge(self.external_call_result_info(stmt.iter, ctx, span))
            target_ref_list = target_refs(stmt.target, ctx, self.facts, self.index)
            for ref in target_ref_list:
                self.facts.add_provider(ref, control_info.providers)
                self.facts.add_type(ref, control_info.types)
                self.facts.add_constructor(ref, control_info.constructors)
                self.facts.add_alias(ref, control_info.aliases)
                self.facts.add_param_dep(ref, control_info.param_deps)
                self.facts.add_string(ref, control_info.strings)
            if control_info.origins:
                for ref in target_ref_list:
                    self.facts.add_taint(ref, {span})
                    if self.is_param_only_value(control_info, control_info.param_deps):
                        self.facts.add_param_taint(ref, {span})
                self.facts.add_data_edge(span, control_info.origins, "assignment")
            self.enter_control_blocks(control_info, span, ctx, stmt.body, stmt.orelse)
        elif isinstance(stmt, ast.Match):
            control_info = self.eval_expr(stmt.subject, ctx, span)
            body_lists = [case.body for case in stmt.cases]
            self.enter_control_blocks(control_info, span, ctx, *body_lists)

    def enter_control_blocks(
        self,
        control_info: ExprInfo,
        span: RegionSpan,
        ctx: FunctionContext,
        *blocks: list[ast.stmt],
    ) -> None:
        """Analyze child blocks under a tainted control origin when needed."""

        next_ctx = ctx
        if control_info.origins:
            self.facts.add_data_edge(span, control_info.origins, "control")
            next_ctx = self.make_context(ctx.info, span)
        for block in blocks:
            self.analyze_block(block, next_ctx)

    def handle_with(
        self,
        stmt: ast.With | ast.AsyncWith,
        ctx: FunctionContext,
        span: RegionSpan,
    ) -> None:
        """Handle context-manager expressions without modeling manager internals."""

        for item in stmt.items:
            info = self.eval_expr(item.context_expr, ctx, span)
            if item.optional_vars is not None and info.origins:
                for ref in target_refs(item.optional_vars, ctx, self.facts, self.index):
                    self.facts.add_taint(ref, {span})
                self.facts.add_data_edge(span, info.origins, "assignment")
        self.analyze_block(stmt.body, ctx)

    def handle_try(self, stmt: ast.Try, ctx: FunctionContext, span: RegionSpan) -> None:
        """Analyze try/except/finally blocks path-insensitively."""

        self.analyze_block(stmt.body, ctx)
        for handler in stmt.handlers:
            if handler.type is not None:
                self.eval_expr(handler.type, ctx, span)
            self.analyze_block(handler.body, ctx)
        self.analyze_block(stmt.orelse, ctx)
        self.analyze_block(stmt.finalbody, ctx)

    def handle_assert_or_raise(
        self,
        stmt: ast.Assert | ast.Raise,
        ctx: FunctionContext,
        span: RegionSpan,
    ) -> None:
        """Record reads inside assert and raise statements."""

        exprs: list[ast.AST | None]
        if isinstance(stmt, ast.Assert):
            exprs = [stmt.test, stmt.msg]
        else:
            exprs = [stmt.exc, stmt.cause]
        origins: set[RegionSpan] = set()
        for expr in exprs:
            origins.update(self.eval_expr(expr, ctx, span).origins)
        self.facts.add_data_edge(span, origins, "access")

    def build_control_regions(self, mode: str) -> list[ControlDependenceRegion]:
        """Build function-level control-dependence output from recorded calls."""

        selected: dict[FunctionKey, RegionSpan] = {}
        queue: list[FunctionKey] = []
        caller_data_spans = self.caller_data_spans()
        for call in sorted(
            self.facts.control_calls,
            key=lambda item: (
                item.callee.module,
                item.callee.qualname,
                item.control_span.file,
                item.control_span.start,
            ),
        ):
            if call.span in caller_data_spans or call.callee in selected:
                continue
            selected[call.callee] = call.control_span
            queue.append(call.callee)

        if mode == "recursive":
            outgoing: dict[FunctionKey, set[FunctionKey]] = {}
            for call in self.facts.calls:
                outgoing.setdefault(call.caller, set()).add(call.callee)
            cursor = 0
            while cursor < len(queue):
                caller = queue[cursor]
                cursor += 1
                for callee in sorted(outgoing.get(caller, set())):
                    if callee in selected:
                        continue
                    selected[callee] = selected[caller]
                    queue.append(callee)

        return [
            ControlDependenceRegion(info=self.index.functions[key], control_span=control_span)
            for key, control_span in selected.items()
            if key in self.index.functions
        ]

    def caller_data_spans(self) -> set[RegionSpan]:
        """Return statement spans that already have direct caller data flow."""

        return {
            edge.span
            for edge in self.facts.data_edges
            if edge.dependence_type == "caller"
        }

    def is_direct_source_only(self, info: ExprInfo) -> bool:
        """Return true when a statement's only origin is its own source call."""

        return bool(info.direct_sources) and info.origins <= info.direct_sources

    def current_param_deps(
        self,
        info: ExprInfo,
        function_key: FunctionKey,
    ) -> set[ParamDep]:
        """Return formal dependencies that belong to the current function."""

        return {dep for dep in info.param_deps if dep.function == function_key}

    def is_param_only_value(self, info: ExprInfo, deps: set[ParamDep]) -> bool:
        """Return true when value facts are only formal-parameter-derived."""

        return bool(deps) and info.origins <= info.param_origins

    def has_value_facts(self, info: ExprInfo) -> bool:
        """Return true when an expression carries facts worth propagating."""

        return bool(
            info.origins
            or info.providers
            or info.types
            or info.constructors
            or info.aliases
            or info.param_deps
            or info.strings
        )
