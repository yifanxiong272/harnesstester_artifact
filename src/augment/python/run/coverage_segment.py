#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from augment.python.prompt.code_excerpt import code_excerpt_from_text
from augment.python.prompt.context import (
    failure_text_from_row,
    project_traceback_context,
)
from augment.python.prompt.packets import source_outline
from augment.python.prompt.prompts import (
    render_coverage_segment_feedback_prompt,
    render_coverage_segment_prompt,
)
from augment.python.prompt.proposal import parse_segment_response
from augment.python.run.candidate import (
    CandidateAttempt,
    context_broker,
    failure_row,
    persist_accepted,
    resolve_context,
    round_test_file_suffix,
    round_test_name_suffix,
    validate_candidate,
)
from augment.python.run.runtime import RunContext, SampleContext
from augment.python.strategy import is_contract_directed
from common.utils.python.json_io import write_json

TEST_COMMAND = ("python", "-m", "pytest", "-q", "<generated-nodeid-or-file>")


def run_coverage_segment(context: RunContext, sample: SampleContext) -> dict[str, Any]:
    """Generate and validate one test for an immutable coverage segment.

    The model may request one deterministic context batch. An unsuccessful
    candidate receives at most one measured repair message.
    """

    packet = build_segment_packet(context, sample)
    contract_directed = is_contract_directed(context.options.strategy)
    prompt = render_coverage_segment_prompt(packet, strategy=context.options.strategy)
    sample.sample_dir.mkdir(parents=True, exist_ok=True)
    write_json(sample.sample_dir / "packet.json", packet)
    write_json(sample.sample_dir / "retrieved_context.json", [])
    (sample.sample_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    messages = [{"role": "user", "content": prompt}]
    base = segment_base_row(context, sample)

    try:
        response = complete_conversation(context, sample, messages, call_index=1)
        if response["action"] == "request_context":
            if not contract_directed:
                raise SystemExit(
                    "context requests are disabled in contract_agnostic mode"
                )
            retrieved = resolve_context(
                response["requests"],
                project_root=context.current_root,
                coverage_source=context.options.coverage_source,
                out_path=sample.sample_dir / "retrieved_context.json",
                visible_context=packet["source_context"],
            )
            messages.append(
                {
                    "role": "user",
                    "content": context_response_message(retrieved),
                }
            )
            response = complete_conversation(context, sample, messages, call_index=2)
        proposal = require_proposal(response)
    except SystemExit as exc:
        row = phase_failure(base, sample, "generation_failed", exc)
    else:
        row = validate_candidate(
            context,
            sample,
            proposal,
            CandidateAttempt(sample.sample_dir, sample.sample_id, base),
        )
        row = require_segment_gain(row)
    if row.get("status") == "accepted":
        return persist_accepted(context, row)

    repair_dir = sample.sample_dir / "repair"
    traceback_context = traceback_for_repair(context, row) if contract_directed else []
    feedback = segment_feedback(sample.objective, row)
    failure_packet = {
        "failure": feedback,
        "project_frames": traceback_context,
    }
    repair_prompt = render_coverage_segment_feedback_prompt(
        feedback=feedback,
        traceback_context=traceback_context,
        context_request_limit=context.options.effective_repair_context_requests,
        strategy=context.options.strategy,
    )
    repair_dir.mkdir(parents=True, exist_ok=True)
    write_json(repair_dir / "feedback.json", feedback)
    write_json(repair_dir / "traceback_context.json", traceback_context)
    write_json(repair_dir / "failure_packet.json", failure_packet)
    write_json(repair_dir / "retrieved_context.json", [])
    (repair_dir / "feedback.md").write_text(repair_prompt, encoding="utf-8")
    messages.append({"role": "user", "content": repair_prompt})
    try:
        repaired = complete_conversation(
            context,
            sample,
            messages,
            call_index=len([item for item in messages if item["role"] == "assistant"])
            + 1,
            raw_dir=repair_dir,
        )
        write_json(
            repair_dir / "decision.json",
            {
                "action": repaired.get("action", ""),
                "diagnosis": repaired.get("diagnosis", ""),
                "request_count": len(repaired.get("requests", [])),
            },
        )
        if repaired.get("action") == "request_context":
            request_limit = context.options.effective_repair_context_requests
            if request_limit <= 0:
                raise SystemExit("repair-time context requests are disabled")
            retrieved = resolve_context(
                repaired["requests"][:request_limit],
                project_root=context.current_root,
                coverage_source=context.options.coverage_source,
                out_path=repair_dir / "retrieved_context.json",
                visible_context=[*packet["source_context"], *traceback_context],
            )
            messages.append(
                {
                    "role": "user",
                    "content": context_response_message(retrieved),
                }
            )
            repaired = complete_conversation(
                context,
                sample,
                messages,
                call_index=len(
                    [item for item in messages if item["role"] == "assistant"]
                )
                + 1,
                raw_dir=repair_dir,
            )
        proposal = require_proposal(repaired)
    except SystemExit as exc:
        write_json(
            repair_dir / "phase_error.json",
            {"status": "repair_generation_failed", "error": str(exc)},
        )
        return {
            **row,
            "repair_status": "repair_generation_failed",
            "repair_error": str(exc),
        }

    row = validate_candidate(
        context,
        sample,
        proposal,
        CandidateAttempt(
            repair_dir,
            sample.repair_sample_id(),
            base | {"prompt_path": str(repair_dir / "feedback.md")},
        ),
    )
    row = require_segment_gain(row)
    return persist_accepted(context, row)


def build_segment_packet(context: RunContext, sample: SampleContext) -> dict[str, Any]:
    """Build the compact, model-visible packet for one coverage segment."""

    objective = sample.objective
    filepath = str(objective["filepath"])
    text = (context.current_root / filepath).read_text(
        encoding="utf-8", errors="replace"
    )
    source_context = [
        code_excerpt_from_text(
            filepath,
            text,
            start_line=int(objective["start_line"]),
            end_line=int(objective["end_line"]),
        ).to_dict()
    ]
    for item in objective.get("segment", {}).get("context_ranges", []):
        source_context.append(
            code_excerpt_from_text(
                filepath,
                text,
                start_line=int(item["start_line"]),
                end_line=int(item["end_line"]),
            ).to_dict()
        )
    gap = objective.get("general_coverage", {})
    return {
        "project": context.options.project,
        "round": sample.round_index,
        "test_name_suffix": round_test_name_suffix(sample.round_index),
        "test_file_suffix": round_test_file_suffix(sample.round_index),
        "objective": {
            "objective_id": objective["objective_id"],
            "filepath": filepath,
            "start_line": objective["start_line"],
            "end_line": objective["end_line"],
            "unit": objective["unit"],
            "round_missing_lines": gap.get("uncovered_lines", []),
            "round_missing_branches": gap.get("uncovered_branches", []),
        },
        "source_context": source_context,
        "source_imports": top_level_imports(filepath, text),
        "source_outline": source_outline(context.current_root, filepath),
        "constraints": [
            *context.options.constraints,
            "Generated tests must be deterministic.",
            "Do not call live models, networks, external services, or real "
            "API-key-backed providers.",
        ],
        "test_command": list(TEST_COMMAND),
    }


def top_level_imports(filepath: str, text: str) -> list[str]:
    """Return exact top-level import statements in source order."""

    try:
        tree = ast.parse(text, filename=filepath)
    except SyntaxError:
        return []
    return [
        source
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and (source := ast.get_source_segment(text, node))
    ]


def complete_conversation(
    context: RunContext,
    sample: SampleContext,
    messages: list[dict[str, str]],
    *,
    call_index: int,
    raw_dir: Path | None = None,
) -> dict[str, Any]:
    """Persist and complete one turn of the segment conversation."""

    raw_dir = raw_dir or sample.sample_dir
    content = context.model.complete_messages(
        messages,
        raw_path=raw_dir / f"response_{call_index:03d}.raw.json",
    )
    messages.append({"role": "assistant", "content": content})
    write_json(sample.sample_dir / "conversation.json", {"messages": messages})
    return parse_segment_response(content)


def context_response_message(retrieved: list[dict[str, Any]]) -> str:
    return (
        "Deterministically resolved project context follows. Return a propose_test "
        "object now; do not request more context.\n"
        + json.dumps(retrieved, indent=2, sort_keys=True)
    )


def require_proposal(response: dict[str, Any]) -> dict[str, Any]:
    if response.get("action") != "propose_test":
        raise SystemExit("only one context request batch is allowed")
    proposal = response.get("proposal")
    if not isinstance(proposal, dict):
        raise SystemExit("segment response is missing a test proposal")
    return proposal


def require_segment_gain(row: dict[str, Any]) -> dict[str, Any]:
    """Reject a passing candidate that misses every round-start residual target."""

    if row.get("status") != "accepted":
        return row
    delta = row.get("coverage_delta", {})
    if int(delta.get("covered_lines") or 0) + int(delta.get("covered_branches") or 0):
        return row
    measured_path = str(row.get("accepted_coverage_path") or "")
    return {
        **row,
        "status": "no_segment_coverage",
        "error": (
            "passing tests covered none of the segment's round-start residual targets"
        ),
        "measured_coverage_path": measured_path,
        "accepted_coverage_path": "",
    }


def segment_feedback(objective: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    gap = objective.get("general_coverage", {})
    return {
        "status": row.get("status", ""),
        "error": row.get("error", ""),
        "failure_output": failure_text_from_row(row),
        "measured_segment_delta": row.get("coverage_delta", {}),
        "round_missing_lines": gap.get("uncovered_lines", []),
        "round_missing_branches": gap.get("uncovered_branches", []),
    }


def traceback_for_repair(
    context: RunContext, row: dict[str, Any]
) -> list[dict[str, Any]]:
    broker = context_broker(context.current_root, context.options.coverage_source)
    return (
        project_traceback_context(failure_text_from_row(row), broker)
        if broker is not None
        else []
    )


def segment_base_row(context: RunContext, sample: SampleContext) -> dict[str, Any]:
    return {
        "run_id": context.run_dir.name,
        "round": sample.round_index,
        "objective_id": sample.objective["objective_id"],
        "packet_path": str(sample.sample_dir / "packet.json"),
        "conversation_path": str(sample.sample_dir / "conversation.json"),
        "retrieved_context_path": str(sample.sample_dir / "retrieved_context.json"),
        "prompt_path": str(sample.sample_dir / "prompt.md"),
    }


def phase_failure(
    base: dict[str, Any],
    sample: SampleContext,
    status: str,
    exc: SystemExit,
    phase_dir: Path | None = None,
) -> dict[str, Any]:
    directory = phase_dir or sample.sample_dir
    write_json(directory / "phase_error.json", {"status": status, "error": str(exc)})
    return failure_row(base, sample.objective, status, str(exc))
