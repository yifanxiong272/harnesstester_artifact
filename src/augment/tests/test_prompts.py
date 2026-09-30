"""Check the shared context-request schema and phase-specific controls."""

import json
import re

import pytest

from augment.python.prompt.prompts import (
    render_coverage_segment_feedback_prompt,
    render_coverage_segment_prompt,
)
from augment.python.prompt.proposal import parse_segment_response


PACKET = {
    "test_name_suffix": "_round_001",
    "test_file_suffix": "_round_001.py",
}


def context_request_example(prompt):
    objects = [
        json.loads(block)
        for block in re.findall(r"```json\n(.*?)\n```", prompt, re.S)
    ]
    requests = [
        item for item in objects
        if isinstance(item, dict) and item.get("action") == "request_context"
    ]
    assert len(requests) == 1
    return requests[0]


@pytest.mark.parametrize(
    "kind",
    ["class_definition", "function_definition", "symbol_definition", "module_context"],
)
def test_generation_and_repair_share_request_fields(kind):
    initial = context_request_example(render_coverage_segment_prompt(PACKET))
    repair = context_request_example(
        render_coverage_segment_feedback_prompt(
            feedback={"status": "validation_failed"},
            traceback_context=[],
            context_request_limit=3,
        )
    )
    assert repair["requests"] == initial["requests"]
    assert set(initial) == {"action", "requests"}
    assert set(repair) == {"action", "diagnosis", "requests"}
    assert repair["diagnosis"]
    for example in (initial, repair):
        request = example["requests"][0]
        assert kind in request["kind"].split(" | ")
        request["kind"] = kind
        parsed = parse_segment_response(example)
        assert parsed["requests"] == example["requests"]
        assert parsed["requests"][0]["start_line"] == 1
        assert parsed["requests"][0]["end_line"] == 20


@pytest.mark.parametrize("strategy", ["contract_directed", "contract_agnostic"])
@pytest.mark.parametrize("limit", [0, 3])
def test_context_request_controls_remain_phase_specific(strategy, limit):
    initial = render_coverage_segment_prompt(PACKET, strategy=strategy)
    repair = render_coverage_segment_feedback_prompt(
        feedback={"status": "no_segment_coverage"},
        traceback_context=[],
        context_request_limit=limit,
        strategy=strategy,
    )
    enabled = strategy == "contract_directed"
    assert ('"action": "request_context"' in initial) == enabled
    assert ('"action": "request_context"' in repair) == (enabled and limit > 0)
    if enabled and limit > 0:
        assert f"at most {limit} item(s)" in repair
    else:
        assert "Repair-time context requests are disabled." in repair
