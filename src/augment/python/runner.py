"""Adapt CLI arguments for the Python augmentation workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common.projects import ARTIFACT_ROOT
from augment.python.input.snapshot import build_initial_metric_snapshot
from augment.python.run.client import load_env
from augment.python.run.runtime import RunOptions
from augment.python.run.workflow import run_augment as run_python


def run_augment(args: argparse.Namespace, config: dict[str, Any]) -> Path:
    """Load user-supplied inputs and invoke the Python augmentation workflow."""
    if config.get("language") != "python":
        raise SystemExit(
            "Use python3 run.py augment --project NAME for TypeScript projects"
        )
    if args.base_input is None:
        raise SystemExit("--base-input is required")
    snapshot, runtime = build_initial_metric_snapshot(
        args.base_input,
        project_root=args.project_root,
        python=args.python_bin,
    )
    if snapshot["project"] != args.project:
        raise SystemExit("base input project does not match --project")
    settings = config.get("augment", {})
    env = load_env(args.env_file)
    model = args.model if args.model is not None else (
        env.get("LLM_MODEL") or env.get("OPENAI_MODEL") or "gpt-5-mini"
    )
    output = run_python(
        snapshot=snapshot,
        options=RunOptions(
            project=args.project,
            project_root=Path(runtime["project_root"]),
            out_root=args.out_root or ARTIFACT_ROOT / "outputs" / args.project / "augment",
            run_id=args.run_id,
            rounds=args.rounds,
            time_budget_seconds=args.time_budget_seconds,
            model=model,
            provider=args.provider,
            env=env,
            python=runtime["python"],
            timeout=args.timeout
            if args.timeout is not None
            else settings.get("timeout", 90),
            coverage_source=runtime["coverage_source"],
            test_pythonpath=runtime["test_pythonpath"],
            constraints=list(settings.get("constraints", [])),
            strategy=args.strategy,
            acceptance_policy=args.acceptance_policy,
            repair_context_requests=args.repair_context_requests,
        ),
    )
    print(output)
    return output
