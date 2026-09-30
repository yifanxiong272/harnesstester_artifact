#!/usr/bin/env python3
"""Run the bundled subjects with their prepared inputs and native workflows."""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))


def supplied(arguments: list[str], *names: str) -> bool:
    return any(item.split("=", 1)[0] in names for item in arguments)


def workflow_command(
    command: str, project: str, language: str, options: list[str], root: Path
) -> list[str]:
    """Invoke the existing runner with its original interpreter and arguments."""
    if language == "typescript" and command in {"augment", "probe"}:
        return [
            "node",
            str(root / "src" / command / "typescript" / "runner.mjs"),
            "--project",
            project,
            *options,
        ]
    python = sys.executable
    if language == "typescript":
        python = os.environ.get("PYTHON") or os.environ.get("PYTHON_BIN") or "python3"
        options = [*options, "--language", "typescript"]
    return [
        python, str(root / "src" / "cli" / "runner.py"), command, "--project", project, *options
    ]


def command_for(
    command: str, project: str, arguments: list[str], *, root: Path = ROOT
) -> list[str]:
    """Add portable defaults while leaving explicit workflow options intact."""
    projects = json.loads((root / "resources" / "projects.json").read_text())
    if project not in projects:
        raise ValueError(f"unknown project: {project}")
    if command == "setup":
        if arguments:
            raise ValueError(
                "setup accepts only --project; PYTHON selects its interpreter"
            )
        return ["bash", str(root / "src" / "cli" / "setup.sh"), project]

    language = projects[project]["language"]
    options = list(arguments)

    def default(flag: str, value: str | Path, *aliases: str) -> None:
        if not supplied(options, flag, *aliases):
            options.extend([flag, str(value)])

    if command == "llm-dependent":
        default("--project-root", root / "resources" / "subjects" / project)
        default(
            "--out",
            root / "outputs" / project / "extraction" / "regions.json",
            "--output-json",
        )
        default("--source-base", root / "resources" / "inputs" / project / "source_files.json")
    elif command == "augment":
        default("--base-input", root / "resources" / "inputs" / project / "base_input.json")
        default("--out-root", root / "outputs" / project / "augment")
        if not supplied(options, "--rounds"):
            budget_parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
            budget_parser.add_argument("--time-budget-seconds", default="0")
            budget, _ = budget_parser.parse_known_args(options)
            value = budget.time_budget_seconds.strip() or "0"
            try:
                seconds = float(value)
            except ValueError:
                # Native TypeScript options also accept radix-prefixed numbers.
                try:
                    seconds = int(value, 0)
                except ValueError:
                    seconds = 0  # Leave invalid values to the native runner.
            if seconds > 0:
                default("--rounds", "100000")
    elif command == "probe":
        latest = supplied(options, "--latest-root")
        if latest and supplied(options, "--buggy-root", "--fixed-root"):
            raise ValueError("use --latest-root or the --buggy-root/--fixed-root pair")
        required = (
            ("--case-json", "--latest-root")
            if latest
            else ("--case-json", "--buggy-root", "--fixed-root")
        )
        for flag in required:
            if not supplied(options, flag):
                raise ValueError(
                    f"probe requires {flag}; supply the case's prepared checkout(s)"
                )
        default("--out-root", root / "outputs" / project / "probe")
    else:
        raise ValueError(f"unknown workflow: {command}")
    return workflow_command(command, project, language, options, root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Commands and workflow options: README.md.",
        allow_abbrev=False,
        add_help=False,
    )
    parser.add_argument("-h", "--help", action="store_true", help="show command help and exit")
    parser.add_argument(
        "command", nargs="?", choices=["setup", "llm-dependent", "augment", "probe"]
    )
    parser.add_argument(
        "--project", help="project name; inferred from a Probe case when omitted"
    )
    args, remaining = parser.parse_known_args(argv)
    try:
        if args.help:
            if args.command is None or args.command == "setup":
                parser.print_help()
                parser.exit()
            if args.command == "probe":
                from cli.probe_checkout import preparation_parser

                preparation_parser().print_help()
            projects = json.loads((ROOT / "resources/projects.json").read_text())
            if args.project and args.project not in projects:
                raise ValueError(f"unknown project: {args.project}")
            language = projects[args.project]["language"] if args.project else "python"
            if language == "typescript" and args.command in {"augment", "probe"}:
                command = workflow_command(args.command, args.project, language, ["--help"], ROOT)
                sys.stdout.flush()
                return subprocess.run(command, check=False).returncode
            from cli.runner import build_parser

            build_parser().parse_args([args.command, "--help"])
        if args.command is None:
            parser.error("a command is required")
        if args.command == "probe":
            from cli.probe_checkout import prepare_probe

            prepared = prepare_probe(args.project, remaining, root=ROOT)
        else:
            if not args.project:
                raise ValueError("--project is required")
            prepared = nullcontext((args.project, remaining))
        with prepared as (project, options):
            command = command_for(args.command, project, options)
            print(shlex.join(command), flush=True)
            return subprocess.run(command, check=False).returncode
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
