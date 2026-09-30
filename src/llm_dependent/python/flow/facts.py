#!/usr/bin/env python3
"""Global fact table for Python LLM-dependent flow analysis."""

from __future__ import annotations

from collections import defaultdict
from typing import TypeVar

from ..common import RegionSpan
from .models import (
    CallFact,
    ClassKey,
    ControlCallFact,
    ExprInfo,
    FlowEdge,
    FunctionKey,
    ParamDep,
    ReturnRef,
    ValueRef,
)


K = TypeVar("K")
T = TypeVar("T")
V = TypeVar("V")


def ordered_spans(spans: set[RegionSpan]) -> tuple[RegionSpan, ...]:
    """Return spans in stable order for hashable edge records."""

    return tuple(sorted(spans, key=lambda span: (span.file, span.start, span.end)))


class FactStore:
    """Store mutable analysis facts and track additions through `version`.

    An unchanged version after a full project scan indicates convergence.
    """

    def __init__(self) -> None:
        self.version = 0
        self.sources: set[RegionSpan] = set()
        self.taints: dict[ValueRef, set[RegionSpan]] = defaultdict(set)
        self.param_taints: dict[ValueRef, set[RegionSpan]] = defaultdict(set)
        self.providers: dict[ValueRef, set[str]] = defaultdict(set)
        self.types: dict[ValueRef, set[ClassKey]] = defaultdict(set)
        self.constructors: dict[ValueRef, set[ClassKey]] = defaultdict(set)
        self.aliases: dict[ValueRef, set[FunctionKey]] = defaultdict(set)
        self.param_deps: dict[ValueRef, set[ParamDep]] = defaultdict(set)
        self.strings: dict[ValueRef, set[str]] = defaultdict(set)
        self.return_param_deps: dict[
            FunctionKey,
            dict[ParamDep, set[RegionSpan]],
        ] = defaultdict(lambda: defaultdict(set))
        self.data_edges: set[FlowEdge] = set()
        self.calls: set[CallFact] = set()
        self.control_calls: set[ControlCallFact] = set()

    def add_source(self, span: RegionSpan) -> None:
        """Record a matched provider/model request location."""

        self._add_set_item(self.sources, span)

    def add_taint(self, ref: ValueRef, origins: set[RegionSpan]) -> None:
        """Mark `ref` as LLM-derived with adjacent origin spans."""

        if origins:
            self._add_map_values(self.taints, ref, origins)

    def add_param_taint(self, ref: ValueRef, origins: set[RegionSpan]) -> None:
        """Mark taint origins on `ref` as formal-parameter-derived."""

        if origins:
            self._add_map_values(self.param_taints, ref, origins)

    def add_provider(self, ref: ValueRef, provider_kinds: set[str]) -> None:
        """Mark `ref` as provider-backed."""

        if provider_kinds:
            self._add_map_values(self.providers, ref, provider_kinds)

    def add_type(self, ref: ValueRef, class_keys: set[ClassKey]) -> None:
        """Record static class types for `ref`."""

        if class_keys:
            self._add_map_values(self.types, ref, class_keys)

    def add_constructor(self, ref: ValueRef, class_keys: set[ClassKey]) -> None:
        """Record class objects that may be called through `ref`."""

        if class_keys:
            self._add_map_values(self.constructors, ref, class_keys)

    def add_alias(self, ref: ValueRef, targets: set[FunctionKey]) -> None:
        """Record callable aliases for `ref`."""

        if targets:
            self._add_map_values(self.aliases, ref, targets)

    def add_param_dep(self, ref: ValueRef, deps: set[ParamDep]) -> None:
        """Record formal-parameter dependencies for `ref`."""

        if deps:
            self._add_map_values(self.param_deps, ref, deps)

    def add_string(self, ref: ValueRef, strings: set[str]) -> None:
        """Record literal string values used for source certification only."""

        if strings:
            self._add_map_values(self.strings, ref, strings)

    def add_return(self, function_key: FunctionKey, origins: set[RegionSpan]) -> None:
        """Mark a function return value as tainted."""

        self.add_taint(ReturnRef(function_key), origins)

    def add_return_param_deps(
        self,
        function_key: FunctionKey,
        deps: set[ParamDep],
        span: RegionSpan,
    ) -> None:
        """Record that a function return depends on formal parameters."""

        for dep in deps:
            self._add_map_values(self.return_param_deps[function_key], dep, {span})

    def add_data_edge(
        self,
        span: RegionSpan,
        origins: set[RegionSpan],
        dependence_type: str,
    ) -> None:
        """Record one statement-level flow edge."""

        if not origins:
            return
        self._add_set_item(
            self.data_edges,
            FlowEdge(
                span=span,
                source_spans=ordered_spans(origins),
                dependence_type=dependence_type,
            ),
        )

    def add_call(self, call: CallFact) -> None:
        """Record a resolved project-local call."""

        self._add_set_item(self.calls, call)

    def add_control_call(self, call: ControlCallFact) -> None:
        """Record a project-local call under a tainted control condition."""

        self._add_set_item(self.control_calls, call)

    def taint_of(self, ref: ValueRef) -> set[RegionSpan]:
        """Return adjacent taint origins for `ref`."""

        return set(self.taints.get(ref, set()))

    def param_taint_of(self, ref: ValueRef) -> set[RegionSpan]:
        """Return taint origins on `ref` that are formal-parameter-derived."""

        return set(self.param_taints.get(ref, set()))

    def provider_of(self, ref: ValueRef) -> set[str]:
        """Return provider provenance for `ref`."""

        return set(self.providers.get(ref, set()))

    def type_of(self, ref: ValueRef) -> set[ClassKey]:
        """Return static class types for `ref`."""

        return set(self.types.get(ref, set()))

    def constructor_of(self, ref: ValueRef) -> set[ClassKey]:
        """Return class objects that may be called through `ref`."""

        return set(self.constructors.get(ref, set()))

    def alias_of(self, ref: ValueRef) -> set[FunctionKey]:
        """Return callable aliases for `ref`."""

        return set(self.aliases.get(ref, set()))

    def param_dep_of(self, ref: ValueRef) -> set[ParamDep]:
        """Return formal-parameter dependencies for `ref`."""

        return set(self.param_deps.get(ref, set()))

    def string_of(self, ref: ValueRef) -> set[str]:
        """Return known literal string values for `ref`."""

        return set(self.strings.get(ref, set()))

    def return_param_deps_of(
        self,
        function_key: FunctionKey,
    ) -> dict[ParamDep, set[RegionSpan]]:
        """Return parameter-dependent return spans for one function."""

        return {
            dep: set(spans)
            for dep, spans in self.return_param_deps.get(function_key, {}).items()
        }

    def info_of(self, ref: ValueRef) -> ExprInfo:
        """Return all facts stored on one exact value ref."""

        return ExprInfo(
            origins=self.taint_of(ref),
            param_origins=self.param_taint_of(ref),
            providers=self.provider_of(ref),
            types=self.type_of(ref),
            constructors=self.constructor_of(ref),
            aliases=self.alias_of(ref),
            param_deps=self.param_dep_of(ref),
            strings=self.string_of(ref),
        )

    def _add_set_item(self, store: set[T], item: T) -> None:
        """Add an item to a set and bump `version` only if it is new."""

        if item in store:
            return
        store.add(item)
        self.version += 1

    def _add_map_values(
        self,
        store: dict[K, set[V]],
        key: K,
        values: set[V],
    ) -> None:
        """Add values into a map-of-sets and bump `version` for new facts."""

        current = store[key]
        before = len(current)
        current.update(values)
        if len(current) != before:
            self.version += 1
