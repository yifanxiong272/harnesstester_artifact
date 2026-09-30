"""Run selected targets on user-prepared latest or paired revision checkouts."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from common.utils.python.json_io import read_json, write_json
from probe.python.input.target_packets import build_target_packet
from probe.python.prompt.prompts import prompt_packet

from .client import load_env
from .deadline import CaseBudgetExceeded, end_case_budget, start_case_budget
from .options import (
    PAIRED_REVEAL_EVALUATION,
    SINGLE_REVISION_DISCOVERY_EVALUATION,
    TargetProbeRunOptions,
    normalize_target_strategy,
    strategy_profile,
    validate_run_options,
    validate_run_path_part,
)
from .preflight import preflight_target_run, run_revision_validation_preflight
from .progress import write_progress
from .session import ModelSession, TargetProbeRuntime, ValidationSession
from .workflow import run_guided_case_samples


def run_prepared_case(
    *,
    case: dict[str, Any],
    buggy_root: Path | None = None,
    fixed_root: Path | None = None,
    latest_root: Path | None = None,
    config: dict[str, Any],
    options: TargetProbeRunOptions,
    run_dir: Path,
    interpreters: dict[str, str],
    model: Any = None,
    validation: Any = None,
) -> Path:
    """Generate and evaluate probes using externally prepared inputs."""
    strategy = normalize_target_strategy(options.strategy)
    if latest_root is not None:
        if buggy_root is not None or fixed_root is not None:
            raise ValueError(
                "latest and paired checkout inputs are mutually exclusive"
            )
        roots = {"latest": latest_root.resolve()}
        mode = SINGLE_REVISION_DISCOVERY_EVALUATION
        targets = case.get("target_units", [])
    else:
        if buggy_root is None or fixed_root is None:
            raise ValueError("provide a latest checkout or both buggy/fixed checkouts")
        roots = {"buggy": buggy_root.resolve(), "fixed": fixed_root.resolve()}
        mode = PAIRED_REVEAL_EVALUATION
        targets = case.get("patch_targets", {}).get("target_units", [])
    options = replace(options, evaluation_mode=mode)
    validate_run_options(options)
    case_id = str(case["case_id"])
    validate_run_path_part(case_id, "case_id")
    run_dir = run_dir.resolve()
    for kind, root in roots.items():
        if not root.is_dir() or not case.get("revisions", {}).get(kind):
            raise ValueError(f"missing prepared {kind} checkout or case revision")
        if run_dir.is_relative_to(root) or root.is_relative_to(run_dir):
            raise ValueError("output and checkout directories must be disjoint")
    if not strategy_profile(strategy).allow_context:
        options = replace(options, context_requests=0, harness_context_requests=0)
    run_dir.mkdir(parents=True, exist_ok=False)
    token = start_case_budget(run_dir, options.case_time_budget_seconds)
    try:
        settings = {**config.get("probe", {}), **case.get("validation", {})}
        packet = build_target_packet(
            project=config["project"],
            strategy=strategy,
            project_root=next(iter(roots.values())),
            target_units=targets,
            generated_test_roots=settings.get(
                "generated_test_roots", ["tests/generated/benchmarkbr"]
            ),
            python_import_roots=tuple(settings.get("python_import_roots", [])),
        )
        packet["evaluation_mode"] = mode
        manifest = {
            "case_id": case_id,
            "project": config["project"],
            "revisions": {kind: str(case["revisions"][kind]) for kind in roots},
            "strategy": strategy,
            "evaluation_mode": mode,
            "options": {
                key: str(value) if isinstance(value, Path) else value
                for key, value in vars(options).items()
                if key != "evaluation_mode"
            },
            "source_roots": config.get("source_roots", []),
            **{f"{kind}_checkout": {"path": str(root)} for kind, root in roots.items()},
        }
        if config.get("repository_url"):
            manifest["repository_url"] = str(config["repository_url"])
        write_json(run_dir / "manifest.json", manifest)
        write_json(run_dir / "packet.json", packet)
        write_json(run_dir / "prompt-packet.json", prompt_packet(packet))
        runtime = TargetProbeRuntime(
            manifest=manifest,
            options=options,
            model=model
            or ModelSession(
                model=options.model,
                provider=options.provider,
                env=load_env(*([options.env_file] if options.env_file else [])),
                timeout=options.model_timeout,
                retries=options.model_retries,
            ),
            validation=validation
            or ValidationSession(case, roots, interpreters, options.timeout),
        )
        preflight = preflight_target_run(manifest=manifest, packet=packet)
        if preflight["passed"]:
            record = run_revision_validation_preflight(
                runtime=runtime, packet=packet, run_dir=run_dir
            )
            preflight["validation"] = record
            preflight["passed"] = record["passed"]
            if not record["passed"]:
                preflight["errors"].append(
                    {"check": "revision_validation_preflight", "path": record["path"]}
                )
            elif (
                record["target_import"]["attempted"]
                and not record["target_import"]["passed"]
            ):
                preflight["warnings"].append(
                    {"kind": "target_import_diagnostic_failed", "path": record["path"]}
                )
        write_json(run_dir / "preflight.json", preflight)
        if preflight["passed"]:
            rows = run_guided_case_samples(
                runtime=runtime, packet=packet, run_dir=run_dir
            )
        else:
            rows = []
        write_progress(run_dir, rows)
    except CaseBudgetExceeded as exc:
        rows = [
            read_json(p) for p in sorted((run_dir / "samples").glob("*/result.json"))
        ]
        write_progress(run_dir, rows, exc)
    finally:
        end_case_budget(token)
    return run_dir
