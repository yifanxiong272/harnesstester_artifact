from __future__ import annotations

from typing import Any

from augment.python.run.coverage_state import coverage_summary
from augment.python.run.runtime import RunContext
from common.utils.python.json_io import write_json


def write_progress(
    context: RunContext,
    snapshot: dict[str, Any],
    rows: list[dict[str, Any]],
    checkpoints: list[dict[str, Any]],
    stop_reason: str,
    elapsed: float,
) -> None:
    """Persist the latest coverage, accepted selectors, and round checkpoints."""
    root = context.run_dir
    options = context.options
    summary = coverage_summary(snapshot)
    if not checkpoints or checkpoints[-1]["round"] != len(rows):
        checkpoints.append(
            {
                "round": len(rows),
                "elapsed_seconds": round(elapsed, 3),
                "ldh_lines": summary["ldh_lines"],
                "ldh_branches": summary["branches"],
                "project_coverage": summary["project_coverage"],
            }
        )
    write_json(root / "coverage.json", snapshot)
    write_json(root / "results.json", rows)
    write_json(
        root / "progress.json",
        {
            "project": options.project,
            "model": options.model,
            "provider": options.provider,
            "strategy": options.strategy,
            "acceptance_policy": options.acceptance_policy,
            "stop_reason": stop_reason,
            "elapsed_seconds": round(elapsed, 3),
            "checkpoints": checkpoints,
        },
    )
