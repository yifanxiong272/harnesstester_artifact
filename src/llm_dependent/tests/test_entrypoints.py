"""Check language dispatch and extraction options independently of analysis."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ARTIFACT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ARTIFACT))

from cli import runner as cli
from llm_dependent.python import runner
from common.projects import project_config


@pytest.mark.parametrize("output", [None, "regions.json", "output.dir"])
@pytest.mark.parametrize("overrides", [False, True])
def test_python_dispatch_preserves_paths_and_modes(
    tmp_path, monkeypatch, output, overrides
):
    options = [
        "llm-dependent",
        "--project",
        "pr-agent",
        "--project-root",
        str(tmp_path),
        "--source-base",
        "files.json",
    ]
    if output:
        options += ["--out", str(tmp_path / output)]
    if overrides:
        options += [
            "--source-base",
            "custom.json",
            "--control-direct-output-json",
            "direct.json",
            "--control-recursive-output-json",
            "recursive.json",
        ]
    args = cli.build_parser().parse_args(options)
    config = project_config("pr-agent")
    if overrides:
        config["label"] = "Fixture"
    monkeypatch.setattr(cli, "ARTIFACT_ROOT", tmp_path)
    execute = Mock()
    monkeypatch.setattr(runner, "run_python", execute)
    cli.run_extraction(args, config)
    out = tmp_path / output if output else tmp_path / "outputs/pr-agent/extraction/regions.json"
    if out.suffix != ".json":
        out /= "regions.json"
    execute.assert_called_once_with(
        project_root=tmp_path.resolve(),
        source_base=Path("custom.json" if overrides else "files.json"),
        project_label="Fixture" if overrides else "pr-agent",
        outputs={
            "none": out,
            "direct": Path("direct.json")
            if overrides
            else out.with_name(f"{out.stem}.control_dependence_direct.json"),
            "recursive": Path("recursive.json")
            if overrides
            else out.with_name(f"{out.stem}.control_dependence_recursive.json"),
        },
    )


@pytest.mark.parametrize("project", ["openclaw", "roo-code", "kimi-code"])
@pytest.mark.parametrize("overrides", [False, True])
def test_typescript_dispatch_preserves_native_options(
    tmp_path, monkeypatch, overrides, project
):
    options = [
        "llm-dependent",
        "--project",
        project,
        "--project-root",
        str(tmp_path),
        "--source-base",
        "files.json",
        "--out",
        "regions.json",
    ]
    if overrides:
        options += [
            "--compact-output-json",
            "compact.json",
            "--max-iterations",
            "7",
            "--control-dependence-mode",
            "control-dependence-recursive",
            "--typescript-root",
            "compiler",
        ]
    execute = Mock(return_value=SimpleNamespace(returncode=0, stdout=""))
    monkeypatch.setattr(cli.subprocess, "run", execute)
    cli.main(argv=options)
    execute.assert_called_once()
    assert execute.call_args.args[0] == [
        "node",
        "--max-old-space-size=12288",
        str(ARTIFACT / "llm_dependent/typescript/runner.mjs"),
    ]
    expected = {
        "root": str(tmp_path.resolve()),
        "sourceBase": "files.json",
        "out": "regions.json",
        "compactOut": "compact.json" if overrides else "regions.compact.json",
        "controlDependenceMode": "control-dependence-recursive"
        if overrides
        else "block_only",
        "maxIterations": 7 if overrides else 120,
    }
    if overrides:
        expected["typescriptRoot"] = "compiler"
    assert json.loads(execute.call_args.kwargs["input"]) == expected


@pytest.mark.parametrize(
    "flag", ["--coverage-json", "--augment-snapshot-output-json", "--out-root", "--run-id"]
)
@pytest.mark.parametrize("project", ["pr-agent", "openclaw"])
def test_extraction_rejects_non_extraction_options(flag, project, capsys):
    with pytest.raises(SystemExit) as error:
        cli.main(argv=["llm-dependent", "--project", project, flag, "data.json"])
    assert error.value.code == 2
    assert f"unrecognized arguments: {flag}" in capsys.readouterr().err


def test_python_extraction_preserves_output_format(tmp_path, monkeypatch):
    source = tmp_path / "agent.py"
    source.write_text("response = None\n")
    source_base = tmp_path / "source_files.json"
    source_base.write_text(json.dumps({"files": [source.name]}))
    payloads = {
        mode: {"sources": [], "data_dependence": [], "mode": mode}
        for mode in ("none", "direct", "recursive")
    }
    analyze = Mock(return_value=payloads)
    monkeypatch.setattr(runner, "analyze_flow_project_outputs", analyze)
    outputs = {mode: tmp_path / "results" / f"{mode}.json" for mode in payloads}
    assert runner.run_python(
        project_root=tmp_path,
        source_base=source_base,
        project_label="Fixture",
        outputs=outputs,
    ) == outputs["none"]
    analyze.assert_called_once_with(
        project_root=tmp_path,
        source_files=[source],
        project_label="Fixture",
        control_modes=("none", "direct", "recursive"),
    )
    for mode, output in outputs.items():
        assert output.read_text() == json.dumps(payloads[mode], indent=2, sort_keys=True) + "\n"
    assert set((tmp_path / "results").iterdir()) == set(outputs.values())


def test_python_requires_explicit_source_list():
    with pytest.raises(SystemExit, match="requires --source-base"):
        cli.main(argv=["llm-dependent", "--project", "pr-agent"])


def test_typescript_requires_source_list_and_reports_native_failure(
    tmp_path, monkeypatch
):
    options = [
        "llm-dependent",
        "--project",
        "openclaw",
        "--project-root",
        str(tmp_path),
    ]
    execute = Mock(
        return_value=SimpleNamespace(returncode=1, stdout="native failure\n")
    )
    monkeypatch.setattr(cli.subprocess, "run", execute)
    with pytest.raises(SystemExit, match="requires --source-base"):
        cli.main(argv=options)
    execute.assert_not_called()
    with pytest.raises(SystemExit, match="native failure"):
        cli.main(argv=[*options, "--source-base", "files.json"])
