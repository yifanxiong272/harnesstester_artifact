#!/usr/bin/env python3
"""Render prompt templates and enforce prompt-safe packet projection."""

from __future__ import annotations

import json
from pathlib import Path
from string import Template
from typing import Any

from probe.python.run.options import (
    TARGET_PROBE_LDH_STRATEGY,
    normalize_target_strategy,
    strategy_profile,
)

TEMPLATE_ROOT = Path(__file__).resolve().parent / "templates"


def render_target_probe_plan_prompt(
    packet: dict[str, Any],
    *,
    prior_attempts: list[dict[str, Any]] | None = None,
    direct: bool = False,
) -> str:
    """Render the boundary-planning prompt for one focused packet."""

    return render_template(
        "target_probe_direct_plan" if direct else "target_probe_plan",
        strategy_guidance=target_guidance(packet, direct=direct),
        packet_json=prompt_packet(packet),
        prior_attempts_json=prompt_prior_attempts(prior_attempts),
        **plan_context_instructions(packet, direct=direct),
    )


def render_target_probe_implementation_prompt(
    packet: dict[str, Any],
    *,
    plan: dict[str, Any],
    prior_attempts: list[dict[str, Any]] | None = None,
    max_assets: int = 5,
    direct: bool = False,
) -> str:
    """Render the probe-implementation prompt for one sample."""

    return render_template(
        "target_probe_direct_implementation"
        if direct
        else "target_probe_implementation",
        strategy_guidance=target_guidance(packet, direct=direct),
        packet_json=prompt_packet(packet),
        plan_json=plan,
        prior_attempts_json=prompt_prior_attempts(prior_attempts),
        max_assets=max(1, int(max_assets)),
        generated_test_file_example=generated_test_file_example(packet),
    )


def render_template(name: str, **values: Any) -> str:
    """Serialize JSON slots once and preserve the template's text and whitespace."""
    path = TEMPLATE_ROOT / f"{name}_prompt.md"
    values = {
        key: json.dumps(value, indent=2) if key.endswith("_json") else value
        for key, value in values.items()
    }
    return (
        Template(path.read_text(encoding="utf-8")).safe_substitute(values).rstrip()
        + "\n"
    )


def render_target_probe_minimize_prompt(
    packet: dict[str, Any],
    *,
    asset: dict[str, Any],
    buggy_summary: dict[str, Any],
    retry_context: dict[str, Any] | None = None,
) -> str:
    return render_template(
        "target_probe_minimize",
        packet_json=prompt_packet(packet),
        asset_json=asset,
        buggy_summary_json=buggy_summary,
        retry_context_section=minimization_retry_context_section(retry_context),
        generated_test_file_example=generated_test_file_example(packet),
    )


def render_target_harness_repair_context_request_prompt(
    packet: dict[str, Any],
    *,
    plan: dict[str, Any],
    asset: dict[str, Any],
    buggy_summary: dict[str, Any],
    traceback_context: list[dict[str, Any]],
    max_context_requests: int,
) -> str:
    return render_template(
        "target_harness_repair_context_request",
        packet_json=prompt_packet(packet, include_module_imports=True),
        plan_json=plan,
        asset_json=asset,
        buggy_summary_json=buggy_summary,
        traceback_context_json=traceback_context,
        context_request_section=f"""Request at most {max_context_requests} exact context item(s):

```json
{{
  \"action\": \"request_context\",
  \"diagnosis\": \"evidence-based root cause and missing contract\",
  \"requests\": [
    {{
      \"kind\": \"module_context|class_definition|function_definition|symbol_definition\",
      \"filepath\": \"src/pkg/module.py\",
      \"qualname\": \"ClassName\",
      \"reason\": \"needed to repair constructor, fixture, mock contract, or payload shape\"
    }}
  ]
}}
```"""
        if max_context_requests > 0
        else "Repair-time context requests are disabled for this run.",
        generated_test_file_example=generated_test_file_example(packet),
    )


def render_target_harness_repair_prompt(
    packet: dict[str, Any],
    *,
    plan: dict[str, Any],
    asset: dict[str, Any],
    buggy_summary: dict[str, Any],
    traceback_context: list[dict[str, Any]],
    repair_context: dict[str, Any],
) -> str:
    return render_template(
        "target_harness_repair",
        packet_json=prompt_packet(packet, include_module_imports=True),
        plan_json=plan,
        asset_json=asset,
        buggy_summary_json=buggy_summary,
        traceback_context_json=traceback_context,
        repair_context_json=repair_context,
        generated_test_file_example=generated_test_file_example(packet),
    )


def render_target_contract_agnostic_repair_prompt(
    packet: dict[str, Any],
    *,
    plan: dict[str, Any],
    asset: dict[str, Any],
    buggy_summary: dict[str, Any],
) -> str:
    return render_template(
        "target_contract_agnostic_repair",
        packet_json=prompt_packet(packet),
        plan_json=plan,
        asset_json=asset,
        buggy_summary_json=buggy_summary,
        generated_test_file_example=generated_test_file_example(packet),
    )


def plan_context_instructions(
    packet: dict[str, Any], *, direct: bool = False
) -> dict[str, str]:
    profile = strategy_profile(
        str(packet.get("strategy") or TARGET_PROBE_LDH_STRATEGY)
    )
    if not profile.allow_context:
        return {
            "context_request_instruction": '- Use only the supplied packet; additional context retrieval is unavailable.\n  Return "context_requests": [].',
            "context_request_example": "[]",
        }
    return {
        "context_request_instruction": (
            "- Request exact target-revision context only when it is essential for the planned\n"
            "  setup or public contract. Otherwise use an empty request list."
            if direct
            else "- Request at most the allowed exact target-revision context when it is necessary\n"
            "  for setup, public contracts, payload shape, or collaborator shape. Requests\n"
            "  use a project-relative `filepath` and exact AST `qualname` except for\n"
            "  `module_context`."
        ),
        "context_request_example": """[
    {
      "kind": "module_context|class_definition|function_definition|symbol_definition",
      "filepath": "src/pkg/module.py",
      "qualname": "ClassName.method",
      "reason": "exact context needed for this probe"
    }
  ]""",
    }


def prompt_packet(
    packet: dict[str, Any], *, include_module_imports: bool = False
) -> dict[str, Any]:
    """Project the audit packet to prompt-safe fields."""

    profile = strategy_profile(
        str(packet.get("strategy") or TARGET_PROBE_LDH_STRATEGY)
    )
    safe_units = []
    for unit in packet.get("target_units", []):
        safe_units.append(
            {
                "unit_id": unit.get("unit_id"),
                "filepath": unit.get("filepath"),
                "qualname": unit.get("qualname"),
                "kind": unit.get("kind"),
                "code": unit.get("code", ""),
            }
        )
    # This projection is the last guard before a model call. It includes target
    # code and prompt-safe context, but omits revisions, patch hunks, fixed-side
    # data, local filesystem paths, and other audit-only fields.
    payload = {
        "project": packet.get("project"),
        "target_units": safe_units,
        "source_file_index": packet.get("source_file_index", []),
        "existing_tests": packet.get("existing_tests", []),
        # Static target import/export metadata is shared by every strategy.
        "module_contracts": packet.get("module_contracts", []),
        "public_target_routes": packet.get("public_target_routes", {}),
        "generated_test_roots": packet.get("generated_test_roots", []),
        "constraints": packet.get("constraints", []),
    }
    if packet.get("lane"):
        payload["lane"] = packet.get("lane")
    if include_module_imports and profile.allow_context:
        # Module imports are withheld from normal generation and added only for
        # harness repair, where import/setup failures need exact setup context.
        payload["module_imports"] = packet.get("module_imports", [])
    if packet.get("focus_target_unit_id"):
        payload["focus_target_unit_id"] = packet.get("focus_target_unit_id")
        payload["focus_sample_index"] = packet.get("focus_sample_index")
        payload["focus_total_target_units"] = packet.get("focus_total_target_units")
    if profile.allow_context and has_retrieved_context(packet):
        payload["retrieved_context"] = packet["retrieved_context"]
    if packet.get("boundary_plan"):
        payload["boundary_plan"] = packet["boundary_plan"]
    if packet.get("whole_target_pass"):
        payload["whole_target_pass"] = True
        payload["soft_sample_index"] = packet.get("soft_sample_index")
    return payload


def has_retrieved_context(packet: dict[str, Any]) -> bool:
    context = packet.get("retrieved_context")
    if not isinstance(context, dict):
        return False
    return any(
        item.get("status") == "found"
        for item in context.get("requests", [])
        if isinstance(item, dict)
    )


def prompt_prior_attempts(
    prior_attempts: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Remove internal exact-deduplication data from the model-facing ledger."""

    projected = []
    for attempt in prior_attempts or []:
        item = {
            key: value
            for key, value in attempt.items()
            if key
            not in {
                "semantic_fingerprint",
                "semantic_fingerprints",
                "buggy_outcomes",
                "latest_outcomes",
            }
        }
        outcomes = attempt.get("latest_outcomes") or attempt.get("buggy_outcomes")
        if outcomes:
            item["target_outcomes"] = outcomes
        projected.append(item)
    return projected


def generated_test_file_example(packet: dict[str, Any]) -> str:
    roots = packet.get("generated_test_roots")
    root = (
        str(roots[0])
        if isinstance(roots, list) and roots
        else "tests/generated/benchmarkbr"
    )
    return f"{root.rstrip('/')}/test_generated_target_probe_asset_001.py"


def target_guidance(packet: dict[str, Any], *, direct: bool = False) -> str:
    """Return strategy-aware target-probing guidance."""

    strategy = normalize_target_strategy(
        str(packet.get("strategy") or TARGET_PROBE_LDH_STRATEGY)
    )
    guidance = shared_guidance(direct=direct)
    if strategy == TARGET_PROBE_LDH_STRATEGY:
        guidance += "\n\n" + ldh_method_guidance()
    return guidance


def shared_guidance(*, direct: bool = False) -> str:
    """Return strategy-neutral target-boundary probing guidance."""

    guidance = (
        "Generate deterministic tests whose purpose is to reveal a defect, not "
        "merely to pass on the target revision. Exercise the provided target "
        "units through their declared public entrypoints. Treat target code as "
        "reachability and failure-hypothesis evidence, never as the authority "
        "that defines expected behavior. Derive one independently justified "
        "public or stable semantic invariant and assert one externally "
        "observable consequence. Probe defensible boundary conditions even when "
        "the expected behavior differs from the current implementation. Choose "
        "the strongest route autonomously without forcing a specific bug pattern "
        "or testing technique."
    )
    if direct:
        guidance += (
            " In the direct lane, minimize harness complexity while preserving "
            "the complete causal route."
        )
    return guidance


def ldh_method_guidance() -> str:
    """Return lightweight LDH-only method guidance."""

    return (
        "As an additional discovery aid, consider how values produced, shaped, "
        "or interpreted through model or agent interactions propagate into target "
        "behavior, and use those flows to identify defensible perturbations and "
        "observable invariants. This perspective must not displace the primary "
        "deterministic bug-reveal objective, target reachability, independent "
        "oracle quality, determinism, or a stronger alternative route; keep target "
        "behavior real and mock only necessary external or nondeterministic boundaries."
    )


def minimization_retry_context_section(retry_context: dict[str, Any] | None) -> str:
    if not retry_context:
        return ""
    return (
        "\n## Preserve-Failure Retry Context\n\n"
        "The previous minimization did not preserve the target-revision failure. "
        "Preserve the original target call and failure-inducing input more "
        "carefully while continuing to delete statements only.\n\n"
        "```json\n" + json.dumps(retry_context, indent=2) + "\n```\n"
    )
