"""Progress checkpoints and stopping policy for target probing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from common.utils.python.json_io import write_json
from probe.python.run.reporting import compact_text, iter_assets
from probe.python.run.options import is_discovery


def reveal_candidate_count(rows: list[dict[str, Any]]) -> int:
    return sum(
        1
        for asset in iter_assets(rows)
        if asset.get("bug_revealed") or asset.get("status") == "revealed"
    )


def candidate_limit_reached(rows: list[dict[str, Any]], options: Any) -> bool:
    return confirmed_candidate_count(rows, options.evaluation_mode) >= max(
        1, options.max_reveal_candidates
    )


def confirmed_candidate_count(
    rows: list[dict[str, Any]], evaluation_mode: str | None
) -> int:
    if not is_discovery(evaluation_mode):
        return reveal_candidate_count(rows)
    return sum(
        1
        for asset in iter_assets(rows)
        if asset.get("stable_failure_candidate")
        or asset.get("status") == "stable_failure_candidate"
    )


def should_stop_after_row(
    rows: list[dict[str, Any]],
    options: Any,
    *,
    defer_discovery_candidate_stop: bool = False,
) -> bool:
    if candidate_limit_reached(rows, options) and not (
        defer_discovery_candidate_stop and is_discovery(options.evaluation_mode)
    ):
        return True
    abort = workflow_abort_for_rows(rows, options.max_workflow_errors)
    if abort:
        rows[-1]["workflow_abort"] = abort
        return True
    return False


def workflow_abort_for_rows(
    rows: list[dict[str, Any]],
    threshold: int,
) -> dict[str, Any] | None:
    if threshold <= 0:
        return None
    counts: dict[str, int] = {}
    for row in rows:
        if row.get("status") != "error" or not isinstance(row.get("error"), dict):
            continue
        error = row["error"]
        key = compact_text(
            f"{error.get('type', 'Error')}: {error.get('message', '')}",
            240,
        )
        counts[key] = counts.get(key, 0) + 1
        if counts[key] >= threshold:
            return {
                "reason": "repeated_sample_error",
                "stop_reason": "workflow_error",
                "error_key": key,
                "threshold": threshold,
            }
    return None


def should_run_soft_extension(
    packet: dict[str, Any],
    *,
    rows: list[dict[str, Any]],
    soft_samples: int,
    max_reveal_candidates: int = 1,
) -> bool:
    if soft_samples <= 0 or confirmed_candidate_count(
        rows, packet.get("evaluation_mode")
    ) >= max(1, max_reveal_candidates):
        return False
    units = [unit for unit in packet.get("target_units", []) if isinstance(unit, dict)]
    return len(units) > 1


def write_progress(
    run_dir: Path,
    rows: list[dict[str, Any]],
    error: BaseException | None = None,
) -> None:
    """Index completed result files and retain any budget exception."""
    payload = {
        "samples": [
            {
                "sample_id": row["sample_id"],
                "result_path": str(
                    run_dir / "samples" / row["sample_id"] / "result.json"
                ),
            }
            for row in rows
            if row.get("sample_id")
        ],
    }
    if error is not None:
        payload["error"] = {"type": type(error).__name__, "message": str(error)}
    write_json(run_dir / "progress.json", payload)
