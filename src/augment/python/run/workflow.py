from __future__ import annotations

import http.client
import math
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from augment.python.acceptance import is_candidate_atomic
from augment.python.input.coverage_segments import (
    build_segment_manifest,
    next_residual_segment,
)
from augment.python.input.snapshot import validate_metric_snapshot
from augment.python.project_files import run_directory
from augment.python.run.client import is_retryable_http_status
from augment.python.run.coverage_segment import run_coverage_segment
from augment.python.run.coverage_state import update_snapshot
from augment.python.run.project_state import (
    cleanup_workspaces,
    current_project_root,
    initialize_current_project,
)
from augment.python.run.report import write_progress
from augment.python.run.runtime import (
    ModelSession,
    RunContext,
    RunOptions,
    SampleContext,
    ValidationSession,
)
from augment.python.strategy import is_contract_directed
from common.utils.python.json_io import read_json, write_json


def validate_run_inputs(snapshot: dict[str, Any], options: RunOptions) -> None:
    """Check the supplied coverage, checkout, and execution options."""
    validate_metric_snapshot(snapshot)
    is_contract_directed(options.strategy)
    is_candidate_atomic(options.acceptance_policy)
    if options.rounds < 1 or options.timeout <= 0:
        raise SystemExit("rounds and timeout must be positive")
    if not math.isfinite(options.time_budget_seconds):
        raise SystemExit("time budget must be finite")
    if options.time_budget_seconds < 0 or options.repair_context_requests < 0:
        raise SystemExit("time budget and context request limit must be non-negative")
    if snapshot.get("project") != options.project:
        raise SystemExit("snapshot project does not match the selected project")
    if not options.project_root.is_dir():
        raise SystemExit(f"project root does not exist: {options.project_root}")
    if options.out_root.resolve().is_relative_to(options.project_root.resolve()):
        raise SystemExit("out_root must be outside project_root")
    if not options.coverage_source:
        raise SystemExit("coverage_source is required")
    if not snapshot.get("general_coverage", {}).get("files"):
        raise SystemExit("coverage input must contain measured files")
    if not snapshot.get("ldh_coverage", {}).get("files"):
        raise SystemExit("the LDH projection contains no executable files")


def execute_sample(context: RunContext, sample: SampleContext) -> dict[str, Any]:
    """Retry a target in a later round after a transient model transport failure."""
    try:
        return run_coverage_segment(context, sample)
    except urllib.error.HTTPError as exc:
        if not is_retryable_http_status(exc.code):
            raise
        return failed_round_row(sample, exc)
    except (
        urllib.error.URLError,
        ConnectionError,
        TimeoutError,
        http.client.HTTPException,
    ) as exc:
        return failed_round_row(sample, exc)


def failed_round_row(sample: SampleContext, error: Exception) -> dict[str, Any]:
    row = {
        "round": sample.round_index,
        "objective_id": sample.objective["objective_id"],
        "status": "model_failed",
        "accepted_nodeids": [],
        "coverage_delta": {},
        "general_coverage_delta": {},
        "error_type": type(error).__name__,
        "error": str(error),
    }
    write_json(sample.sample_dir / "phase_error.json", row)
    return row


def run_augment(*, snapshot: dict[str, Any], options: RunOptions) -> Path:
    """Run the fixed target queue, retaining tests and coverage after each round."""
    validate_run_inputs(snapshot, options)
    model = ModelSession(options.model, options.provider, options.env)
    model.validate()
    run_id = options.run_id or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    run_dir = run_directory(options.out_root, run_id)
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir()
    rows: list[dict[str, Any]] = []
    checkpoints: list[dict[str, Any]] = []
    context = RunContext(
        options=options,
        run_dir=run_dir,
        current_root=current_project_root(run_dir, options.project_root),
        model=model,
        validation=ValidationSession(
            python=options.python,
            timeout=options.timeout,
            coverage_source=options.coverage_source,
            test_pythonpath=options.test_pythonpath,
        ),
    )
    stop_reason = "failed"
    started: float | None = None
    try:
        initialize_current_project(options.project_root, context.current_root)
        manifest = build_segment_manifest(options.project_root, snapshot)
        objectives = manifest["segments"]
        write_json(run_dir / "targets.json", manifest)
        started = time.perf_counter()
        write_progress(context, snapshot, rows, checkpoints, "running", 0.0)
        cursor = 0
        stop_reason = "round_limit"
        for round_index in range(1, options.rounds + 1):
            elapsed = time.perf_counter() - started
            # Finish the active round before checking the next round's budget.
            if options.time_budget_seconds and elapsed >= options.time_budget_seconds:
                stop_reason = "time_budget"
                break
            objective, next_cursor, _ = next_residual_segment(
                objectives, snapshot, start=cursor
            )
            if objective is None:
                stop_reason = "target_exhausted"
                break
            sample = SampleContext(
                round_index=round_index,
                sample_dir=run_dir
                / "rounds"
                / f"round_{round_index:03d}"
                / "sample_001",
                objective=objective,
                snapshot=snapshot,
            )
            round_started = time.perf_counter()
            started_at = datetime.now(timezone.utc).isoformat()
            row = execute_sample(context, sample)
            if row.get("status") != "model_failed":
                cursor = next_cursor
            coverage_path = row.get("accepted_coverage_path")
            if row.get("status") == "accepted" and coverage_path:
                update_snapshot(snapshot, read_json(Path(coverage_path)))
            row["timing"] = {
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": round((time.perf_counter() - round_started) * 1000, 3),
            }
            rows.append(row)
            write_progress(
                context,
                snapshot,
                rows,
                checkpoints,
                "running",
                time.perf_counter() - started,
            )
    except BaseException:
        stop_reason = "interrupted"
        raise
    finally:
        try:
            write_progress(
                context,
                snapshot,
                rows,
                checkpoints,
                stop_reason,
                time.perf_counter() - started if started is not None else 0.0,
            )
        finally:
            cleanup_workspaces(run_dir)
    return run_dir
