"""Deterministic target-unit packet projection for generation lanes."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def focus_target_packet(
    packet: dict[str, Any],
    sample_index: int,
    *,
    lane: str = "hard_core",
) -> dict[str, Any]:
    """Return a focused prompt packet for one target unit."""

    units = [unit for unit in packet.get("target_units", []) if isinstance(unit, dict)]
    if not units:
        return packet
    focus = focus_target_unit(units, sample_index)
    focused = deepcopy(packet)
    focused["lane"] = lane
    focused["all_target_units"] = units
    focused["target_units"] = [focus]
    focused["focus_target_unit_id"] = str(focus.get("unit_id") or "")
    focused["focus_sample_index"] = sample_index
    focused["focus_total_target_units"] = len(units)
    focused["focus_target_unit"] = unit_identity(focus)
    focused["source_file_index"] = focus_source_file_index(
        packet.get("source_file_index", []), focus
    )
    focused["module_imports"] = [
        item
        for item in packet.get("module_imports", [])
        if item.get("path") == focus.get("filepath")
    ]
    focused["module_contracts"] = [
        item
        for item in packet.get("module_contracts", [])
        if item.get("filepath") == focus.get("filepath")
    ]
    routes = packet.get("public_target_routes", {})
    focused["public_target_routes"] = {
        **routes,
        "targets": [
            item
            for item in routes.get("targets", [])
            if item.get("target_unit_id") == focus.get("unit_id")
        ],
        "unreachable_target_unit_ids": [
            unit_id
            for unit_id in routes.get("unreachable_target_unit_ids", [])
            if unit_id == focus.get("unit_id")
        ],
    }
    focused["existing_tests"] = focus_existing_tests(
        packet.get("existing_tests", []),
        focus,
        total_units=len(units),
    )
    focused["retrieved_context"] = focus_retrieved_context(
        packet.get("retrieved_context"), focus
    )
    return focused


def soft_target_packet(packet: dict[str, Any], sample_index: int) -> dict[str, Any]:
    """Return a whole-target extension packet after hard focus is exhausted."""

    focused = deepcopy(packet)
    focused["lane"] = "soft_extension"
    focused["soft_sample_index"] = sample_index
    focused["whole_target_pass"] = True
    return focused


def focus_target_unit(
    units: list[dict[str, Any]],
    sample_index: int,
) -> dict[str, Any]:
    if not units:
        raise SystemExit("target packet has no target units")
    index = (max(1, int(sample_index)) - 1) % len(units)
    return units[index]


def unit_identity(unit: dict[str, Any]) -> dict[str, str]:
    return {
        "unit_id": str(unit.get("unit_id") or ""),
        "filepath": str(unit.get("filepath") or ""),
        "qualname": str(unit.get("qualname") or ""),
        "kind": str(unit.get("kind") or ""),
    }


def focus_source_file_index(
    entries: Any,
    focus: dict[str, Any],
) -> list[dict[str, Any]]:
    filepath = str(focus.get("filepath") or "")
    valid_entries = [item for item in entries if isinstance(item, dict)]
    return [item for item in valid_entries if str(item.get("path") or "") == filepath]


def focus_existing_tests(
    tests: Any,
    focus: dict[str, Any],
    *,
    total_units: int,
) -> list[dict[str, Any]]:
    valid_tests = [item for item in tests if isinstance(item, dict)]
    if total_units <= 1:
        return valid_tests
    focus_unit_id = str(focus.get("unit_id") or "")
    focus_filepath = str(focus.get("filepath") or "")
    return [
        item
        for item in valid_tests
        if focus_unit_id in {str(value) for value in item.get("target_unit_ids", [])}
        or focus_filepath in {str(value) for value in item.get("target_filepaths", [])}
    ]


def focus_retrieved_context(
    context: Any,
    focus: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {}
    filepath = str(focus.get("filepath") or "")
    requests = [
        item
        for item in context.get("requests", [])
        if isinstance(item, dict)
        and item.get("status") == "found"
        and str(item.get("filepath") or "") == filepath
    ]
    if not requests:
        return {}
    return {**context, "requests": requests}
