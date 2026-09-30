#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from augment.python.models import ContextRequest, TestProposal


def parse_test_proposal(content: str | dict[str, Any]) -> TestProposal:
    data = content if isinstance(content, dict) else parse_json_object(content)
    test_file = require_string(data, "test_file")
    append_code = require_string(data, "append_code")
    validate_test_path(test_file)
    expected_nodeids = string_list(data.get("expected_nodeids", []), "expected_nodeids")
    for nodeid in expected_nodeids:
        if not nodeid.startswith(test_file + "::"):
            raise SystemExit(f"expected nodeid outside proposed test file: {nodeid}")
    return TestProposal(
        test_file=test_file,
        append_code=append_code,
        expected_nodeids=expected_nodeids,
        targeted_objective_ids=string_list(
            data.get("targeted_objective_ids", []), "targeted_objective_ids"
        ),
        targeted_lines=string_list(data.get("targeted_lines", []), "targeted_lines"),
        mocking_strategy=optional_string(data, "mocking_strategy"),
        oracle=optional_string(data, "oracle"),
    )


def parse_context_requests(value: Any) -> list[ContextRequest]:
    """Validate one context-request list returned by the model."""

    if value is None:
        return []
    if not isinstance(value, list):
        raise SystemExit("context requests must be a list")
    return [parse_context_request(item) for item in value]


def parse_segment_response(content: str | dict[str, Any]) -> dict[str, Any]:
    """Validate a request_context or propose_test response."""

    data = content if isinstance(content, dict) else parse_json_object(content)
    action = require_string(data, "action")
    diagnosis = optional_string(data, "diagnosis")
    if action == "request_context":
        requests = parse_context_requests(data.get("requests", []))
        if not requests:
            raise SystemExit("context action must contain at least one request")
        return {
            "action": action,
            "diagnosis": diagnosis,
            "requests": [request.to_dict() for request in requests],
        }
    if action == "propose_test":
        proposal = parse_test_proposal(
            {
                key: value
                for key, value in data.items()
                if key not in {"action", "diagnosis"}
            }
        )
        return {
            "action": action,
            "diagnosis": diagnosis,
            "proposal": proposal.to_dict(),
        }
    raise SystemExit(f"unsupported segment response action: {action}")


def parse_context_request(item: Any) -> ContextRequest:
    if not isinstance(item, dict):
        raise SystemExit("context request must be an object")
    kind = require_string(item, "kind")
    filepath = require_string(item, "filepath")
    validate_project_path(filepath, field="filepath")
    start_line = optional_positive_int(item.get("start_line"), "start_line")
    end_line = optional_positive_int(item.get("end_line"), "end_line")
    if start_line is not None and end_line is not None and end_line < start_line:
        raise SystemExit("proposal field end_line must not precede start_line")
    return ContextRequest(
        kind=kind,
        filepath=filepath,
        qualname=optional_string(item, "qualname"),
        reason=optional_string(item, "reason"),
        start_line=start_line,
        end_line=end_line,
    )


def parse_json_object(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"proposal is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("proposal must be a JSON object")
    return data


def require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"proposal missing string field: {key}")
    return value


def string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SystemExit(f"proposal field must be a list: {field}")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise SystemExit(f"proposal field entries must be non-empty strings: {field}")
    return list(value)


def optional_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise SystemExit(f"proposal field must be a string: {key}")
    return value


def optional_positive_int(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SystemExit(f"proposal field must be a positive integer: {field}")
    return value


def validate_test_path(path: str) -> None:
    validate_project_path(path, field="test_file")
    if not path.startswith("tests/") or not path.endswith(".py"):
        raise SystemExit(f"proposal can only append pytest files under tests/: {path}")


def validate_project_path(path: str, *, field: str) -> None:
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise SystemExit(f"unsafe {field}: {path}")
