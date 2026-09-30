"""Confirm failure candidates on one frozen latest revision."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable

from .candidate import asset_result_row
from .options import strategy_profile
from .repair import (
    minimize_asset,
    repair_disposition,
    repair_harness_asset,
    skipped_harness_repair_record,
)
from .reporting import compact_text, validation_failure_kind, validation_status
from .session import AssetValidationState, TargetProbeRuntime, validate_buggy_asset


def is_discovery_failure(summary: dict[str, Any]) -> bool:
    """Accept completed assertions and structured call-phase failures."""
    status = validation_status(summary)
    if status == "assertion_failed":
        return True
    failed_reports = [
        item
        for item in (summary.get("diagnostics") or {}).get("test_failures", [])
        if isinstance(item, dict) and item.get("outcome") == "failed"
    ]
    return bool(
        status == "needs_repair"
        and not summary.get("timed_out")
        and summary.get("classification_source") == "structured_reporter"
        and summary.get("classification_reason")
        == "non_assertion_or_incomplete_execution"
        and summary.get("failed_nodeids")
        and failed_reports
        and all(item.get("phase") == "call" for item in failed_reports)
    )


def _normalize_checkout(text: str, copy_root: str) -> str:
    """Replace only the recorded disposable checkout root, at path boundaries."""
    root = str(copy_root or "").rstrip("/\\")
    if not root:
        return text
    roots = {root}
    # Non-strict resolution follows surviving ancestor symlinks after cleanup.
    try:
        roots.add(str(Path(root).resolve()))
    except (OSError, RuntimeError):
        pass
    alternatives = "|".join(
        re.escape(value) for value in sorted(roots, key=len, reverse=True)
    )
    return re.sub(
        r"(?<![\w./\\-])(?:file://)?(?:" + alternatives + ")"
        + r"(?=$|[/\\\s:'\")\],}])",
        "<checkout>",
        text,
    )


def failure_fingerprint(summary: dict[str, Any], *, copy_root: str = "") -> str:
    """Identify the observed failure across repeated latest-revision executions."""
    nodeids = []
    for item in summary.get("failed_nodeids", []):
        filepath, separator, identity = str(item).partition("::")
        filepath = _normalize_checkout(filepath, copy_root)
        filepath = re.sub(r"^<checkout>[/\\]", "", filepath)
        nodeids.append(filepath + separator + identity)
    payload = {
        "nodeids": sorted(nodeids),
        "kind": validation_failure_kind(summary),
        "excerpt": compact_text(
            _normalize_checkout(str(summary.get("failure_excerpt") or ""), copy_root),
            400,
        ),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


def confirm_failure(
    runtime: TargetProbeRuntime, state: AssetValidationState, variant: str
) -> dict[str, Any]:
    summary = state.buggy["summary"]
    fingerprint = failure_fingerprint(
        summary, copy_root=state.buggy.get("materialized", {}).get("copy_root", "")
    )
    count = max(1, int(runtime.options.reveal_confirmation_runs))
    result = {
        "required_runs": count,
        "initial_failure_fingerprint": fingerprint,
        "runs": [],
        "stable": False,
    }
    if not is_discovery_failure(summary):
        return {**result, "skipped_reason": "latest_outcome_not_candidate_eligible"}
    for attempt in range(1, count + 1):
        validation = runtime.validation.run(
            revision_kind="latest",
            proposal=state.asset,
            proposal_path=state.proposal_path,
            sample_dir=state.sample_dir / f"{variant}-confirmation-{attempt:03d}",
        )
        latest = validation["summary"]
        observed = failure_fingerprint(
            latest, copy_root=validation.get("materialized", {}).get("copy_root", "")
        )
        result["runs"].append(
            {
                "attempt": attempt,
                "passed": is_discovery_failure(latest) and observed == fingerprint,
                "latest": latest,
                "failure_fingerprint": observed,
            }
        )
    result["stable"] = len(result["runs"]) == count and all(
        run["passed"] for run in result["runs"]
    )
    return result


def run_discovery_asset(
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
    """Repair eligible setup failures, confirm stability, then try minimization."""
    asset_dir.mkdir(parents=True, exist_ok=True)
    state = validate_buggy_asset(runtime, asset, asset_dir)
    classification = repair_disposition(state.buggy["summary"])
    repair = {}
    minimization = {}
    if validation_status(state.buggy["summary"]) == "passed":
        return {
            **asset_result_row(
                state,
                original_asset=asset,
                harness_repair=repair,
                minimization=minimization,
                outcome_key="latest",
            ),
            "status": "latest_passed",
            "stable_failure_candidate": False,
        }
    if classification["needs_repair"]:
        repair = (
            repair_harness_asset(runtime=runtime, packet=packet, plan=plan, state=state)
            if harness_repair_allowed
            else skipped_harness_repair_record(classification)
        )
        if repair.get("state") is not None:
            state = repair["state"]

    confirmation = confirm_failure(runtime, state, "base")

    def result_row():
        row = asset_result_row(
            state,
            original_asset=asset,
            harness_repair=repair,
            minimization=minimization,
            outcome_key="latest",
        )
        if "harness_repair" in row:
            row[strategy_profile(runtime.options.strategy).repair_key] = row.pop(
                "harness_repair"
            )
        return {
            **row,
            "confirmation": confirmation,
            "stable_failure_candidate": confirmation["stable"],
            "status": "stable_failure_candidate"
            if confirmation["stable"]
            else (
                "unstable_failure"
                if is_discovery_failure(state.buggy["summary"])
                else "latest_needs_repair"
            ),
        }

    if confirmation["stable"]:
        if on_result:
            on_result(result_row())
        minimization = minimize_asset(
            runtime=runtime,
            packet=packet,
            plan=plan,
            state=state,
            enabled=minimization_allowed,
        )
        if (
            minimization.get("record", {}).get("use_minimized")
            and minimization.get("state") is not None
        ):
            minimized_confirmation = confirm_failure(
                runtime, minimization["state"], "minimized"
            )
            if minimized_confirmation["stable"]:
                state, confirmation = minimization["state"], minimized_confirmation

    return result_row()
