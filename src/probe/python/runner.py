"""Adapt CLI arguments and interpreters for one prepared Python probe case."""

from __future__ import annotations

import argparse
import shutil
import time
from dataclasses import fields
from pathlib import Path
from typing import Any

from common.projects import ARTIFACT_ROOT

from common.utils.python.json_io import read_json
from probe.python.run.client import load_env
from probe.python.run.options import TargetProbeRunOptions, validate_run_path_part
from probe.python.run.case import run_prepared_case


def run_probe(args: argparse.Namespace, config: dict[str, Any]) -> Path:
    if args.latest_root is not None:
        if (
            args.buggy_root is not None
            or args.fixed_root is not None
            or args.fixed_python_bin is not None
        ):
            raise ValueError(
                "--latest-root cannot be combined with paired-revision options"
            )
        revisions = (("latest", args.latest_root, args.python_bin),)
    else:
        if args.buggy_root is None or args.fixed_root is None:
            raise ValueError(
                "provide --latest-root or both --buggy-root and --fixed-root"
            )
        revisions = (
            ("buggy", args.buggy_root, args.python_bin),
            ("fixed", args.fixed_root, args.fixed_python_bin or args.python_bin),
        )
    case = read_json(args.case_json)
    if case.get("project", args.project) != args.project:
        raise ValueError("--project does not match the selected case")
    run_id = args.run_id or f"{case['case_id']}-{time.time_ns()}"
    validate_run_path_part(run_id, "run_id")
    out_root = args.out_root or ARTIFACT_ROOT / "outputs" / args.project / "probe"
    values = {
        field.name: getattr(args, field.name)
        for field in fields(TargetProbeRunOptions)
        if hasattr(args, field.name)
    }
    env = load_env(*([args.env_file] if args.env_file else []))
    values["model"] = args.model if args.model is not None else (
        env.get("LLM_MODEL") or env.get("OPENAI_MODEL") or "gpt-5-mini"
    )
    options = TargetProbeRunOptions(**values)
    interpreters = {}
    for kind, root, override in revisions:
        binary = override or root / ".venv/bin/python"
        resolved = shutil.which(str(binary)) or (
            str(binary.absolute()) if binary.is_file() else None
        )
        if not resolved:
            raise ValueError(
                f"supply a prepared Python interpreter for {kind}: --python-bin"
            )
        interpreters[kind] = resolved
    result = run_prepared_case(
        case=case,
        buggy_root=args.buggy_root,
        fixed_root=args.fixed_root,
        latest_root=args.latest_root,
        config=config,
        options=options,
        run_dir=out_root / run_id,
        interpreters=interpreters,
    )
    print(result)
    return result
