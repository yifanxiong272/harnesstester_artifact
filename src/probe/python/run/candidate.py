"""Validate generated probe assets on isolated project revisions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from common.utils.python.json_io import write_json
from probe.python.run.deadline import CaseBudgetExceeded
from probe.python.run.generation import semantic_fingerprint
from probe.python.run.repair import (
    minimize_asset,
    repair_disposition,
    repair_harness_asset,
    skipped_harness_repair_record,
)
from probe.python.run.reporting import validation_status
from probe.python.run.session import AssetValidationState, validate_buggy_asset
from probe.python.run.options import is_discovery, strategy_profile

if TYPE_CHECKING:
    from probe.python.run.session import TargetProbeRuntime


@dataclass(frozen=True)
class EvaluatedVariant:
    """Candidate state and its paired-validation evidence."""

    state: AssetValidationState
    record: dict[str, Any]


def run_sample_assets(
    *,
    runtime: TargetProbeRuntime,
    packet: dict[str, Any],
    plan: dict[str, Any],
    sample_dir: Path,
    assets: list[Any],
    minimization_budget: int,
    harness_repair_budget: int,
    on_progress: Callable[[list[dict[str, Any]]], Any] | None = None,
) -> list[dict[str, Any]]:
    """Validate every generated asset independently within one sample."""

    rows = []
    minimizations_used = 0
    harness_repairs_used = 0
    for asset in assets:
        asset_dir = sample_dir / "assets" / asset.asset_id
        try:
            minimization_allowed = minimizations_used < minimization_budget
            harness_repair_allowed = harness_repairs_used < harness_repair_budget
            row = run_target_asset(
                runtime=runtime,
                packet=packet,
                plan=plan,
                asset=asset,
                asset_dir=asset_dir,
                minimization_allowed=minimization_allowed,
                harness_repair_allowed=harness_repair_allowed,
                on_result=(lambda row: on_progress([*rows, row])) if on_progress else None,
            )
            if row.get("minimization", {}).get("called"):
                minimizations_used += 1
            if row.get(strategy_profile(runtime.options.strategy).repair_key, {}).get(
                "called"
            ):
                harness_repairs_used += 1
            rows.append(row)
        except (Exception, SystemExit) as exc:
            if isinstance(exc, CaseBudgetExceeded):
                raise
            rows.append(asset_error(asset_dir, exc, asset_id=asset.asset_id))
        if on_progress:
            on_progress(rows)
    return rows


def run_target_asset(
    *,
    runtime: TargetProbeRuntime,
    packet: dict[str, Any],
    plan: dict[str, Any],
    asset: Any,
    asset_dir: Path,
    minimization_allowed: bool,
    harness_repair_allowed: bool,
    on_result: Callable[[dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    """Validate the original asset and any additive repair/minimization variants."""

    if is_discovery(runtime.options.evaluation_mode):
        from .discovery import run_discovery_asset

        return run_discovery_asset(
            runtime=runtime,
            packet=packet,
            plan=plan,
            asset=asset,
            asset_dir=asset_dir,
            minimization_allowed=minimization_allowed,
            harness_repair_allowed=harness_repair_allowed,
            on_result=on_result,
        )

    asset_dir.mkdir(parents=True, exist_ok=True)
    # Parsed assets carry the validated plan's canonical boundary metadata.
    base_state = validate_buggy_asset(runtime, asset, asset_dir)
    base_classification = repair_disposition(base_state.buggy["summary"])
    harness_repair: dict[str, Any] = {}

    if validation_status(base_state.buggy["summary"]) == "passed":
        row = asset_result_row(
            base_state,
            minimization={},
            original_asset=asset,
            harness_repair={},
        )
        return {**row, "status": "buggy_passed", "bug_revealed": False}

    variants = [validate_fixed_state(runtime=runtime, state=base_state, variant="base")]
    base_revealed = variants[0].record["bug_revealed"]
    if not base_revealed and base_classification["needs_repair"]:
        harness_repair = (
            repair_harness_asset(
                runtime=runtime,
                packet=packet,
                plan=plan,
                state=base_state,
            )
            if harness_repair_allowed
            else skipped_harness_repair_record(base_classification)
        )
        repaired_state = harness_repair.get("state")
        if repaired_state is not None:
            if is_buggy_non_pass(repaired_state.buggy["summary"]):
                variants.append(
                    validate_fixed_state(
                        runtime=runtime, state=repaired_state, variant="repaired"
                    )
                )

    chosen = next(
        (candidate for candidate in variants if candidate.record["bug_revealed"]),
        next(
            (candidate for candidate in variants if candidate.record["raw_reveal"]),
            variants[0],
        ),
    )
    minimization: dict[str, Any] = {}

    def result_row():
        row = asset_result_row(
            chosen.state,
            minimization=minimization,
            original_asset=asset,
            harness_repair=harness_repair,
        )
        row["fixed"] = chosen.record["fixed"]
        row["fixed_variants"] = [item.record for item in variants]
        row["status"] = chosen.record["status"]
        row["bug_revealed"] = chosen.record["bug_revealed"]
        row["raw_reveal"] = any(item.record.get("raw_reveal") for item in variants)
        if "harness_repair" in row:
            row[strategy_profile(runtime.options.strategy).repair_key] = row.pop(
                "harness_repair"
            )
        return row

    if chosen.record["bug_revealed"]:
        # Persist confirmed evidence before optional work can exhaust the budget.
        if on_result:
            on_result(result_row())
        minimization = minimize_asset(
            runtime=runtime,
            packet=packet,
            plan=plan,
            state=chosen.state,
            enabled=minimization_allowed,
        )
        if (
            minimization.get("record", {}).get("use_minimized")
            and minimization.get("state") is not None
        ):
            minimized = validate_fixed_state(
                runtime=runtime, state=minimization["state"], variant="minimized"
            )
            variants.append(minimized)
            if minimized.record["bug_revealed"]:
                chosen = minimized

    return result_row()


def validate_fixed_state(
    *,
    runtime: TargetProbeRuntime,
    state: AssetValidationState,
    variant: str,
) -> EvaluatedVariant:
    fixed = runtime.validation.run(
        revision_kind="fixed",
        proposal=state.asset,
        proposal_path=state.proposal_path,
        sample_dir=state.sample_dir,
    )
    record = fixed_variant_record(variant, state, fixed)
    if record["raw_reveal"]:
        confirmation = confirm_reveal_candidate(
            runtime=runtime, state=state, variant=variant
        )
        record["confirmation"] = confirmation
        record["bug_revealed"] = confirmation["stable"]
        record["status"] = "revealed" if confirmation["stable"] else "unstable_reveal"
    return EvaluatedVariant(state, record)


def fixed_variant_record(
    variant: str, state: AssetValidationState, fixed: dict[str, Any]
) -> dict[str, Any]:
    """Return a compact record for one fixed-side validation variant."""

    fixed_summary = fixed["summary"]
    raw_reveal = (
        is_buggy_non_pass(state.buggy["summary"])
        and validation_status(fixed_summary) == "passed"
    )
    return {
        "variant": variant,
        "variant_id": f"{variant}:{state.asset.asset_id}",
        "asset_id": state.asset.asset_id,
        "proposal_path": str(state.proposal_path),
        "test_file": state.asset.test_file,
        "buggy": state.buggy["summary"],
        "fixed": fixed_summary,
        "status": "reveal_candidate" if raw_reveal else "fixed_failed",
        "raw_reveal": raw_reveal,
        "bug_revealed": False,
    }


def confirm_reveal_candidate(
    *,
    runtime: TargetProbeRuntime,
    state: AssetValidationState,
    variant: str,
) -> dict[str, Any]:
    runs = []
    count = max(1, int(runtime.options.reveal_confirmation_runs))
    for attempt in range(1, count + 1):
        confirmation_dir = state.sample_dir / f"{variant}-confirmation-{attempt:03d}"
        buggy, fixed = (
            runtime.validation.run(
                revision_kind=kind,
                proposal=state.asset,
                proposal_path=state.proposal_path,
                sample_dir=confirmation_dir,
            )
            for kind in ("buggy", "fixed")
        )
        runs.append(
            {
                "attempt": attempt,
                "passed": is_buggy_non_pass(buggy["summary"])
                and validation_status(fixed["summary"]) == "passed",
                "buggy": buggy["summary"],
                "fixed": fixed["summary"],
            }
        )
    return {
        "required_runs": count,
        "runs": runs,
        "stable": len(runs) == count and all(run["passed"] for run in runs),
    }


def asset_result_row(
    state: AssetValidationState,
    *,
    minimization: dict[str, Any],
    original_asset: Any,
    harness_repair: dict[str, Any],
    outcome_key: str = "buggy",
) -> dict[str, Any]:
    asset = state.asset
    # Keep execution and ledger fields; candidate explanations stay in proposal.json.
    row = asset.to_dict()
    for key in (
        "append_code",
        "mocking_plan",
        "supporting_evidence",
        "expected_observation",
        "novelty_from_prior",
        "bug_hypothesis",
    ):
        row.pop(key)
    row.update(
        proposal_path=str(state.proposal_path),
        semantic_fingerprint=semantic_fingerprint(asset),
    )
    row[outcome_key] = state.buggy["summary"]
    if harness_repair:
        row["harness_repair"] = harness_repair.get("record", {})
    if minimization:
        row["minimization"] = minimization.get("record", {})
    if asset.asset_id != original_asset.asset_id:
        row["original_asset_id"] = original_asset.asset_id
    return row


def is_buggy_non_pass(summary: dict[str, Any]) -> bool:
    return validation_status(summary) != "passed"


def asset_error(
    asset_dir: Path, exc: BaseException, *, asset_id: str
) -> dict[str, Any]:
    asset_dir.mkdir(parents=True, exist_ok=True)
    payload = {"type": type(exc).__name__, "message": str(exc)}
    write_json(asset_dir / "error.json", payload)
    return {
        "asset_id": asset_id,
        "status": "error",
        "bug_revealed": False,
        "error": payload,
    }
