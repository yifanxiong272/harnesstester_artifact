#!/usr/bin/env python3
"""Serialize Python LLM-dependent facts to the final regions JSON."""

from __future__ import annotations

from typing import Any

from ..common import RegionSpan
from .facts import FactStore, ordered_spans
from .models import AnalysisStats, ControlDependenceRegion, FlowEdge, FunctionInfo


def build_payload(
    project_label: str,
    facts: FactStore,
    stats: AnalysisStats,
    control_regions: list[ControlDependenceRegion] | None = None,
) -> dict[str, Any]:
    """Build the final JSON payload consumed by downstream workflows."""

    payload = {
        "project": project_label,
        "extractor": "source_rooted_cross_function_return_flow",
        "fixed_point": {
            "converged": stats.converged,
            "iterations": stats.iterations,
            "max_iterations": stats.max_iterations,
        },
        "sources": source_payloads(facts.sources),
        "data_dependence": data_edge_payloads(facts.data_edges),
    }
    if control_regions is not None:
        payload["control_dependence"] = [
            control_region_payload(region)
            for region in sorted(
                control_regions,
                key=lambda item: (
                    item.info.file,
                    item.info.qualname,
                    item.control_span.file,
                    item.control_span.start,
                ),
            )
        ]
    return payload


def span_location(span: RegionSpan) -> dict[str, Any]:
    """Convert an internal span to the public location shape."""

    return {
        "filepath": span.file,
        "start_line": span.start,
        "end_line": span.end,
    }


def function_location(info: FunctionInfo) -> dict[str, str]:
    """Convert a function identity to the public control-region shape."""

    return {
        "filepath": info.file,
        "function": info.qualname,
    }


def source_payloads(sources: set[RegionSpan]) -> list[dict[str, Any]]:
    """Serialize source locations only."""

    return [{"location": span_location(span)} for span in ordered_spans(sources)]


def data_edge_payloads(edges: set[FlowEdge]) -> list[dict[str, Any]]:
    """Group edges so one location can carry several flow types."""

    grouped: dict[tuple[str, int, int], dict[str, set[RegionSpan]]] = {}
    for edge in edges:
        key = (edge.span.file, edge.span.start, edge.span.end)
        grouped.setdefault(key, {}).setdefault(edge.dependence_type, set()).update(
            edge.source_spans
        )

    return [
        {
            "location": {"filepath": filepath, "start_line": start, "end_line": end},
            "flows": [
                {
                    "dependence_type": dependence_type,
                    "source_locations": [
                        span_location(span) for span in ordered_spans(origins)
                    ],
                }
                for dependence_type, origins in sorted(flows.items())
            ],
        }
        for (filepath, start, end), flows in sorted(grouped.items())
    ]


def control_region_payload(region: ControlDependenceRegion) -> dict[str, Any]:
    """Serialize a function-level control-dependence region."""

    return {
        "location": function_location(region.info),
        "control_flow_statement_location": span_location(region.control_span),
    }
