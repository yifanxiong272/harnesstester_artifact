"""Plan target probes, resolve requested context, and parse generated assets."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from common.utils.python.json_io import write_json
from probe.python.models import ProbeAsset
from probe.python.prompt.context_index import resolve_context_requests
from probe.python.prompt.prompts import (
    render_target_probe_implementation_prompt,
    render_target_probe_plan_prompt,
)
from probe.python.prompt.proposal import parse_probe_plan, parse_proposal_partial
from probe.python.run.client import message_content
from probe.python.run.deadline import CaseBudgetExceeded
from probe.python.run.options import is_discovery, primary_checkout, strategy_profile
from probe.python.run.reporting import (
    compact_text,
    buggy_outcome_category,
    latest_outcome_category,
)
from probe.python.run.session import complete_and_record

if TYPE_CHECKING:
    from probe.python.run.session import TargetProbeRuntime


DIRECT_PROMPT_STYLE = "direct"
STRICT_PROMPT_STYLE = "strict"


class InvalidModelOutputError(ValueError):
    """Model output failed the plan or proposal contract."""


@dataclass(frozen=True)
class SampleProbeProposal:
    path: Path
    assets: list[Any]


def generate_probe_assets(
    *,
    runtime: TargetProbeRuntime,
    packet: dict[str, Any],
    plan: dict[str, Any],
    sample_dir: Path,
    prior_attempts: list[dict[str, Any]],
    prompt_style: str,
) -> SampleProbeProposal:
    """Ask the model for independent pytest assets and parse its JSON response."""

    implementation_prompt = render_target_probe_implementation_prompt(
        packet,
        plan=plan,
        prior_attempts=prior_attempts,
        direct=prompt_style == DIRECT_PROMPT_STYLE,
        max_assets=runtime.options.assets_per_sample,
    )
    (sample_dir / "implementation.prompt.md").write_text(
        implementation_prompt, encoding="utf-8"
    )
    response = complete_and_record(
        runtime, implementation_prompt, sample_dir / "implementation.raw.json"
    )

    try:
        proposal, parse_errors = parse_proposal_partial(
            message_content(response),
            max_assets=runtime.options.assets_per_sample,
            allowed_test_roots=packet.get("generated_test_roots"),
            canonical_plan=plan,
            public_entrypoints=packet_public_entrypoints(packet),
        )
    except (Exception, SystemExit) as exc:
        if isinstance(exc, CaseBudgetExceeded):
            raise
        raise InvalidModelOutputError(str(exc)) from exc
    proposal_data = proposal.to_dict()
    if not proposal_data.get("boundary_plan") and plan.get("boundary_plan"):
        proposal_data["boundary_plan"] = plan["boundary_plan"]
    if parse_errors:
        proposal_data["parse_errors"] = parse_errors

    # Parsed assets inherit target/focus membership from the validated plan.
    assets, dropped_duplicate_assets = filter_semantic_duplicates(
        proposal.assets, prior_attempts
    )
    if dropped_duplicate_assets:
        proposal_data["dropped_duplicate_assets"] = dropped_duplicate_assets

    proposal_path = sample_dir / "proposal.json"
    write_json(proposal_path, proposal_data)
    return SampleProbeProposal(proposal_path, assets)


def filter_semantic_duplicates(
    assets: list[Any],
    prior_attempts: list[dict[str, Any]],
) -> tuple[list[Any], list[dict[str, str]]]:
    seen = prior_semantic_fingerprints(prior_attempts)
    kept = []
    dropped = []
    for asset in assets:
        fingerprint = semantic_fingerprint(asset)
        if fingerprint in seen:
            dropped.append(
                {"asset_id": asset.asset_id, "semantic_fingerprint": fingerprint}
            )
            continue
        seen.add(fingerprint)
        kept.append(asset)
    return kept, dropped


def prior_semantic_fingerprints(prior_attempts: list[dict[str, Any]]) -> set[str]:
    fingerprints: set[str] = set()
    for attempt in prior_attempts:
        fingerprint = str(attempt.get("semantic_fingerprint") or "")
        if fingerprint:
            fingerprints.add(fingerprint)
        fingerprints.update(
            str(item) for item in attempt.get("semantic_fingerprints", []) if item
        )
    return fingerprints


def semantic_fingerprint(asset: Any) -> str:
    if isinstance(asset, ProbeAsset):
        asset = asset.to_dict()

    def normalized(value: Any) -> str:
        return compact_text(value, 1000).lower()

    def field(name: str, default: Any = "") -> Any:
        if isinstance(asset, dict):
            return asset.get(name, default)
        return getattr(asset, name, default)

    payload = {
        "target_unit_ids": sorted(str(item) for item in field("target_unit_ids", [])),
        "public_entrypoint_id": normalized(field("public_entrypoint_id")),
        "test_intent": normalized(field("test_intent")),
        "activation_conditions": [
            normalized(item) for item in field("activation_conditions", [])
        ],
        "independent_oracle": normalized(field("independent_oracle")),
        "input_construction": normalized(field("input_construction")),
        "primary_oracle": normalized(
            field("primary_oracle") or field("observable_oracle")
        ),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


def generate_target_plan_and_context(
    *,
    runtime: TargetProbeRuntime,
    packet: dict[str, Any],
    sample_dir: Path,
    prior_attempts: list[dict[str, Any]],
    prompt_style: str,
) -> dict[str, Any]:
    """Ask for a boundary plan, then resolve its exact context requests."""

    allow_context = strategy_profile(runtime.options.strategy).allow_context
    max_context_requests = (
        max(0, int(runtime.options.context_requests or 0)) if allow_context else 0
    )
    prompt = render_target_probe_plan_prompt(
        packet,
        prior_attempts=prior_attempts,
        direct=prompt_style == DIRECT_PROMPT_STYLE,
    )
    prompt_path = sample_dir / "plan.prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    response = complete_and_record(runtime, prompt, sample_dir / "plan.raw.json")
    try:
        plan_data, parse_errors = parse_probe_plan(
            message_content(response),
            max_context_requests=max_context_requests,
        )
        validate_boundary_plan(packet, plan_data)
    except (Exception, SystemExit) as exc:
        if isinstance(exc, CaseBudgetExceeded):
            raise
        raise InvalidModelOutputError(str(exc)) from exc
    if parse_errors:
        plan_data["parse_errors"] = parse_errors
    write_json(sample_dir / "plan.json", plan_data)
    # Context resolution is deterministic and scoped to the target checkout.
    # Missing or out-of-scope requests are recorded rather than replaced with a
    # heuristic fallback.
    context = (
        resolve_context_for_manifest(
            manifest=runtime.manifest,
            requests=plan_data["context_requests"],
            max_requests=max_context_requests,
            out_path=sample_dir / "retrieved-context.json",
        )
        if allow_context
        else {"requests": []}
    )
    packet["retrieved_context"] = context
    return plan_data


def validate_boundary_plan(packet: dict[str, Any], plan: dict[str, Any]) -> None:
    """Check a parsed plan's target, focus, and public-entrypoint membership."""
    allowed = {
        str(unit.get("unit_id") or "") for unit in packet.get("target_units", [])
    }
    focus = str(packet.get("focus_target_unit_id") or "")
    entrypoints = packet_public_entrypoints(packet)
    for boundary in plan["boundary_plan"]:
        boundary_id = boundary["boundary_id"]
        target_unit_ids = boundary["target_unit_ids"]
        unknown = [unit_id for unit_id in target_unit_ids if unit_id not in allowed]
        if unknown:
            raise SystemExit(
                f"boundary {boundary_id} references unknown target_unit_ids: {unknown}"
            )
        if focus and focus not in target_unit_ids:
            raise SystemExit(
                f"boundary {boundary_id} does not include focused target unit {focus}"
            )
        entrypoint_id = boundary["route"]["entrypoint_id"]
        entrypoint = next(
            (item for item in entrypoints if item.get("entrypoint_id") == entrypoint_id),
            None,
        )
        if entrypoint is None:
            raise SystemExit(
                f"boundary {boundary_id} references unavailable public entrypoint: "
                f"{entrypoint_id or '<missing>'}"
            )
        if entrypoint.get("target_unit_id") not in target_unit_ids:
            raise SystemExit(
                f"boundary {boundary_id} public entrypoint does not reach a selected target unit"
            )


def packet_public_entrypoints(packet: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {**entrypoint, "target_unit_id": target.get("target_unit_id")}
        for target in (packet.get("public_target_routes") or {}).get("targets", [])
        for entrypoint in target.get("entrypoints", [])
        if isinstance(entrypoint, dict)
    ]


def resolve_context_for_manifest(
    *,
    manifest: dict[str, Any],
    requests: list[dict[str, Any]],
    max_requests: int,
    out_path: Path,
) -> dict[str, Any]:
    """Resolve model-requested context against the active target checkout."""

    checkout = primary_checkout(manifest).get("path")
    source_roots = manifest.get("source_roots", [])
    source = (
        "target-revision exact context requests"
        if is_discovery(manifest.get("evaluation_mode"))
        else "buggy-side exact context requests"
    )
    if not checkout or not isinstance(source_roots, list):
        resolved = {
            "source": source,
            "requests": [],
            "error": "missing_checkout_or_source_roots",
        }
    else:
        resolved = resolve_context_requests(
            project_root=Path(str(checkout)),
            source_roots=[str(root) for root in source_roots],
            requests=requests,
            max_requests=max_requests,
            source=source,
        )
    write_json(out_path, resolved)
    return resolved


def prior_attempt_ledger(
    rows: list[dict[str, Any]],
    *,
    max_items: int = 18,
    evaluation_mode: str | None = None,
) -> list[dict[str, Any]]:
    families: dict[str, dict[str, Any]] = {}
    discovery = is_discovery(evaluation_mode)
    outcome_key = "latest_outcomes" if discovery else "buggy_outcomes"
    for row in rows:
        for asset in row.get("assets", []):
            if not isinstance(asset, dict):
                continue
            fingerprint = str(asset.get("semantic_fingerprint") or "")
            if not fingerprint and asset.get("input_construction"):
                fingerprint = semantic_fingerprint(asset)
            if not fingerprint:
                continue
            target_unit_ids = sorted(
                str(item) for item in asset.get("target_unit_ids", [])
            )
            oracle_family = compact_text(
                asset.get("oracle_family")
                or asset.get("primary_oracle")
                or asset.get("observable_oracle")
                or asset.get("independent_oracle")
                or asset.get("test_intent")
                or f"unclassified-{fingerprint[:12]}",
                260,
            )
            family_key = "\0".join(target_unit_ids + [oracle_family.lower()])
            family = families.get(family_key) or {
                "family_id": f"family-{hashlib.sha256(family_key.encode()).hexdigest()[:12]}",
                "target_unit_ids": target_unit_ids,
                "oracle_family": oracle_family,
                "representative_intent": compact_text(
                    asset.get("test_intent", ""), 180
                ),
                "attempt_count": 0,
                outcome_key: {},
                "semantic_fingerprints": [],
            }
            family["attempt_count"] += 1
            outcome = (
                latest_outcome_category(asset)
                if discovery
                else buggy_outcome_category(asset)
            )
            counts = family[outcome_key]
            counts[outcome] = counts.get(outcome, 0) + 1
            if fingerprint not in family["semantic_fingerprints"]:
                family["semantic_fingerprints"].append(fingerprint)
            families.pop(family_key, None)
            families[family_key] = family
    return list(families.values())[-max_items:]
