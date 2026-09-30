"""Parse workflow arguments and dispatch to language-specific runners."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.projects import (
    ARTIFACT_ROOT,
    project_config,
    project_root as configured_project_root,
)


def common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", required=True)
    parser.add_argument("--language", choices=["python", "typescript"])


def model_options(
    parser: argparse.ArgumentParser, *, execution_options: bool = True
) -> None:
    parser.add_argument("--model")
    parser.add_argument(
        "--provider",
        choices=["openai", "openrouter"],
        default=os.environ.get("LLM_PROVIDER") or "openai",
    )
    parser.add_argument("--env-file", type=Path)
    if execution_options:
        parser.add_argument("--model-timeout", type=int, default=120)
        parser.add_argument("--model-retries", type=int, default=4)


def probe_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--case-json", type=Path, required=True)
    parser.add_argument("--buggy-root", type=Path)
    parser.add_argument("--fixed-root", type=Path)
    parser.add_argument("--latest-root", type=Path)
    parser.add_argument("--python-bin", type=Path)
    parser.add_argument("--fixed-python-bin", type=Path)
    parser.add_argument(
        "--strategy",
        choices=[
            "target_probe_ldh",
            "target_probe_contract_agnostic",
        ],
        default="target_probe_ldh",
    )
    for flag, default, aliases in (
        ("direct-samples", 10, ()),
        ("samples", 10, ()),
        ("soft-samples", 2, ()),
        ("assets-per-sample", 5, ()),
        ("timeout", 240, ()),
        ("context-requests", 1, ()),
        ("harness-context-requests", 1, ("--repair-context-requests",)),
        ("harness-repair-attempts", 1, ("--repair-attempts",)),
        ("harness-repairs-per-sample", 1, ()),
        ("minimize-buggy-failures-per-sample", 1, ()),
        ("minimization-preserve-attempts", 1, ()),
        ("minimization-failure-excerpt-chars", 1000, ()),
        ("max-workflow-errors", 2, ()),
        ("max-reveal-candidates", 1, ("--max-reveals",)),
        ("reveal-confirmation-runs", 2, ("--confirmations",)),
    ):
        parser.add_argument(f"--{flag}", *aliases, type=int, default=default)
    parser.add_argument("--case-time-budget-seconds", type=float, default=1800)
    parser.set_defaults(model_retries=5)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 run.py",
        description="Run extraction, augmentation, or probing for a registered project",
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    dep = sub.add_parser("llm-dependent", help="extract compact LDH regions")
    common_options(dep)
    dep.add_argument("--project-root", type=Path)
    dep.add_argument("--output-json", "--out", dest="output_json", type=Path)
    dep.add_argument("--source-base", type=Path)
    dep.add_argument("--typescript-root", type=Path)
    dep.add_argument("--compact-output-json", type=Path)
    dep.add_argument("--control-direct-output-json", type=Path)
    dep.add_argument("--control-recursive-output-json", type=Path)
    dep.add_argument(
        "--control-dependence-mode",
        choices=[
            "block_only",
            "control-dependence-direct",
            "control-dependence-recursive",
        ],
        default="block_only",
    )
    dep.add_argument(
        "--max-iterations", type=int, default=120, help="TypeScript fixed-point limit"
    )

    aug = sub.add_parser("augment", help="run one-project coverage-guided augmentation")
    common_options(aug)
    model_options(aug, execution_options=False)
    aug.add_argument("--project-root", type=Path)
    aug.add_argument("--out-root", type=Path)
    aug.add_argument("--run-id")
    aug.add_argument("--base-input", type=Path)
    aug.add_argument("--rounds", type=int, default=1)
    aug.add_argument("--time-budget-seconds", type=float, default=0.0)
    aug.add_argument("--timeout", type=int)
    aug.add_argument("--python-bin", type=Path)
    aug.add_argument(
        "--strategy",
        choices=["contract_directed", "contract_agnostic"],
        default="contract_directed",
    )
    aug.add_argument(
        "--acceptance-policy",
        choices=["passing_subset", "candidate_atomic"],
        default="passing_subset",
    )
    aug.add_argument("--repair-context-requests", type=int, default=0)

    probe = sub.add_parser(
        "probe", help="probe one paired case or latest-revision target selection", allow_abbrev=False
    )
    common_options(probe)
    model_options(probe)
    probe_options(probe)
    probe.add_argument("--out-root", type=Path)
    probe.add_argument("--run-id")

    return parser


def run_extraction(args: argparse.Namespace, config: dict[str, Any]) -> Path:
    """Resolve extraction CLI paths and dispatch to the language-native runner."""
    if args.source_base is None:
        raise SystemExit(f"{args.project} requires --source-base")
    root = configured_project_root(config, args.project_root)
    out = args.output_json or ARTIFACT_ROOT / "outputs" / args.project / "extraction" / "regions.json"
    if out.suffix != ".json":
        out = out / "regions.json"

    def sidecar(suffix: str) -> Path:
        return out.with_name(f"{out.stem}.{suffix}.json")

    if config["language"] == "python":
        from llm_dependent.python.runner import run_python

        return run_python(
            project_root=root,
            source_base=args.source_base,
            project_label=str(config.get("label") or args.project),
            outputs={
                "none": out,
                "direct": args.control_direct_output_json
                or sidecar("control_dependence_direct"),
                "recursive": args.control_recursive_output_json
                or sidecar("control_dependence_recursive"),
            },
        )

    payload = {
        "root": str(root),
        "sourceBase": str(args.source_base),
        "out": str(out),
        "compactOut": str(args.compact_output_json or sidecar("compact")),
        "controlDependenceMode": args.control_dependence_mode,
        "maxIterations": args.max_iterations,
    }
    if args.typescript_root:
        payload["typescriptRoot"] = str(args.typescript_root)
    result = subprocess.run(
        [
            "node",
            "--max-old-space-size=12288",
            str(ARTIFACT_ROOT / "src" / "llm_dependent" / "typescript" / "runner.mjs"),
        ],
        input=json.dumps(payload),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stdout)
    print(result.stdout.rstrip())
    return out


def main(default_language: str | None = None, argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    language = args.language or default_language
    config = project_config(args.project, language=language)
    if args.command == "llm-dependent":
        run_extraction(args, config)
    elif args.command == "augment":
        from augment.python.runner import run_augment

        run_augment(args, config)
    elif args.command == "probe":
        if config["language"] != "python":
            raise SystemExit(
                "Use python3 run.py probe --project NAME for TypeScript projects"
            )
        from probe.python.runner import run_probe

        run_probe(args, config)
    else:
        raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    main("python")
