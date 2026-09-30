"""The convenience launcher only supplies paths and forwards workflow options."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
spec = importlib.util.spec_from_file_location("artifact_launcher", ROOT / "run.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
PROJECTS = json.loads((ROOT / "resources/projects.json").read_text())


@pytest.mark.parametrize("workflow", ["augment", "probe", "llm_dependent"])
def test_language_runners_share_entrypoint_names(workflow):
    for language, suffix in (("python", "py"), ("typescript", "mjs")):
        assert (ROOT / "src" / workflow / language / f"runner.{suffix}").is_file()


def test_release_separates_code_resources_and_results():
    for directory in ("augment", "probe", "llm_dependent", "common", "cli", "collect_coverage"):
        assert (ROOT / "src" / directory).is_dir()
        assert not (ROOT / directory).exists()
    for name in ("inputs", "subjects", "benchmark", "projects.json"):
        assert (ROOT / "resources" / name).exists()
        assert not (ROOT / name).exists()
    assert (ROOT / "dataset/subjects.csv").is_file()
    assert not (ROOT / "results").exists()


@pytest.mark.parametrize("project", PROJECTS)
@pytest.mark.parametrize("workflow", ["augment", "llm-dependent"])
def test_bundled_defaults(project, workflow):
    command = launcher.command_for(workflow, project, [])
    native_ts = PROJECTS[project]["language"] == "typescript" and workflow == "augment"
    assert Path(command[1]) == ROOT / "src" / ("augment/typescript/runner.mjs" if native_ts else "cli/runner.py")
    assert command[command.index("--project") + 1] == project
    if not native_ts:
        assert command[2] == workflow
    flag = "--base-input" if workflow == "augment" else "--project-root"
    assert Path(command[command.index(flag) + 1]).exists()
    output_flag = "--out-root" if workflow == "augment" else "--out"
    output = Path(command[command.index(output_flag) + 1])
    assert project in output.parts
    if workflow == "augment":
        assert Path(command[command.index(flag) + 1]).parent.name == project
    if workflow == "llm-dependent":
        assert Path(command[command.index("--source-base") + 1]).is_file()


def test_budget_leaves_core_defaults_and_explicit_round_limit_intact():
    command = launcher.command_for("augment", "aider", ["--time-budget-seconds=7200"])
    assert command[command.index("--rounds") + 1] == "100000"
    explicit = launcher.command_for(
        "augment", "aider", ["--time-budget-seconds=7200", "--rounds=2"]
    )
    assert "--rounds" not in explicit
    assert "--rounds=2" in explicit
    assert "--repair-context-requests" not in explicit
    assert "--strategy" not in explicit


@pytest.mark.parametrize("project", ["aider", "openclaw"])
@pytest.mark.parametrize("options,rounds,budget", [
    ([], 1, 0),
    (["--time-budget-seconds", "0"], 1, 0),
    (["--time-budget-seconds=0"], 1, 0),
    (["--time-budget-seconds=-0.0"], 1, 0),
    (["--time-budget-seconds=0e3"], 1, 0),
    (["--time-budget-seconds", "0.5"], 100000, 0.5),
    (["--time-budget-seconds=7200"], 100000, 7200),
    (["--time-budget-seconds=7200", "--time-budget-seconds", "0"], 1, 0),
    (["--time-budget-seconds", "0", "--time-budget-seconds=7200"], 100000, 7200),
    (["--time-budget-seconds=7200", "--rounds", "3"], 3, 7200),
    (["--rounds=2", "--time-budget-seconds=0"], 2, 0),
    (["--rounds=2", "--time-budget-seconds=7200", "--rounds", "4"], 4, 7200),
])
def test_budget_defaults_follow_native_last_value(project, options, rounds, budget):
    command = launcher.command_for("augment", project, options)
    start = command.index("--project") + 2
    assert command[start:start + len(options)] == options
    if project == "aider":
        from cli.runner import build_parser

        parsed = build_parser().parse_args(command[2:])
        actual = [parsed.rounds, parsed.time_budget_seconds]
    else:
        script = (
            "const {parseAugmentArgs} = await import(process.argv[1]);"
            "const v = parseAugmentArgs('test', JSON.parse(process.argv[2]));"
            "console.log(JSON.stringify([Number(v.rounds), Number(v['time-budget-seconds'])]));"
        )
        actual = json.loads(subprocess.check_output([
            "node", "--input-type=module", "-e", script,
            (ROOT / "src/augment/typescript/run_cli.mjs").as_uri(),
            json.dumps(command[2:]),
        ], text=True, timeout=15))
    assert actual == [rounds, budget]


@pytest.mark.parametrize("value,expanded", [
    ("", False), ("  ", False), ("0x0", False), ("0x10", True),
    ("0b0", False), ("0b10", True), ("0o0", False), ("0o10", True),
])
def test_typescript_budget_numeric_forms_are_forwarded(value, expanded):
    option = f"--time-budget-seconds={value}"
    command = launcher.command_for("augment", "openclaw", [option])
    assert option in command
    assert ("--rounds" in command) == expanded


def test_user_paths_and_options_are_forwarded_without_rewriting():
    options = [
        "--base-input=custom.json",
        "--project-root",
        "checkout with spaces",
        "--out-root",
        "results",
        "--repair-context-requests=3",
    ]
    command = launcher.command_for("augment", "openclaw", options)
    assert command[command.index("--project") + 2:] == options


def test_extraction_output_alias_is_preserved():
    command = launcher.command_for(
        "llm-dependent", "aider", ["--output-json=custom.json"]
    )
    assert "--out" not in command


@pytest.mark.parametrize("project", ["aider", "openclaw"])
def test_extraction_source_list_override_is_preserved(project):
    command = launcher.command_for(
        "llm-dependent", project, ["--source-base=custom.json"]
    )
    assert "--source-base" not in command
    assert "--source-base=custom.json" in command


@pytest.mark.parametrize("project", ["aider", "openclaw"])
def test_probe_uses_case_roots_not_the_augmentation_snapshot(project):
    options = ["--case-json", "case.json", "--buggy-root=old", "--fixed-root=new"]
    command = launcher.command_for("probe", project, options)
    assert Path(command[1]) == ROOT / "src" / ("probe/typescript/runner.mjs" if project == "openclaw" else "cli/runner.py")
    start = command.index("--project") + 2
    assert command[start:start + len(options)] == options
    assert "--project-root" not in command
    with pytest.raises(ValueError, match="--buggy-root"):
        launcher.command_for("probe", project, ["--case-json=case.json"])


@pytest.mark.parametrize("project", ["pr-agent", "openclaw"])
def test_probe_latest_root_is_forwarded(project):
    options = ["--case-json=targets.json", "--latest-root=latest checkout"]
    command = launcher.command_for("probe", project, options)
    start = command.index("--project") + 2
    assert command[start:start + len(options)] == options
    assert "--buggy-root" not in command and "--fixed-root" not in command
    for flag in ["--buggy-root=old", "--fixed-root=fixed"]:
        with pytest.raises(ValueError, match="use --latest-root"):
            launcher.command_for("probe", project, [*options, flag])


def test_launcher_executes_command_and_returns_exit_status(monkeypatch):
    from types import SimpleNamespace

    calls = []

    def execute(command, *, check):
        assert check is False
        calls.append(command)
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr(launcher.subprocess, "run", execute)
    assert launcher.main(["augment", "--project", "aider", "--rounds=2"]) == 7
    assert calls == [launcher.command_for("augment", "aider", ["--rounds=2"])]


def test_setup_does_not_accept_workflow_flags():
    assert launcher.command_for("setup", "aider", [])[-1] == "aider"
    with pytest.raises(ValueError, match="setup accepts"):
        launcher.command_for("setup", "aider", ["--model=x"])


def test_unknown_project_fails_before_launch():
    with pytest.raises(ValueError, match="unknown project"):
        launcher.command_for("augment", "not-a-project", [])


@pytest.mark.parametrize("options,expected", [
    ([], "README.md"),
    (["probe", "--project", "pr-agent"], "--case-time-budget-seconds"),
    (["augment"], "--base-input"),
    (["llm-dependent"], "--source-base"),
    (["setup"], "--project"),
])
def test_standard_help_does_not_prepare_or_execute(monkeypatch, capsys, options, expected):
    from cli import probe_checkout

    def unexpected(*args, **kwargs):
        pytest.fail("help must not prepare source or launch a process")

    monkeypatch.setattr(probe_checkout, "prepare_probe", unexpected)
    monkeypatch.setattr(launcher.subprocess, "run", unexpected)
    with pytest.raises(SystemExit) as exc:
        launcher.main([*options, "--help"])
    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert expected in output
    if options[:1] == ["probe"]:
        assert "--case-id" in output and "--setup-script" in output


@pytest.mark.parametrize("workflow,expected", [
    ("augment", "--base-input"), ("probe", "--case-time-budget-seconds"),
])
def test_typescript_help_needs_no_installation_or_checkout(tmp_path, workflow, expected):
    copied = tmp_path / "release"
    shutil.copytree(
        ROOT / "src", copied / "src",
        ignore=shutil.ignore_patterns("tests", "node_modules", "__pycache__"),
    )
    (copied / "resources").mkdir()
    shutil.copy2(ROOT / "resources/projects.json", copied / "resources/projects.json")
    shutil.copy2(ROOT / "run.py", copied / "run.py")
    result = subprocess.run(
        [sys.executable, "-B", str(copied / "run.py"), workflow,
         "--project", "openclaw", "--help"],
        cwd=tmp_path, text=True, capture_output=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert expected in result.stdout
    if workflow == "probe":
        assert "--case-id" in result.stdout and "--setup-script" in result.stdout
    assert not (copied / "outputs").exists()
    assert not (copied / "resources/subjects").exists()


@pytest.mark.parametrize("python,python_bin,expected", [
    (None, None, "python3"),
    (None, "custom-python", "custom-python"),
    ("selected-python", "other-python", "selected-python"),
])
def test_typescript_extraction_preserves_interpreter_selection(monkeypatch, python, python_bin, expected):
    for key, value in [("PYTHON", python), ("PYTHON_BIN", python_bin)]:
        monkeypatch.delenv(key, raising=False)
        if value is not None:
            monkeypatch.setenv(key, value)
    command = launcher.command_for("llm-dependent", "openclaw", [])
    assert command[0] == expected
    assert command[-2:] == ["--language", "typescript"]
    assert launcher.command_for("augment", "openclaw", [])[0] == "node"
    assert launcher.command_for("llm-dependent", "pr-agent", [])[0] == sys.executable


def test_runtime_helpers_are_internal():
    assert {path.name for path in ROOT.glob("*.py")} == {"run.py"}
    assert not list(ROOT.glob("*.mjs"))
    assert not list(ROOT.glob("*.sh"))
    assert Path(launcher.command_for("setup", "pr-agent", [])[1]) == ROOT / "src/cli/setup.sh"


@pytest.mark.parametrize("settings", [
    {},
    {"constraints": []},
    {"constraints": ["Place generated pytest files under tests/unittest/."]},
])
@pytest.mark.parametrize("strategy", ["contract_directed", "contract_agnostic"])
def test_python_augment_project_constraints_are_optional(tmp_path, monkeypatch, settings, strategy):
    from unittest.mock import Mock

    from cli.runner import build_parser
    from augment.python import runner

    args = build_parser().parse_args([
        "augment", "--project", "fixture", "--base-input", "input.json",
        "--strategy", strategy,
    ])
    monkeypatch.setattr(runner, "build_initial_metric_snapshot", lambda *a, **kw: (
        {"project": "fixture"},
        {"project_root": str(tmp_path), "python": sys.executable,
         "coverage_source": "package", "test_pythonpath": []},
    ))
    monkeypatch.setattr(runner, "load_env", lambda _: {})
    execute = Mock(return_value=tmp_path)
    monkeypatch.setattr(runner, "run_python", execute)
    runner.run_augment(args, {"language": "python", "augment": settings})
    options = execute.call_args.kwargs["options"]
    assert options.constraints == settings.get("constraints", [])
    assert options.strategy == strategy
    assert options.out_root == ROOT / "outputs" / "fixture" / "augment"


@pytest.mark.parametrize("output", [None, "custom", "custom/selected.json"])
def test_extraction_runner_output_defaults(monkeypatch, output):
    from cli.runner import build_parser, run_extraction
    from llm_dependent.python import runner

    argv = ["llm-dependent", "--project", "fixture", "--source-base", "source_files.json",
            "--project-root", "checkout"]
    if output:
        argv += ["--out", output]
    args = build_parser().parse_args(argv)
    calls = []

    def extract(**kwargs):
        calls.append(kwargs)
        return kwargs["outputs"]["none"]

    monkeypatch.setattr(runner, "run_python", extract)
    actual = run_extraction(args, {"language": "python"})
    expected = Path(output) if output else ROOT / "outputs/fixture/extraction/regions.json"
    if expected.suffix != ".json":
        expected /= "regions.json"
    assert actual == expected
    assert calls[0]["outputs"]["direct"] == expected.with_name(f"{expected.stem}.control_dependence_direct.json")


def test_probe_runner_output_defaults(tmp_path, monkeypatch):
    from cli.runner import build_parser
    from probe.python import runner
    from unittest.mock import Mock

    case = tmp_path / "case.json"
    case.write_text(json.dumps({"case_id": "fixture"}))
    args = build_parser().parse_args([
        "probe", "--project", "fixture", "--case-json", str(case),
        "--buggy-root", "buggy", "--fixed-root", "fixed", "--run-id", "check",
        "--python-bin", sys.executable,
    ])
    execute = Mock(return_value=tmp_path)
    monkeypatch.setattr(runner, "run_prepared_case", execute)
    runner.run_probe(args, {"language": "python"})
    assert execute.call_args.kwargs["run_dir"] == ROOT / "outputs/fixture/probe/check"


@pytest.mark.parametrize("workflow", ["augment", "probe"])
@pytest.mark.parametrize("process_env,file_env,explicit,expected", [
    ({}, {}, None, "gpt-5-mini"),
    ({"OPENAI_MODEL": "process-model"}, {}, None, "process-model"),
    ({}, {"OPENAI_MODEL": "file-model"}, None, "file-model"),
    ({"OPENAI_MODEL": "process-model"}, {"OPENAI_MODEL": "file-model"}, None, "file-model"),
    ({}, {"LLM_MODEL": "llm-file", "OPENAI_MODEL": "openai-file"}, None, "llm-file"),
    ({"LLM_MODEL": "llm-process"}, {"OPENAI_MODEL": "file-model"}, None, "llm-process"),
    ({"LLM_MODEL": "process-model"}, {"LLM_MODEL": "file-model"}, None, "file-model"),
    ({}, {"OPENAI_MODEL": "file-model"}, "gpt-5-mini", "gpt-5-mini"),
    ({"LLM_MODEL": "process-model"}, {"OPENAI_MODEL": "file-model"}, "explicit-model", "explicit-model"),
])
def test_python_runner_resolves_model_after_env_file(
    tmp_path, monkeypatch, workflow, process_env, file_env, explicit, expected
):
    from unittest.mock import Mock

    from cli.runner import build_parser

    for name in ("LLM_MODEL", "OPENAI_MODEL"):
        monkeypatch.delenv(name, raising=False)
    for name, value in process_env.items():
        monkeypatch.setenv(name, value)
    env_file = tmp_path / "model.env"
    env_file.write_text("".join(f"{name}={value}\n" for name, value in file_env.items()))
    argv = [workflow, "--project", "fixture", "--env-file", str(env_file)]
    if explicit is not None:
        argv.extend(["--model", explicit])
    execute = Mock(return_value=tmp_path)
    if workflow == "augment":
        from augment.python import runner

        argv.extend(["--base-input", "input.json"])
        monkeypatch.setattr(runner, "build_initial_metric_snapshot", lambda *a, **kw: (
            {"project": "fixture"},
            {"project_root": str(tmp_path), "python": sys.executable,
             "coverage_source": "package", "test_pythonpath": []},
        ))
        monkeypatch.setattr(runner, "run_python", execute)
        invoke = runner.run_augment
    else:
        from probe.python import runner

        case = tmp_path / "case.json"
        case.write_text(json.dumps({"case_id": "fixture"}))
        argv.extend(["--case-json", str(case), "--latest-root", str(tmp_path),
                     "--python-bin", sys.executable])
        monkeypatch.setattr(runner, "run_prepared_case", execute)
        invoke = runner.run_probe
    invoke(build_parser().parse_args(argv), {"language": "python"})
    execute.assert_called_once()
    assert execute.call_args.kwargs["options"].model == expected


@pytest.mark.parametrize("latest", [False, True])
@pytest.mark.parametrize("invalid", [["--modle=x"], ["--samples=-1"]])
def test_launcher_rejects_invalid_probe_options_before_any_subprocess(
    tmp_path, monkeypatch, latest, invalid
):
    from cli import probe_checkout

    def unexpected(*args, **kwargs):
        pytest.fail("invalid arguments must not start preparation or a workflow")

    monkeypatch.setattr(probe_checkout, "checkout", unexpected)
    monkeypatch.setattr(launcher.subprocess, "run", unexpected)
    selection = (
        ["--project", "pr-agent", "--repository", "https://example.invalid/repo.git",
         "--revision", "a" * 40, "--target", "source.py"]
        if latest else ["--case-id", "pr-agent-946c3e22"]
    )
    with pytest.raises(SystemExit) as exc:
        launcher.main(["probe", *selection, "--out-root", str(tmp_path / "out"), *invalid])
    assert exc.value.code == 2
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("latest", [False, True])
def test_launcher_preserves_prepared_python_environment(tmp_path, monkeypatch, latest):
    from types import SimpleNamespace
    from cli import probe_checkout
    from probe.python import runner
    from cli.runner import build_parser

    case = tmp_path / "case.json"
    case.write_text(json.dumps({"case_id": "fixture", "project": "pr-agent"}))
    root_args = []
    interpreters = {}
    for kind in (("latest",) if latest else ("buggy", "fixed")):
        root = tmp_path / kind
        binary = root / ".venv/bin/python"
        binary.parent.mkdir(parents=True)
        binary.symlink_to(sys.executable)
        root_args.extend([f"--{kind}-root", str(root)])
        interpreters[kind] = str(binary)

    def unexpected(*args, **kwargs):
        pytest.fail("prepared environments must not trigger preparation")

    calls = []

    def execute_workflow(**kwargs):
        calls.append(kwargs)
        return tmp_path

    def dispatch(command, *, check):
        assert Path(command[1]) == ROOT / "src/cli/runner.py"
        args = build_parser().parse_args(command[2:])
        runner.run_probe(args, PROJECTS[args.project])
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(probe_checkout, "checkout", unexpected)
    monkeypatch.setattr(probe_checkout, "run_step", unexpected)
    monkeypatch.setattr(runner, "run_prepared_case", execute_workflow)
    monkeypatch.setattr(launcher.subprocess, "run", dispatch)
    assert launcher.main(["probe", "--case-json", str(case), *root_args]) == 0
    assert len(calls) == 1
    assert calls[0]["interpreters"] == interpreters


@pytest.mark.parametrize("latest", [False, True])
def test_native_python_probe_rejects_conflicting_case_project(tmp_path, monkeypatch, latest):
    from cli.runner import build_parser
    from probe.python import runner

    case = tmp_path / "case.json"
    case.write_text(json.dumps({"project": "pr-agent", "case_id": "fixture"}))
    roots = ["--latest-root=latest"] if latest else ["--buggy-root=old", "--fixed-root=new"]
    args = build_parser().parse_args([
        "probe", "--project", "aider", "--case-json", str(case), *roots,
    ])
    monkeypatch.setattr(runner, "run_prepared_case", lambda **kw: pytest.fail("unexpected workflow"))
    with pytest.raises(ValueError, match="--project does not match"):
        runner.run_probe(args, PROJECTS["aider"])


@pytest.mark.parametrize("latest", [False, True])
def test_native_typescript_probe_rejects_conflicting_case_project(tmp_path, latest):
    case = tmp_path / "case.json"
    case.write_text(json.dumps({"project": "openclaw", "case_id": "fixture"}))
    roots = ["--latest-root=latest"] if latest else ["--buggy-root=old", "--fixed-root=new"]
    result = subprocess.run([
        "node", str(ROOT / "src/probe/typescript/runner.mjs"),
        "--project", "roo-code", "--case-json", str(case),
        "--out-root", str(tmp_path / "out"), *roots,
    ], cwd=tmp_path, text=True, capture_output=True, timeout=15)
    assert result.returncode != 0
    assert "--project does not match the selected case" in result.stderr
    assert not (tmp_path / "out").exists()


def test_copied_launcher_runs_outside_repository(tmp_path):
    copied = tmp_path / "copied artifact"
    for name in ("cli", "common", "llm_dependent"):
        shutil.copytree(
            ROOT / "src" / name,
            copied / "src" / name,
            ignore=shutil.ignore_patterns("tests", "node_modules", "__pycache__"),
        )
    (copied / "resources").mkdir()
    for name in ("run.py", "resources/projects.json"):
        shutil.copy2(ROOT / name, copied / name)
    source = copied / "resources/subjects/pr-agent/pr_agent/example.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "from litellm import completion\n"
        "def run(messages):\n"
        "    response = completion(model='fixture', messages=messages)\n"
        "    return response\n"
    )
    source_base = copied / "resources/inputs/pr-agent/source_files.json"
    source_base.parent.mkdir(parents=True)
    source_base.write_text(json.dumps({"files": ["pr_agent/example.py"]}))
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    result = subprocess.run(
        [
            sys.executable,
            str(copied / "run.py"),
            "llm-dependent",
            "--project",
            "pr-agent",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    output = copied / "outputs/pr-agent/extraction/regions.json"
    assert json.loads(output.read_text())["sources"]
    for mode in ("direct", "recursive"):
        assert output.with_name(f"regions.control_dependence_{mode}.json").is_file()
