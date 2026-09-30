#!/usr/bin/env python3
"""Parse model-requested exact context for harness repair phases."""

from __future__ import annotations

from typing import Any

from probe.python.prompt.proposal import extract_json, parse_request_list


def parse_context_requests(
    text: str | dict[str, Any],
    *,
    max_requests: int = 1,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """Parse a bounded request list while preserving per-entry errors."""

    data = text if isinstance(text, dict) else extract_json(text)
    return parse_request_list(data.get("requests", []), max_requests=max_requests)


def parse_harness_repair_decision(
    text: str | dict[str, Any],
    *,
    max_requests: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Parse one repair decision without weakening proposal validation."""

    data = text if isinstance(text, dict) else extract_json(text)
    action = str(data.get("action") or "").strip()
    diagnosis = str(data.get("diagnosis") or "").strip()
    if action == "request_context":
        if max_requests <= 0:
            raise SystemExit("repair-time context requests are disabled")
        requests, errors = parse_context_requests(data, max_requests=max_requests)
        if not requests:
            raise SystemExit("request_context decision must contain a valid request")
        return {
            "action": action,
            "diagnosis": diagnosis,
            "requests": requests,
        }, errors
    if action == "repair":
        return {
            "action": action,
            "diagnosis": diagnosis,
            "proposal": data,
        }, []
    if action == "retain_original":
        return {"action": action, "diagnosis": diagnosis}, []
    raise SystemExit(f"unsupported harness repair action: {action}")
