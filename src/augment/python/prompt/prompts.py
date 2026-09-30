#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from string import Template
from typing import Any

from augment.python.strategy import DEFAULT_STRATEGY, is_contract_directed

TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "templates"


def render_coverage_segment_prompt(
    packet: dict[str, Any], *, strategy: str = DEFAULT_STRATEGY
) -> str:
    """Render the direct-generation prompt for one coverage segment."""

    directed = is_contract_directed(strategy)
    return render_template(
        "frozen_coverage_segment_prompt.md",
        value_guidance=(
            "Within the segment, prioritize behavior directly or indirectly influenced "
            "by model-derived values, including structured provider or tool payloads, "
            "accumulated agent state, observations, and runtime or error signals. "
            if directed
            else ""
        ),
        contract_guidance=(
            "You must account for agentic contracts when they are relevant:\n"
            "- preserve provider, tool, action, message, and observation payload shapes;\n"
            "- construct the state or history needed to reach the branch;\n"
            "- match sync or async call signatures and return shapes exactly;\n"
            "- patch the symbol where the code under test resolves it;\n"
            "- avoid live models, network access, external services, and real API keys."
            if directed
            else "Avoid live models, network access, external services, and real API keys."
        ),
        context_instruction=(
            "If an exact constructor, fixture, collaborator, or mock contract is "
            "missing, first return one context request batch. Otherwise return a "
            "test proposal directly."
            if directed
            else "Return a test proposal directly."
        ),
        response_instruction=(
            "Return only one JSON object in one of these forms."
            if directed
            else "Return only one JSON object."
        ),
        context_request_schema=(
            """Context request, allowed once:
```json
{
  "action": "request_context",
  "requests": [
    {
      "kind": "class_definition | function_definition | symbol_definition | module_context",
      "filepath": "project/relative/path.py",
      "qualname": "exact.qualified.name",
      "start_line": 1,
      "end_line": 20,
      "reason": "contract needed by the test"
    }
  ]
}
```

"""
            if directed
            else ""
        ),
        packet_json=json.dumps(packet, indent=2, sort_keys=True),
        test_file_suffix=str(packet["test_file_suffix"]),
        test_name_suffix=str(packet["test_name_suffix"]),
    )


def render_coverage_segment_feedback_prompt(
    *,
    feedback: dict[str, Any],
    traceback_context: list[dict[str, Any]],
    context_request_limit: int,
    strategy: str = DEFAULT_STRATEGY,
) -> str:
    """Render the only repair message allowed in a segment conversation."""

    directed = is_contract_directed(strategy)
    if not directed:
        context_request_limit = 0
    return render_template(
        "frozen_coverage_segment_feedback_prompt.md",
        diagnosis_context=(
            "measured failure and exact project context"
            if directed
            else "measured feedback"
        ),
        feedback_json=json.dumps(feedback, indent=2, sort_keys=True),
        traceback_section=(
            "\nProject-local traceback context:\n```json\n"
            + json.dumps(traceback_context, indent=2, sort_keys=True)
            + "\n```\n"
            if directed
            else ""
        ),
        context_request_instruction=(
            "You may instead request one exact context batch containing at most "
            f"{context_request_limit} item(s)."
            if context_request_limit > 0
            else "Repair-time context requests are disabled."
        ),
        context_request_schema=(
            """
Or request exact missing context before repairing:
```json
{
  "action": "request_context",
  "diagnosis": "evidence-based root cause and the missing contract",
  "requests": [
    {
      "kind": "class_definition | function_definition | symbol_definition | module_context",
      "filepath": "project/relative/path.py",
      "qualname": "exact.qualified.name",
      "start_line": 1,
      "end_line": 20,
      "reason": "contract needed by the test"
    }
  ]
}
```
""".strip()
            if context_request_limit > 0
            else ""
        ),
    )


def render_template(name: str, **values: str) -> str:
    template = Template((TEMPLATE_ROOT / name).read_text(encoding="utf-8"))
    return template.safe_substitute(**values).rstrip() + "\n"
