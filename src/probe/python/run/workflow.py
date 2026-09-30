from __future__ import annotations

import http.client
import urllib.error
from pathlib import Path
from typing import Any, Callable

from common.utils.python.json_io import write_json
from probe.python.prompt.prompts import prompt_packet, prompt_prior_attempts
from probe.python.run.candidate import run_sample_assets
from probe.python.run.deadline import (
    CaseBudgetExceeded,
    limit_timeout,
)
from probe.python.run.focus import (
    focus_target_packet,
    soft_target_packet,
    unit_identity,
)
from probe.python.run.generation import (
    DIRECT_PROMPT_STYLE,
    STRICT_PROMPT_STYLE,
    InvalidModelOutputError,
    generate_probe_assets,
    generate_target_plan_and_context,
    prior_attempt_ledger,
)
from probe.python.run.progress import (
    candidate_limit_reached,
    should_run_soft_extension,
    should_stop_after_row,
    write_progress,
)
from probe.python.run.reporting import aggregate_asset_rows
from probe.python.run.session import TargetProbeRuntime
from probe.python.run.options import (
    normalize_target_strategy,
)


def run_guided_case_samples(
    *,
    runtime: TargetProbeRuntime,
    packet: dict[str, Any],
    run_dir: Path,
) -> list[dict[str, Any]]:
    """Run focused direct/strict lanes, then an eligible whole-target extension."""

    options = runtime.options
    rows: list[dict[str, Any]] = []
    repair_budget = options.harness_repairs_per_sample
    lanes = (
        ("direct_probe", "direct", options.direct_samples, DIRECT_PROMPT_STYLE),
        ("hard_core", "sample", options.samples, STRICT_PROMPT_STYLE),
        ("soft_extension", "soft", options.soft_samples, STRICT_PROMPT_STYLE),
    )
    for lane, prefix, budget, prompt_style in lanes:
        if lane == "hard_core" and candidate_limit_reached(rows, options):
            break
        if lane == "soft_extension" and not should_run_soft_extension(
            packet,
            rows=rows,
            soft_samples=budget,
            max_reveal_candidates=options.max_reveal_candidates,
        ):
            break
        for index in range(1, max(0, budget) + 1):
            sample_id = f"{prefix}-{index:03d}"
            sample_dir = run_dir / "samples" / sample_id
            row = run_lane_sample(
                runtime=runtime,
                packet=(
                    soft_target_packet(packet, index)
                    if lane == "soft_extension"
                    else focus_target_packet(packet, index, lane=lane)
                ),
                sample_id=sample_id,
                sample_dir=sample_dir,
                prior_attempts=prior_attempt_ledger(
                    rows, evaluation_mode=options.evaluation_mode
                ),
                prompt_style=prompt_style,
                harness_repair_budget=repair_budget,
                lane=lane,
            )
            rows.append(row)
            stop = should_stop_after_row(
                rows, options, defer_discovery_candidate_stop=lane == "direct_probe"
            )
            write_json(sample_dir / "result.json", row)
            write_progress(run_dir, rows)
            if stop:
                return rows
    return rows


def run_lane_sample(
    *,
    runtime: TargetProbeRuntime,
    packet: dict[str, Any],
    sample_id: str,
    sample_dir: Path,
    prior_attempts: list[dict[str, Any]],
    prompt_style: str,
    harness_repair_budget: int,
    lane: str,
) -> dict[str, Any]:
    """Persist completed asset evidence and the final sample result."""

    limit_timeout()
    strategy = normalize_target_strategy(runtime.options.strategy)
    result_path = sample_dir / "result.json"

    def finish(row):
        row["strategy"] = strategy
        row["lane"] = lane
        row["evaluation_mode"] = runtime.options.evaluation_mode
        write_json(result_path, row)
        return row

    try:
        row = run_target_sample(
            runtime=runtime,
            packet=packet,
            sample_id=sample_id,
            sample_dir=sample_dir,
            prior_attempts=prior_attempts,
            prompt_style=prompt_style,
            harness_repair_budget=harness_repair_budget,
            on_progress=finish,
        )
    except (Exception, SystemExit) as exc:
        if isinstance(exc, CaseBudgetExceeded) or is_transient_provider_error(exc):
            raise
        row = sample_error(sample_dir, exc)
    return finish(row)


def is_transient_provider_error(exc: BaseException) -> bool:
    """Keep provider outages/limits from being counted as generated samples."""

    if isinstance(exc, urllib.error.HTTPError):
        return exc.code >= 500 or exc.code in {408, 409, 425, 429}
    return isinstance(
        exc, (urllib.error.URLError, TimeoutError, http.client.HTTPException)
    )


def run_target_sample(
    *,
    runtime: TargetProbeRuntime,
    packet: dict[str, Any],
    sample_id: str,
    sample_dir: Path,
    prior_attempts: list[dict[str, Any]],
    prompt_style: str,
    harness_repair_budget: int,
    on_progress: Callable[[dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    """Run planning, implementation, and independent asset validation."""

    options = runtime.options
    sample_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        sample_dir / "prior-attempts.json", prompt_prior_attempts(prior_attempts)
    )
    write_json(sample_dir / "prompt-packet.json", prompt_packet(packet))
    focus_unit = (
        packet.get("focus_target_unit")
        if isinstance(packet.get("focus_target_unit"), dict)
        else {}
    )
    base = sample_base_row(packet, sample_id, sample_dir, focus_unit)

    # Resolve requested modules or symbols from the active target checkout.
    plan_data = generate_target_plan_and_context(
        runtime=runtime,
        packet=packet,
        sample_dir=sample_dir,
        prior_attempts=prior_attempts,
        prompt_style=prompt_style,
    )
    packet["boundary_plan"] = plan_data.get("boundary_plan", [])

    if not packet["boundary_plan"]:
        row = {
            **base,
            "status": "exhausted",
            "bug_revealed": False,
            "assets": [],
            "exhausted_reason": plan_data["exhausted_reason"],
        }
    else:
        # Each asset has its own validation; sibling failures stay independent.
        probe = generate_probe_assets(
            runtime=runtime,
            packet=packet,
            plan=plan_data,
            sample_dir=sample_dir,
            prior_attempts=prior_attempts,
            prompt_style=prompt_style,
        )
        asset_rows = run_sample_assets(
            runtime=runtime,
            packet=packet,
            plan=plan_data,
            sample_dir=sample_dir,
            assets=probe.assets,
            minimization_budget=options.minimize_buggy_failures_per_sample,
            harness_repair_budget=harness_repair_budget,
            on_progress=(
                lambda rows: on_progress(
                    aggregate_asset_rows(
                        base, probe.path, rows, evaluation_mode=options.evaluation_mode
                    )
                )
            )
            if on_progress
            else None,
        )
        row = aggregate_asset_rows(
            base, probe.path, asset_rows, evaluation_mode=options.evaluation_mode
        )
    return row


def sample_base_row(
    packet: dict[str, Any],
    sample_id: str,
    sample_dir: Path,
    focus_unit: dict[str, Any],
) -> dict[str, Any]:
    row = {
        "sample_id": sample_id,
        "prompt_path": str(sample_dir / "implementation.prompt.md"),
        "target_unit_ids": [unit["unit_id"] for unit in packet.get("target_units", [])],
    }
    if focus_unit:
        row["focus_target_unit_id"] = str(focus_unit.get("unit_id") or "")
        row["focus_target_unit"] = unit_identity(focus_unit)
    return row


def sample_error(sample_dir: Path, exc: BaseException) -> dict[str, Any]:
    sample_dir.mkdir(parents=True, exist_ok=True)
    payload = {"type": type(exc).__name__, "message": str(exc)}
    write_json(sample_dir / "error.json", payload)
    status = (
        "invalid_model_output" if isinstance(exc, InvalidModelOutputError) else "error"
    )
    return {"sample_id": sample_dir.name, "status": status, "error": payload}
