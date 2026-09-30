#!/usr/bin/env python3
"""Identities and facts used by Python LLM-dependent flow analysis."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypeAlias

from ..common import RegionSpan


@dataclass(frozen=True, order=True)
class ScopeKey:
    """Lexical scope identity used only by the resolver.

    `module` identifies the file/module. `qualname` is empty for module scope
    and dotted for class/function scopes, for example `Agent.step.inner`.
    """

    module: str
    qualname: str = ""


@dataclass(frozen=True, order=True)
class FunctionKey:
    """Canonical identity for one project-local function or method."""

    module: str
    qualname: str


@dataclass(frozen=True, order=True)
class ClassKey:
    """Canonical identity for one project-local class."""

    module: str
    qualname: str


@dataclass(frozen=True, order=True)
class LocalRef:
    """A value path inside one function scope, such as `action` or `obj.value`."""

    function: FunctionKey
    path: str


@dataclass(frozen=True, order=True)
class ReturnRef:
    """The return value of one project-local function."""

    function: FunctionKey


@dataclass(frozen=True, order=True)
class ParamDep:
    """A value dependency on one formal parameter."""

    function: FunctionKey
    name: str


@dataclass(frozen=True, order=True)
class ClassFieldRef:
    """A field fact shared across instances of a class.

    Writes through `self.x` contribute to reads of the class-scoped field.
    """

    class_key: ClassKey
    path: str


@dataclass(frozen=True, order=True)
class ModuleRef:
    """A module-level value fact, such as `module.client`."""

    module: str
    path: str


ValueRef: TypeAlias = LocalRef | ReturnRef | ClassFieldRef | ModuleRef


@dataclass
class NameEnv:
    """Lexical name bindings and the parent scope used for outward lookup."""

    scope: ScopeKey
    parent: ScopeKey | None
    imports: dict[str, set[str]] = field(default_factory=dict)
    imported_attrs: dict[str, set[tuple[str, str]]] = field(default_factory=dict)
    local_functions: dict[str, set[FunctionKey]] = field(default_factory=dict)
    local_classes: dict[str, set[ClassKey]] = field(default_factory=dict)


@dataclass
class FunctionInfo:
    """AST and resolver context for one project-local function."""

    key: FunctionKey
    file: str
    module: str
    qualname: str
    name: str
    scope: ScopeKey
    parent_scope: ScopeKey
    node: ast.FunctionDef | ast.AsyncFunctionDef
    params: tuple[str, ...]
    assigned_names: frozenset[str]
    param_types: dict[str, set[ClassKey]] = field(default_factory=dict)
    return_types: set[ClassKey] = field(default_factory=set)
    enclosing_functions: tuple[FunctionKey, ...] = ()
    class_key: ClassKey | None = None
    method_kind: Literal["function", "instance", "class", "static"] = "function"


@dataclass
class ClassInfo:
    """AST and resolver context for one project-local class."""

    key: ClassKey
    file: str
    module: str
    qualname: str
    name: str
    scope: ScopeKey
    parent_scope: ScopeKey
    node: ast.ClassDef
    bases: tuple[ClassKey, ...] = ()


@dataclass
class ProjectIndex:
    """Static project index consumed by resolver and analysis."""

    project_root: Path
    module_files: dict[str, Path]
    module_is_package: dict[str, bool]
    module_bodies: dict[str, list[ast.stmt]]
    scope_envs: dict[ScopeKey, NameEnv]
    functions: dict[FunctionKey, FunctionInfo]
    classes: dict[ClassKey, ClassInfo]
    class_methods: dict[tuple[ClassKey, str], set[FunctionKey]]
    class_bases: dict[ClassKey, set[ClassKey]]
    class_subclasses: dict[ClassKey, set[ClassKey]]


@dataclass(frozen=True)
class ResolvedName:
    """One result from lexical name resolution."""

    kind: Literal["function", "class", "external"]
    full_name: str
    function: FunctionKey | None = None
    class_key: ClassKey | None = None


@dataclass(frozen=True)
class CallTarget:
    """A project-local callable reached by a call expression.

    `positional_offset` counts implicit receiver parameters skipped when mapping
    explicit caller arguments to callee parameters.
    """

    key: FunctionKey
    positional_offset: int = 0


@dataclass
class FunctionContext:
    """Current function analysis context."""

    info: FunctionInfo
    control_origin: RegionSpan | None = None


@dataclass
class ExprInfo:
    """Facts learned from reading one expression."""

    origins: set[RegionSpan] = field(default_factory=set)
    param_origins: set[RegionSpan] = field(default_factory=set)
    direct_sources: set[RegionSpan] = field(default_factory=set)
    providers: set[str] = field(default_factory=set)
    types: set[ClassKey] = field(default_factory=set)
    constructors: set[ClassKey] = field(default_factory=set)
    aliases: set[FunctionKey] = field(default_factory=set)
    param_deps: set[ParamDep] = field(default_factory=set)
    strings: set[str] = field(default_factory=set)

    def merge(self, other: "ExprInfo") -> None:
        """Merge another expression result into this one."""

        self.origins.update(other.origins)
        self.param_origins.update(other.param_origins)
        self.direct_sources.update(other.direct_sources)
        self.providers.update(other.providers)
        self.types.update(other.types)
        self.constructors.update(other.constructors)
        self.aliases.update(other.aliases)
        self.param_deps.update(other.param_deps)
        self.strings.update(other.strings)


@dataclass(frozen=True)
class FlowEdge:
    """One statement-level dependence edge."""

    span: RegionSpan
    source_spans: tuple[RegionSpan, ...]
    dependence_type: str


@dataclass(frozen=True)
class CallFact:
    """One resolved project-local call seen during analysis."""

    caller: FunctionKey
    callee: FunctionKey
    span: RegionSpan


@dataclass(frozen=True)
class ControlCallFact:
    """A project-local call reached only through tainted control flow."""

    caller: FunctionKey
    callee: FunctionKey
    span: RegionSpan
    control_span: RegionSpan


@dataclass(frozen=True)
class ControlDependenceRegion:
    """One function-level control-dependence output region."""

    info: FunctionInfo
    control_span: RegionSpan


@dataclass(frozen=True)
class AnalysisStats:
    """Fixed-point convergence metadata."""

    converged: bool
    iterations: int
    max_iterations: int
