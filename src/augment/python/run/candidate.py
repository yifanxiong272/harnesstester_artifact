#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from augment.python.acceptance import is_candidate_atomic
from augment.python.prompt.context import (
    ContextBroker,
    omit_visible_context,
    source_roots_from_coverage_source,
)
from augment.python.prompt.proposal import (
    parse_context_requests,
    parse_test_proposal,
)
from augment.python.run.project_state import (
    cleanup_staging,
    create_staging_project,
    materialize_in_project,
    persist_generated_snapshot,
    staging_project_root,
)
from augment.python.run.runtime import RunContext, SampleContext
from augment.python.run.coverage_delta import (
    score_general_coverage_delta,
    score_test_coverage_delta,
)
from augment.python.run.validate import coverage_succeeded
from common.utils.python.json_io import read_json, write_json


@dataclass(frozen=True)
class CandidateAttempt:
    """Paths and base result fields for one generated proposal attempt."""

    directory: Path
    sample_id: str
    base_row: dict[str, Any]


def validate_candidate(
    context: RunContext,
    sample: SampleContext,
    proposal_data: dict[str, Any] | str,
    attempt: CandidateAttempt,
) -> dict[str, Any]:
    """Materialize, run, and measure one generated pytest proposal."""

    try:
        proposal = parse_test_proposal(proposal_data)
        require_round_test_file(
            context.current_root, proposal.test_file, sample.round_index
        )
    except SystemExit as exc:
        write_json(
            attempt.directory / "proposal_error.json",
            {"error": str(exc), "raw_proposal": proposal_data},
        )
        return failure_row(
            attempt.base_row, sample.objective, "proposal_invalid", str(exc)
        )

    payload = proposal.to_dict()
    write_json(attempt.directory / "proposal.json", payload)
    staging_root = staging_project_root(
        context.run_dir, context.options.project_root, attempt.sample_id
    )
    create_staging_project(context.current_root, staging_root)
    try:
        materialized = materialize_in_project(staging_root, proposal)
        write_json(attempt.directory / "materialized.json", materialized)
        generated_snapshot = attempt.directory / "generated_test_file.py"
        generated_snapshot.write_text(
            (staging_root / proposal.test_file).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        atomic = is_candidate_atomic(context.options.acceptance_policy)
        suffix = round_test_name_suffix(sample.round_index)
        candidate_path = attempt.directory / "accepted_coverage.json"
        coverage_path: Path | None = None
        coverage_run: dict[str, Any] = {}
        collect_result: dict[str, Any] = {}
        generated_nodeids: list[str] = []

        # Atomic validation measures the whole file before collecting its tests.
        if atomic:
            coverage_run = context.validation.coverage(
                staging_root, [proposal.test_file], candidate_path, fail_fast=True
            )
            if coverage_succeeded(coverage_run, candidate_path):
                coverage_path = candidate_path
        if not atomic or coverage_path is not None:
            generated_nodeids, collect_result = context.validation.collect(
                staging_root, proposal.test_file, keyword=suffix
            )
            generated_nodeids = [
                nodeid
                for nodeid in generated_nodeids
                if nodeid_has_suffix(nodeid, suffix)
            ]

        if atomic:
            run_result = coverage_run.get("coverage_run")
            filter_result = {
                "acceptance_policy": "candidate_atomic",
                "test_selector": proposal.test_file,
                "generated_nodeids": generated_nodeids,
                "accepted_nodeids": generated_nodeids if coverage_path else [],
                "rejected_nodeids": []
                if coverage_path
                else [
                    {
                        "nodeid": proposal.test_file,
                        **(run_result if isinstance(run_result, dict) else {}),
                    }
                ],
            }
        else:
            filter_result = context.validation.filter_passing(
                staging_root, generated_nodeids
            )
        declared_nodeids = sorted(set(proposal.expected_nodeids))
        write_json(
            attempt.directory / "validation.json",
            {
                "collect_result": collect_result,
                "required_test_name_suffix": suffix,
                "declared_nodeids": declared_nodeids,
                "collected_round_nodeids": generated_nodeids,
                "missing_declared_nodeids": sorted(
                    set(declared_nodeids) - set(generated_nodeids)
                ),
                "undeclared_collected_nodeids": sorted(
                    set(generated_nodeids) - set(declared_nodeids)
                ),
                **filter_result,
            },
        )

        coverage_update_path: Path | None = None
        coverage_delta: dict[str, Any] = {}
        project_delta: dict[str, Any] = {}
        score: dict[str, Any] = {}
        accepted_nodeids = filter_result["accepted_nodeids"]
        if not atomic and accepted_nodeids:
            coverage_run = context.validation.coverage(
                staging_root, accepted_nodeids, candidate_path
            )
            if coverage_succeeded(coverage_run, candidate_path):
                coverage_path = candidate_path
        if coverage_path is not None:
            accepted_coverage = read_json(coverage_path)
            score = score_test_coverage_delta(
                objective=sample.objective,
                accepted_coverage=accepted_coverage,
            )
            coverage_delta = score["coverage_delta"]
            project_delta = score_general_coverage_delta(
                snapshot=sample.snapshot,
                accepted_coverage=accepted_coverage,
            )
        if atomic and coverage_path is None:
            status = (
                "validation_failed"
                if isinstance(run_result, dict)
                and run_result.get("exit_code") not in (0, None)
                else "coverage_failed"
            )
        elif not generated_nodeids:
            status = "round_nodeid_missing"
        elif not accepted_nodeids:
            status = "validation_failed"
        elif coverage_path is None:
            status = "coverage_failed"
        else:
            status = "accepted"
        coverage_paths = {"accepted_coverage_path": str(coverage_path or "")}
        if coverage_path is not None and status != "accepted":
            coverage_paths = {
                "accepted_coverage_path": "",
                "measured_coverage_path": str(coverage_path),
            }
        if atomic or accepted_nodeids:
            coverage_update_path = attempt.directory / "coverage_update.json"
            write_json(
                coverage_update_path,
                {
                    **coverage_paths,
                    "run": coverage_run,
                    "score": score,
                    "general_coverage_delta": project_delta,
                },
            )
        return {
            **attempt.base_row,
            "sample_id": attempt.sample_id,
            "unit_id": sample.objective["unit"]["unit_id"],
            "proposal_path": str(attempt.directory / "proposal.json"),
            "test_file": proposal.test_file,
            "generated_test_file_path": str(generated_snapshot),
            "generated_nodeids": generated_nodeids,
            "accepted_nodeids": accepted_nodeids,
            "rejected_nodeids": filter_result["rejected_nodeids"],
            "coverage_delta": coverage_delta,
            "general_coverage_delta": project_delta,
            "coverage_update_path": str(coverage_update_path or ""),
            **coverage_paths,
            "status": status,
            "failure_output": validation_failure_output(
                status,
                collect_result=collect_result,
                coverage_run=coverage_run,
            ),
            "error": (
                f"generated pytest nodeids must contain {suffix}"
                if status == "round_nodeid_missing"
                else "generated test file did not pass as an atomic candidate"
                if atomic and status == "validation_failed"
                else ""
            ),
        }
    finally:
        cleanup_staging(staging_root)


def persist_accepted(context: RunContext, row: dict[str, Any]) -> dict[str, Any]:
    """Commit one accepted generated test into the rolling project."""

    if row.get("status") != "accepted":
        return row
    saved = persist_generated_snapshot(
        run_dir=context.run_dir,
        sample_id=str(row["sample_id"]),
        current_root=context.current_root,
        test_file=str(row["test_file"]),
        generated_snapshot=Path(str(row["generated_test_file_path"])),
    )
    return {**row, **saved}


def resolve_context(
    requests: list[Any],
    *,
    project_root: Path,
    coverage_source: str,
    out_path: Path,
    visible_context: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve one model-requested batch against project-local AST definitions."""

    broker = context_broker(project_root, coverage_source)
    if broker is None:
        write_json(out_path, [])
        return []
    context = omit_visible_context(
        broker.resolve_batch(parse_context_requests(requests)),
        visible_context,
    )
    write_json(out_path, context)
    return context


def context_broker(project_root: Path, coverage_source: str) -> ContextBroker | None:
    roots = source_roots_from_coverage_source(project_root, coverage_source)
    return ContextBroker(project_root, roots) if roots else None


def failure_row(
    base: dict[str, Any], objective: dict[str, Any], status: str, error: str
) -> dict[str, Any]:
    """Return the complete empty-result shape for a failed generation attempt."""

    return {
        **base,
        "unit_id": objective["unit"]["unit_id"],
        "proposal_path": "",
        "generated_nodeids": [],
        "accepted_nodeids": [],
        "rejected_nodeids": [],
        "coverage_delta": {},
        "general_coverage_delta": {},
        "coverage_update_path": "",
        "accepted_coverage_path": "",
        "status": status,
        "failure_output": "",
        "error": error,
    }


def validation_failure_output(
    status: str,
    *,
    collect_result: dict[str, Any],
    coverage_run: dict[str, Any],
) -> str:
    """Return measured subprocess output relevant to one failed candidate."""

    if status == "round_nodeid_missing":
        return str(collect_result.get("output_tail") or "")
    if status != "coverage_failed":
        return ""
    parts = []
    for key in ("coverage_run", "coverage_json"):
        result = coverage_run.get(key)
        if isinstance(result, dict) and result.get("output_tail"):
            parts.append(str(result["output_tail"]))
    return "\n".join(parts)[-10000:]


def round_test_name_suffix(round_index: int) -> str:
    return f"_round_{round_index:03d}"


def round_test_file_suffix(round_index: int) -> str:
    return f"{round_test_name_suffix(round_index)}.py"


def require_round_test_file(
    project_root: Path, test_file: str, round_index: int
) -> None:
    suffix = round_test_file_suffix(round_index)
    if not Path(test_file).name.endswith(suffix):
        raise SystemExit(f"generated test filename must end with {suffix}: {test_file}")
    if (project_root / test_file).exists():
        raise SystemExit(f"generated test file already exists: {test_file}")


def nodeid_has_suffix(nodeid: str, suffix: str) -> bool:
    return any(
        part.split("[", 1)[0].endswith(suffix) for part in nodeid.split("::")[1:]
    )
