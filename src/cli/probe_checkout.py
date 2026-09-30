"""Prepare pinned Probe checkouts before invoking a language-native workflow."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import signal
import subprocess
import tempfile
import time
import zipfile


def find_case(root: Path, case_id: str) -> Path:
    """Locate one case in a release or per-project case collection."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", case_id):
        raise ValueError("case ID must be a simple directory name")
    candidates = {
        root / case_id / "case.json",
        root / "cases" / case_id / "case.json",
        *root.glob(f"cases/*/{case_id}.json"),
        *root.glob(f"*/benchmarkBR/cases/{case_id}/case.json"),
    }
    matches = sorted({path.resolve() for path in candidates if path.is_file()})
    if len(matches) != 1:
        raise ValueError(
            f"expected one case {case_id} under {root}; found {len(matches)}"
        )
    return matches[0]


def prepare_dependencies(root: Path, archive_path: Path, directory: Path, log) -> None:
    """Verify upstream files and stage supplemental resolved inputs separately."""
    root, directory = root.resolve(), directory.resolve()
    matched = 0
    with zipfile.ZipFile(archive_path) as archive:
        for entry in archive.infolist():
            relative = PurePosixPath(entry.filename)
            supplemental = relative.parts[:1] == ("resolved",)
            base = directory if supplemental else root
            target = (base / relative).resolve()
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or not target.is_relative_to(base)
            ):
                raise ValueError(f"invalid dependency path: {entry.filename}")
            if entry.is_dir():
                continue
            content = archive.read(entry)
            if supplemental:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            elif not target.is_file() or target.read_bytes() != content:
                raise ValueError(
                    f"dependency mismatch: {entry.filename}; archive: {archive_path}"
                )
            else:
                matched += 1
        log.write(
            f"Dependencies: {archive_path.name}; {matched} files matched\n"
        )
        log.flush()


def run_step(
    command: list[str], cwd: Path, log, env: dict[str, str], timeout: int
) -> None:
    """Record preparation output and stop its process group on interruption."""
    log.write(f"$ {shlex.join(command)}\n")
    log.flush()
    with subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    ) as process:
        def interrupt(signum, frame):
            raise SystemExit(128 + signum)

        previous = signal.signal(signal.SIGTERM, interrupt)
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            for sig, grace in ((signal.SIGTERM, 3), (signal.SIGKILL, None)):
                try:
                    os.killpg(process.pid, sig)
                except ProcessLookupError:
                    break
                try:
                    process.wait(timeout=grace)
                except subprocess.TimeoutExpired:
                    continue
                if sig == signal.SIGKILL:
                    break
            raise
        finally:
            signal.signal(signal.SIGTERM, previous)
    if code:
        raise ValueError(f"preparation command exited {code}; see {log.name}")


def checkout(
    repository: str, revision: str, destination: Path, log, env: dict[str, str]
) -> None:
    """Fetch the requested commit into a fresh, shallow checkout."""
    destination.mkdir()
    commands = [
        [
            "git",
            "init",
            "-q",
            f"--object-format={'sha256' if len(revision) == 64 else 'sha1'}",
        ],
        ["git", "remote", "add", "origin", repository],
        ["git", "fetch", "--no-tags", "--depth=1", "origin", revision],
        [
            "git",
            "-c",
            "advice.detachedHead=false",
            "checkout",
            "--detach",
            "FETCH_HEAD",
        ],
    ]
    for command in commands:
        run_step(command, destination, log, env, 300)


def verify_checkout(root: Path, revision: str, log, env: dict[str, str]) -> None:
    """Require the selected revision and unchanged tracked source after setup."""
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        env=env,
        text=True,
        timeout=30,
    ).strip()
    if head != revision.lower():
        raise ValueError(f"checkout revision mismatch: expected {revision}, got {head}")
    run_step(["git", "diff", "--exit-code", "HEAD", "--"], root, log, env, 30)


def file_targets(root: Path, files: list[str]) -> list[dict]:
    """Build target-unit records for selected complete files."""
    targets = []
    for name in dict.fromkeys(files):
        relative = PurePosixPath(name)
        path = (root / relative).resolve()
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not path.is_relative_to(root)
        ):
            raise ValueError(f"target must be a checkout-relative file: {name}")
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if not lines:
            raise ValueError(f"target file is empty: {name}")
        targets.append(
            {
                "unit_id": f"{relative}::<module>@1-{lines}:file",
                "filepath": str(relative),
                "qualname": "<module>",
                "kind": "file",
                "start_line": 1,
                "end_line": lines,
            }
        )
    return targets


def preparation_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 run.py probe",
        description="Checkout preparation options (in addition to workflow options below)",
        add_help=False,
        allow_abbrev=False,
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--case-json", type=Path)
    selection.add_argument("--case-id")
    parser.add_argument("--cases-root", type=Path)
    parser.add_argument("--repository")
    parser.add_argument("--revision")
    parser.add_argument("--target", action="append", default=[])
    parser.add_argument("--setup-script", type=Path)
    return parser


def validate_workflow_options(
    project: str, language: str, arguments: list[str], *, root: Path
) -> None:
    """Use the native parser before creating checkouts or installing dependencies."""
    if language == "typescript":
        result = subprocess.run(
            [
                "node", "--input-type=module", "-e",
                "const { parseProbeArgs } = await import(process.argv[1]); "
                "parseProbeArgs(JSON.parse(process.argv[2]));",
                (root / "src/probe/typescript/runner.mjs").resolve().as_uri(),
                json.dumps(["--project", project, *arguments]),
            ],
            text=True, capture_output=True, check=False,
        )
        if result.returncode:
            raise ValueError(result.stderr.strip() or "invalid Probe workflow options")
        return

    from cli.runner import build_parser
    from probe.python.run.options import (
        PAIRED_REVEAL_EVALUATION, validate_run_options, validate_run_path_part,
    )

    options = build_parser().parse_args(["probe", "--project", project, *arguments])
    if options.language not in {None, "python"}:
        raise ValueError("--language must match the Python project")
    options.evaluation_mode = PAIRED_REVEAL_EVALUATION
    validate_run_options(options)
    if options.run_id:
        validate_run_path_part(options.run_id, "run_id")


@contextmanager
def prepare_probe(
    project: str | None, arguments: list[str], *, root: Path
):
    """Resolve external inputs, prepare source when needed, and forward core options."""
    parser = preparation_parser()
    args, forwarded = parser.parse_known_args(arguments)

    workflow = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    for flag in (
        "buggy-root",
        "fixed-root",
        "latest-root",
        "out-root",
        "python-bin",
        "fixed-python-bin",
        "run-id",
    ):
        workflow.add_argument(f"--{flag}")
    options, _ = workflow.parse_known_args(forwarded)
    manual = any((options.buggy_root, options.fixed_root, options.latest_root))
    if args.cases_root and not args.case_id:
        raise ValueError("--cases-root requires --case-id")
    projects = json.loads((root / "resources" / "projects.json").read_text())
    if project:
        if project not in projects:
            raise ValueError("provide a known --project or a case with a registered project")
        validate_workflow_options(
            project, projects[project]["language"],
            ["--case-json", str(args.case_json or "targets.json"), *forwarded], root=root,
        )
    if manual:
        if options.latest_root and (options.buggy_root or options.fixed_root):
            raise ValueError("use --latest-root or the --buggy-root/--fixed-root pair")
        if not options.latest_root and not (options.buggy_root and options.fixed_root):
            raise ValueError("provide both --buggy-root and --fixed-root")
        if args.repository or args.revision or args.target or args.setup_script:
            raise ValueError(
                "checkout preparation options cannot be combined with prepared roots"
            )
        if not args.case_json and not args.case_id:
            raise ValueError("probe requires --case-json or --case-id")
    if args.case_id:
        cases_root = args.cases_root or Path(
            os.environ.get("BENCHMARK_RELEASE_ROOT", root / "resources" / "benchmark")
        )
        args.case_json = find_case(cases_root, args.case_id)
        selected = json.loads(args.case_json.read_text())
        if selected.get("case_id") != args.case_id:
            raise ValueError("case ID does not match the selected case.json")
        if project and selected.get("project", project) != project:
            raise ValueError("--project does not match the selected case")

    case = json.loads(args.case_json.read_text()) if args.case_json else {}
    if args.case_json and (not isinstance(case, dict) or not case.get("case_id")):
        raise ValueError("case JSON must contain case_id")
    if not project:
        project = case.get("project")
        if project not in projects:
            raise ValueError("provide a known --project or a case with a registered project")
        validate_workflow_options(
            project, projects[project]["language"],
            ["--case-json", str(args.case_json or "targets.json"), *forwarded], root=root,
        )
    if case.get("project", project) != project:
        raise ValueError("--project does not match the selected case")

    # Caller-provided checkouts bypass download and installation.
    if manual:
        yield project, ["--case-json", str(args.case_json), *forwarded]
        return

    repository = args.repository or case.get("repository")
    if not repository:
        raise ValueError(
            "automatic checkout requires a case repository or --repository"
        )
    if Path(repository).exists():
        repository = str(Path(repository).resolve())
    revisions = case.get("revisions", {})
    latest = not case or "latest" in revisions
    if latest:
        if "buggy" in revisions or "fixed" in revisions or options.fixed_python_bin:
            raise ValueError("latest discovery cannot use paired-revision options")
        if args.revision and case and revisions.get("latest") != args.revision:
            raise ValueError("--revision conflicts with the target-selection revision")
        revisions = {"latest": args.revision or revisions.get("latest")}
    elif args.revision or args.target:
        raise ValueError("--revision and --target are for latest-revision discovery")
    else:
        revisions = {kind: revisions.get(kind) for kind in ("buggy", "fixed")}
    for revision in revisions.values():
        if not isinstance(revision, str) or not re.fullmatch(
            r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", revision
        ):
            raise ValueError(
                "automatic checkout requires full commit hashes for every revision"
            )
    if args.case_json and args.target:
        raise ValueError("use a target-selection JSON or --target, not both")
    if not case and not args.target:
        raise ValueError(
            "latest discovery requires --target or a target-selection JSON"
        )
    if case and not (
        case.get("target_units")
        if latest
        else case.get("patch_targets", {}).get("target_units")
    ):
        raise ValueError("selected case has no target units")

    script = args.setup_script.resolve() if args.setup_script else None
    if script and not script.is_file():
        raise ValueError(f"setup script does not exist: {script}")
    profiles = {}
    if not script and not (
        projects[project]["language"] == "python" and options.python_bin
    ):
        if latest or args.repository or options.fixed_python_bin:
            raise ValueError(
                "automatic checkout requires --setup-script or an existing Python --python-bin"
            )
        from cli.benchmark_setup import setup_profiles

        profiles = setup_profiles(root / "resources" / "benchmark", args.case_json, case)
    if not case:
        case = {"case_id": f"{project}-{revisions['latest'][:12]}", "project": project}
    case_id = str(case["case_id"])
    run_id = options.run_id or f"{case_id}-{time.time_ns()}"
    if run_id == "preparation" or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]*", run_id
    ):
        raise ValueError("run ID must be a simple directory name")
    out = Path(options.out_root or root / "outputs" / project / "probe").resolve()
    records = out / "preparation" / run_id
    case_path = args.case_json.resolve() if args.case_json else records / "targets.json"
    if not options.run_id:
        forwarded.extend(["--run-id", run_id])
    if (out / run_id).exists():
        raise ValueError(f"run output already exists: {out / run_id}")
    records.mkdir(parents=True, exist_ok=False)
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"}
    }
    env["GIT_TERMINAL_PROMPT"] = "0"
    with tempfile.TemporaryDirectory(prefix="lci_probe_checkout_") as temporary:
        roots = {}
        with (records / "prepare.log").open("w", encoding="utf-8") as log:
            for kind, revision in revisions.items():
                destination = Path(temporary).resolve() / kind
                print(
                    f"Preparing {project} {kind} at {revision}; log: {log.name}",
                    flush=True,
                )
                checkout(repository, revision, destination, log, env)
                verify_checkout(destination, revision, log, env)
                dependency_dir = Path(temporary) / "dependencies" / kind
                dependency = case.get("dependencies", {}).get(kind)
                if isinstance(dependency, str):
                    prepare_dependencies(
                        destination, args.case_json.parent / dependency, dependency_dir, log
                    )
                if script:
                    setup_env = {
                        **env,
                        "PROBE_PROJECT": project,
                        "PROBE_REVISION_KIND": kind,
                        "PROBE_REVISION": revision,
                    }
                    run_step(["bash", str(script)], destination, log, setup_env, 1800)
                    verify_checkout(destination, revision, log, env)
                elif profiles:
                    from cli.benchmark_setup import install_environment

                    install_environment(
                        destination,
                        dependency_dir,
                        profiles[kind],
                        projects[project]["language"],
                        log,
                        env,
                        run_step,
                    )
                    verify_checkout(destination, revision, log, env)
                roots[kind] = destination
        if not args.case_json:
            case.update(
                repository=repository,
                revisions=revisions,
                target_units=file_targets(roots["latest"], args.target),
            )
            case_path.write_text(json.dumps(case, indent=2) + "\n", encoding="utf-8")
        (records / "checkouts.json").write_text(
            json.dumps(
                {
                    "repository": repository,
                    "revisions": revisions,
                    "case_json": str(case_path),
                    "setup_script": str(script) if script else None,
                    **({"setup_profiles": profiles} if profiles else {}),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        root_options = [
            item
            for kind, path in roots.items()
            for item in (f"--{kind}-root", str(path))
        ]
        yield project, ["--case-json", str(case_path), *forwarded, *root_options]
