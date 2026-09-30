"""Repair invalid harnesses and minimize successful bug-revealing probes."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from common.utils.python.json_io import write_json
from probe.python.models import ProbeAsset
from probe.python.prompt.context_index import (
    failure_text_from_summary,
    project_traceback_context,
)
from probe.python.prompt.context_requests import parse_harness_repair_decision
from probe.python.prompt.prompts import (
    render_target_contract_agnostic_repair_prompt,
    render_target_harness_repair_context_request_prompt,
    render_target_harness_repair_prompt,
    render_target_probe_minimize_prompt,
)
from probe.python.prompt.proposal import (
    parse_proposal_partial,
    validate_minimized_code_is_subset,
)
from probe.python.run.client import message_content
from probe.python.run.deadline import CaseBudgetExceeded
from probe.python.run.options import primary_checkout, strategy_profile
from probe.python.run.generation import (
    packet_public_entrypoints,
    resolve_context_for_manifest,
)
from probe.python.run.reporting import (
    compact_text,
    validation_failure_kind,
    validation_status,
)
from probe.python.run.session import (
    AssetValidationState,
    complete_and_record,
    validate_buggy_asset,
)

if TYPE_CHECKING:
    from probe.python.run.session import TargetProbeRuntime


def repair_harness_asset(
    *,
    runtime: TargetProbeRuntime,
    packet: dict[str, Any],
    plan: dict[str, Any],
    state: AssetValidationState,
) -> dict[str, Any]:
    """Let the model decide whether a non-assertion failure needs an additive repair."""

    options = runtime.options
    profile = strategy_profile(options.strategy)
    classification = repair_disposition(state.buggy["summary"])
    if options.harness_repair_attempts <= 0 or not options.model:
        return {
            "record": {
                "called": False,
                "enabled": False,
                "classification": classification,
            }
        }
    last: dict[str, Any] = {
        "record": {"called": False, "classification": classification}
    }
    asset_dir = state.sample_dir
    attempt_records: list[dict[str, Any]] = []
    for attempt_index in range(1, options.harness_repair_attempts + 1):
        repair_dir = (
            asset_dir / f"{profile.repair_key.replace('_', '-')}-{attempt_index:03d}"
        )
        repair_dir.mkdir(parents=True, exist_ok=True)
        traceback_context = []
        if profile.repair_mode == "harness":
            traceback_context = repair_traceback_context(
                runtime.manifest, state.buggy["summary"]
            )
            write_json(repair_dir / "traceback-context.json", traceback_context)
        failure_summary = buggy_failure_summary(
            state.buggy["summary"],
            failure_excerpt_chars=8000,
        )
        write_json(
            repair_dir / "failure-packet.json",
            {
                "summary": failure_summary,
                "failure_evidence": failure_text_from_summary(state.buggy["summary"]),
                "project_frames": traceback_context,
            },
        )
        decision_result = generate_harness_repair_decision(
            runtime=runtime,
            packet=packet,
            plan=plan,
            asset=state.asset,
            buggy_summary=failure_summary,
            traceback_context=traceback_context,
            repair_dir=repair_dir,
        )
        decision = decision_result["decision"]
        base_record = {
            "attempt": attempt_index,
            "classification": classification,
            **decision_result["record"],
        }
        if decision["action"] == "retain_original":
            record = {**base_record, "decision": "retain_original"}
            return record_repair_attempt(record, attempt_records)

        prompt_path = Path(decision_result["record"]["prompt_path"])
        raw_path = Path(decision_result["record"]["raw_path"])
        proposal_content: str | dict[str, Any] = decision.get("proposal", {})
        if decision["action"] == "request_context":
            prompt = render_target_harness_repair_prompt(
                packet,
                plan=plan,
                asset=state.asset.to_dict(),
                buggy_summary=failure_summary,
                traceback_context=traceback_context,
                repair_context=decision_result["retrieved_context"],
            )
            prompt_path = repair_dir / "repair.prompt.md"
            prompt_path.write_text(prompt, encoding="utf-8")
            raw_path = repair_dir / "repair.raw.json"
            response = complete_and_record(runtime, prompt, raw_path)
            proposal_content = message_content(response)
        base_record = {
            **base_record,
            "prompt_path": str(prompt_path),
            "traceback_context_path": str(repair_dir / "traceback-context.json")
            if profile.repair_mode == "harness"
            else "",
        }
        try:
            proposal, parse_errors = parse_proposal_partial(
                proposal_content,
                max_assets=1,
                allowed_test_roots=packet.get("generated_test_roots"),
                canonical_plan=plan,
                public_entrypoints=packet_public_entrypoints(packet),
                allow_empty_assets=True,
            )
            if not proposal.assets:
                if parse_errors:
                    detail = "; ".join(
                        str(error.get("message") or "") for error in parse_errors
                    )
                    raise SystemExit(f"repair proposal has no valid assets: {detail}")
                record = {
                    **base_record,
                    "raw_path": str(raw_path),
                    "decision": "retain_original",
                }
                return record_repair_attempt(record, attempt_records)
            validate_harness_repair_preserves_intent(state.asset, proposal.assets[0])
            repaired_asset = normalize_harness_repaired_asset(
                state.asset, proposal.assets[0]
            )
            repaired_state = validate_buggy_asset(
                runtime, repaired_asset, repair_dir, parse_errors
            )
        except (Exception, SystemExit) as exc:
            if isinstance(exc, CaseBudgetExceeded):
                raise
            record = {
                **base_record,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
            last = record_repair_attempt(record, attempt_records)
            continue

        record = {
            **base_record,
            "raw_path": str(raw_path),
            "proposal_path": str(repaired_state.proposal_path),
            "sample_dir": str(repair_dir),
            "decision": "repair",
        }
        last = record_repair_attempt(record, attempt_records, repaired_state)
        classification = repair_disposition(repaired_state.buggy["summary"])
        if not classification["needs_repair"]:
            return last
        state = repaired_state
    return last


def skipped_harness_repair_record(classification: dict[str, Any]) -> dict[str, Any]:
    return {
        "record": {
            "called": False,
            "enabled": False,
            "classification": classification,
            "skipped_reason": "sample_harness_repair_budget_exhausted",
        }
    }


def record_repair_attempt(
    record: dict[str, Any],
    attempts: list[dict[str, Any]],
    state: AssetValidationState | None = None,
) -> dict[str, Any]:
    """Retain ordered attempt evidence and the current validated state."""

    attempts.append(record)
    return {
        "record": {"called": True, "attempts": attempts},
        **({"state": state} if state is not None else {}),
    }


def generate_harness_repair_decision(
    *,
    runtime: TargetProbeRuntime,
    packet: dict[str, Any],
    plan: dict[str, Any],
    asset: Any,
    buggy_summary: dict[str, Any],
    traceback_context: list[dict[str, Any]],
    repair_dir: Path,
) -> dict[str, Any]:
    """Let the model repair directly or request one exact context batch."""

    generic = strategy_profile(runtime.options.strategy).repair_mode == "generic"
    max_context_requests = (
        0 if generic else max(0, int(runtime.options.harness_context_requests or 0))
    )
    prompt_args = {
        "plan": plan,
        "asset": asset.to_dict(),
        "buggy_summary": buggy_summary,
    }
    if generic:
        prompt = render_target_contract_agnostic_repair_prompt(packet, **prompt_args)
    else:
        prompt = render_target_harness_repair_context_request_prompt(
            packet,
            **prompt_args,
            traceback_context=traceback_context,
            max_context_requests=max_context_requests,
        )
    prompt_path = repair_dir / "repair-decision.prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    raw_path = repair_dir / "repair-decision.raw.json"
    decision_error = None
    try:
        response = complete_and_record(runtime, prompt, raw_path)
        decision, parse_errors = parse_harness_repair_decision(
            message_content(response),
            max_requests=max_context_requests,
        )
    except (Exception, SystemExit) as exc:
        decision_error = {"type": type(exc).__name__, "message": str(exc)}
        if not raw_path.exists():
            write_json(raw_path, runtime.model.raw_payload({"error": decision_error}))
        if isinstance(exc, CaseBudgetExceeded):
            raise
        # Failed calls and rejected replies still consume the repair budget.
        decision = {
            "action": "retain_original",
            "diagnosis": "repair decision unavailable",
        }
        parse_errors = [decision_error]
    write_json(
        repair_dir / "repair-decision.json",
        {
            "action": decision["action"],
            "diagnosis": decision.get("diagnosis", ""),
            "request_count": len(decision.get("requests", [])),
            **({"parse_errors": parse_errors} if parse_errors else {}),
        },
    )
    requested_context = {"requests": []}
    if decision["action"] == "request_context":
        requested_context = resolve_context_for_manifest(
            manifest=runtime.manifest,
            requests=decision["requests"],
            max_requests=max_context_requests,
            out_path=repair_dir / "requested-context.json",
        )
    retrieved_context = {
        "traceback_context": traceback_context,
        "requested_context": requested_context,
    }
    write_json(repair_dir / "retrieved-context.json", retrieved_context)
    return {
        "record": {
            "prompt_path": str(prompt_path),
            "raw_path": str(raw_path),
            **({"error": decision_error} if decision_error else {}),
            "context_request_path": str(repair_dir / "repair-decision.json"),
            "retrieved_context_path": str(repair_dir / "retrieved-context.json"),
        },
        "decision": decision,
        "retrieved_context": retrieved_context,
    }


def repair_traceback_context(
    manifest: dict[str, Any], summary: dict[str, Any]
) -> list[dict[str, Any]]:
    checkout = primary_checkout(manifest).get("path")
    source_roots = manifest.get("source_roots", [])
    if not checkout or not isinstance(source_roots, list):
        return []
    return project_traceback_context(
        project_root=Path(str(checkout)),
        source_roots=[str(root) for root in source_roots],
        failure_text=failure_text_from_summary(summary),
    )


def validate_harness_repair_preserves_intent(
    original: ProbeAsset, repaired: ProbeAsset
) -> None:
    # The repair may change imports, fixtures, mocks, and construction code,
    # but it cannot move the test or change its canonical behavioral boundary.
    before, after = original.to_dict(), repaired.to_dict()
    for field in (
        "test_file",
        "boundary_id",
        "target_unit_ids",
        "public_entrypoint_id",
    ):
        if after[field] != before[field]:
            raise SystemExit(f"harness repair changed canonical {field}")


def normalize_harness_repaired_asset(
    original: ProbeAsset, repaired: ProbeAsset
) -> ProbeAsset:
    return replace(
        original,
        asset_id=repaired.asset_id or original.asset_id,
        append_code=repaired.append_code,
        input_construction=repaired.input_construction or original.input_construction,
        mocking_plan=repaired.mocking_plan,
    )


def minimize_asset(
    *,
    runtime: TargetProbeRuntime,
    packet: dict[str, Any],
    plan: dict[str, Any],
    state: AssetValidationState,
    enabled: bool,
) -> dict[str, Any]:
    """Try to simplify an already buggy-failing probe using buggy evidence only."""

    if not enabled or validation_status(state.buggy["summary"]) != "assertion_failed":
        return {}
    buggy_summary = buggy_failure_summary(
        state.buggy["summary"],
        failure_excerpt_chars=runtime.options.minimization_failure_excerpt_chars,
    )

    def attempt(directory: Path, retry_context=None) -> dict[str, Any]:
        return run_minimization_attempt(
            runtime=runtime,
            packet=packet,
            plan=plan,
            asset=state.asset,
            buggy_summary=buggy_summary,
            directory=directory,
            retry_context=retry_context,
        )

    first = attempt(state.sample_dir)
    if (
        first.get("record", {}).get("use_minimized")
        or first.get("record", {}).get("minimized_buggy_status") != "buggy_passed"
        or runtime.options.minimization_preserve_attempts <= 0
    ):
        return first

    # A preserve retry is used only when the first minimized asset no longer
    # fails on buggy. The retry receives that failure-preservation feedback, but
    # still no fixed-side result.
    retry = attempt(
        state.sample_dir / "minimization-preserve-001", minimization_retry_context(first)
    )
    attempts = [deepcopy(first.get("record", {})), deepcopy(retry.get("record", {}))]
    selected = retry if retry.get("record", {}).get("use_minimized") else first
    selected.setdefault("record", {})["attempts"] = attempts
    return selected


def run_minimization_attempt(
    *,
    runtime: TargetProbeRuntime,
    packet: dict[str, Any],
    plan: dict[str, Any],
    asset: Any,
    buggy_summary: dict[str, Any],
    directory: Path,
    retry_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one buggy-only minimization attempt and validate it on buggy."""

    prompt_path = directory / "minimization.prompt.md"
    raw_path = directory / "minimization.raw.json"
    output_dir = directory / "minimized"
    prompt = render_target_probe_minimize_prompt(
        packet,
        asset=asset.to_dict(),
        buggy_summary=buggy_summary,
        retry_context=retry_context,
    )
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")
    base_record = {
        "called": True,
        "prompt_path": str(prompt_path),
        "use_minimized": False,
    }
    try:
        response = complete_and_record(runtime, prompt, raw_path)
        proposal, parse_errors = parse_proposal_partial(
            message_content(response),
            max_assets=1,
            allowed_test_roots=packet.get("generated_test_roots"),
            canonical_plan=plan,
            public_entrypoints=packet_public_entrypoints(packet),
        )
        minimized_asset = proposal.assets[0]
        validate_minimized_metadata(asset, minimized_asset)
        validate_minimized_code_is_subset(asset, minimized_asset)
    except (Exception, SystemExit) as exc:
        if isinstance(exc, CaseBudgetExceeded):
            raise
        return {
            "record": {
                **base_record,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
        }

    state = validate_buggy_asset(runtime, minimized_asset, output_dir, parse_errors)
    minimized_status = minimized_buggy_status(state.buggy)
    return {
        "record": {
            **base_record,
            "raw_path": str(raw_path),
            "proposal_path": str(state.proposal_path),
            "sample_dir": str(output_dir),
            "minimized_buggy_status": minimized_status,
            "use_minimized": minimized_status == "buggy_failed_candidate",
        },
        "state": state,
    }


def minimized_buggy_status(validation: dict[str, Any]) -> str:
    summary = validation.get("summary", {})
    status = validation_status(summary)
    if status == "assertion_failed":
        return "buggy_failed_candidate"
    if status == "passed":
        return "buggy_passed"
    return "buggy_needs_repair"


def validate_minimized_metadata(original: ProbeAsset, minimized: ProbeAsset) -> None:
    before, after = original.to_dict(), minimized.to_dict()
    for field in (
        "test_file",
        "boundary_id",
        "target_unit_ids",
        "public_entrypoint_id",
        "test_intent",
        "activation_conditions",
        "independent_oracle",
        "supporting_evidence",
        "expected_observation",
        "oracle_family",
        "novelty_from_prior",
        "bug_hypothesis",
        "input_construction",
        "observable_oracle",
        "primary_oracle",
        "oracle_mode",
        "mocking_plan",
    ):
        if after[field] != before[field]:
            raise SystemExit(f"minimization changed {field}")


def minimization_retry_context(result: dict[str, Any]) -> dict[str, Any]:
    state = result.get("state")
    return {
        "previous_asset": state.asset.to_dict() if state is not None else {},
        "previous_buggy_status": result.get("record", {}).get(
            "minimized_buggy_status", ""
        ),
        "previous_buggy_summary": buggy_failure_summary(
            state.buggy.get("summary", {}) if state is not None else {},
            failure_excerpt_chars=800,
        ),
    }


def buggy_failure_summary(
    summary: dict[str, Any],
    *,
    failure_excerpt_chars: int,
) -> dict[str, Any]:
    return {
        "phase": summary.get("phase", ""),
        "exit_code": summary.get("exit_code"),
        "timed_out": summary.get("timed_out", False),
        "status": validation_status(summary),
        "classification_source": summary.get("classification_source", ""),
        "classification_reason": summary.get("classification_reason", ""),
        "failed_nodeids": summary.get("failed_nodeids", []),
        "failure_kind": validation_failure_kind(summary),
        "failure_excerpt": compact_text(
            summary.get("failure_excerpt", ""), failure_excerpt_chars
        ),
        "diagnostics": compact_text(
            summary.get("diagnostics", {}), failure_excerpt_chars
        ),
        "output_tail": compact_text(
            summary.get("output_tail", ""), failure_excerpt_chars
        ),
    }


def repair_disposition(summary: dict[str, Any]) -> dict[str, Any]:
    outcome = validation_status(summary)
    return {
        "outcome": outcome,
        "needs_repair": outcome == "needs_repair",
        "reason": summary.get("classification_reason")
        or ("non_assertion_failure" if outcome == "needs_repair" else ""),
    }
