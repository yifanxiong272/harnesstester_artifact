"""Pinned source preparation stays outside the Probe workflow and its budget."""

import importlib.util
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import textwrap
import time
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
spec = importlib.util.spec_from_file_location(
    "probe_checkout", ROOT / "src/cli/probe_checkout.py"
)
preparation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparation)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


@pytest.fixture
def source(tmp_path):
    repo = tmp_path / "source repository"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Artifact Fixture")
    git(repo, "config", "user.email", "fixture@example.test")
    source_file = repo / "module.py"
    revisions = {}
    for kind, value in (("buggy", 1), ("fixed", 2)):
        source_file.write_text(f"def advance():\n    return {value}\n")
        git(repo, "add", "module.py")
        git(repo, "-c", "commit.gpgsign=false", "commit", "-qm", kind)
        revisions[kind] = git(repo, "rev-parse", "HEAD")
    case = {
        "project": "pr-agent",
        "case_id": "pr-agent-fixture",
        "repository": str(repo),
        "revisions": revisions,
        "patch_targets": {
            "target_units": [
                {
                    "unit_id": "u1",
                    "filepath": "module.py",
                    "qualname": "advance",
                    "kind": "function",
                    "start_line": 1,
                    "end_line": 2,
                }
            ]
        },
    }
    case_path = tmp_path / "release" / case["case_id"] / "case.json"
    case_path.parent.mkdir(parents=True)
    case_path.write_text(json.dumps(case))
    return repo, case_path, case


def options(tmp_path, case_path):
    return [
        "--case-json",
        str(case_path),
        "--python-bin",
        sys.executable,
        "--out-root",
        str(tmp_path / "outputs"),
        "--run-id",
        "check",
        "--case-time-budget-seconds",
        "1800",
        "--strategy",
        "target_probe_contract_agnostic",
    ]


def value(arguments, flag):
    return arguments[arguments.index(flag) + 1]


def test_real_paired_fetch_preserves_case_and_cleans_checkouts(tmp_path, source):
    repo, case_path, case = source
    original = case_path.read_bytes()
    args = options(tmp_path, case_path)
    with preparation.prepare_probe(None, args, root=ROOT) as (
        project,
        forwarded,
    ):
        assert project == "pr-agent"
        assert forwarded[: len(args)] == args
        roots = {
            kind: Path(value(forwarded, f"--{kind}-root")) for kind in case["revisions"]
        }
        for kind, root in roots.items():
            assert git(root, "rev-parse", "HEAD") == case["revisions"][kind]
            assert git(root, "rev-list", "--count", "HEAD") == "1"
        assert "return 1" in (roots["buggy"] / "module.py").read_text()
        assert "return 2" in (roots["fixed"] / "module.py").read_text()
        assert git(repo, "status", "--porcelain") == ""
    assert all(not root.exists() for root in roots.values())
    assert case_path.read_bytes() == original
    record = json.loads(
        (tmp_path / "outputs/preparation/check/checkouts.json").read_text()
    )
    assert record["revisions"] == case["revisions"]
    assert (tmp_path / "outputs/preparation/check/prepare.log").is_file()


def test_case_id_lookup_and_project_inference(tmp_path, source, monkeypatch):
    _, case_path, case = source
    monkeypatch.setenv("BENCHMARK_RELEASE_ROOT", str(case_path.parent.parent))
    args = ["--case-id", case["case_id"], *options(tmp_path, case_path)[2:]]
    with preparation.prepare_probe(None, args, root=ROOT) as (
        project,
        forwarded,
    ):
        assert project == "pr-agent"
        assert value(forwarded, "--case-json") == str(case_path)
    assert (tmp_path / "outputs/preparation/check/checkouts.json").is_file()


def test_bundled_default_selects_formal_case_without_external_path(monkeypatch):
    monkeypatch.delenv("BENCHMARK_RELEASE_ROOT", raising=False)
    args = ["--case-id", "pr-agent-946c3e22", "--buggy-root=old", "--fixed-root=new"]
    with preparation.prepare_probe(None, args, root=ROOT) as (
        project,
        forwarded,
    ):
        assert project == "pr-agent"
        assert (
            Path(value(forwarded, "--case-json"))
            == ROOT / "resources/benchmark/cases/pr-agent/pr-agent-946c3e22.json"
        )


def test_latest_checkout_still_requires_user_environment(
    tmp_path, source, monkeypatch
):
    repo, _, case = source
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    from cli import benchmark_setup

    def unexpected(*args):
        pytest.fail("latest discovery must not select a historical environment")

    monkeypatch.setattr(benchmark_setup, "setup_profiles", unexpected)
    args = [
        "--repository",
        str(repo),
        "--revision",
        case["revisions"]["buggy"],
        "--target",
        "module.py",
    ]
    with pytest.raises(ValueError, match="--setup-script"):
        with preparation.prepare_probe("pr-agent", args, root=ROOT):
            pytest.fail("missing latest environment")


@pytest.mark.parametrize("failed_kind", [None, "buggy", "fixed"])
def test_benchmark_install_stages_inputs_and_cleans_all_temporary_state(
    tmp_path, source, monkeypatch, failed_kind
):
    repo, _, case = source
    monkeypatch.syspath_prepend(str(ROOT))
    from cli import benchmark_setup

    artifact = tmp_path / "artifact"
    (artifact / "resources").mkdir(parents=True)
    (artifact / "resources/projects.json").write_bytes((ROOT / "resources/projects.json").read_bytes())
    case_path = artifact / "resources/benchmark/cases/pr-agent/fixture.json"
    case_path.parent.mkdir(parents=True)
    case["dependencies"] = {}
    for kind, revision in case["revisions"].items():
        archive = artifact / f"resources/benchmark/dependencies/pr-agent/{kind}.zip"
        archive.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr(
                "module.py",
                subprocess.check_output(
                    ["git", "show", f"{revision}:module.py"], cwd=repo
                ),
            )
            z.writestr("resolved/requirements.lock", kind.encode())
        case["dependencies"][kind] = f"../../dependencies/pr-agent/{kind}.zip"
    case_path.write_text(json.dumps(case))
    (artifact / "resources/benchmark/setup.json").write_text(
        json.dumps(
            {
                "profiles": {"fixture": [["installer", "{dependencies}/resolved/requirements.lock"]]},
                "snapshots": {
                    f"pr-agent/{kind}.zip": "fixture" for kind in case["revisions"]
                },
            }
        )
    )
    roots, inputs = [], []
    original_install = benchmark_setup.install_environment

    def install(root, dependencies, recipe, language, log, env, run_step):
        roots.append(root)
        inputs.append(dependencies)
        assert not (root / "resolved").exists()

        def execute(command, *args):
            if command[0] == "installer":
                assert Path(command[1]) == dependencies.resolve() / "resolved/requirements.lock"
                assert Path(command[1]).read_text() == root.name
                (root / ".venv").mkdir()
                if root.name == failed_kind:
                    raise ValueError("installation failure")

        original_install(root, dependencies, recipe, language, log, env, execute)

    monkeypatch.setattr(benchmark_setup, "install_environment", install)
    args = [
        "--case-json",
        str(case_path),
        "--out-root",
        str(tmp_path / "output"),
        "--run-id",
        "failure",
    ]
    if failed_kind:
        with pytest.raises(ValueError, match="installation failure"):
            with preparation.prepare_probe(None, args, root=artifact):
                pytest.fail("workflow must not start after installation failure")
    else:
        with preparation.prepare_probe(None, args, root=artifact):
            assert all(path.exists() for path in [*roots, *inputs])
    assert len(roots) == (1 if failed_kind == "buggy" else 2)
    assert all(not path.exists() for path in [*roots, *inputs])
    assert (tmp_path / "output/preparation/failure/prepare.log").is_file()


@pytest.mark.parametrize("mismatch", [False, True])
def test_dependency_archives_match_before_core_execution(tmp_path, source, mismatch):
    repo, case_path, case = source
    case["dependencies"] = {}
    for kind, revision in case["revisions"].items():
        name = f"{kind}.zip"
        payload = subprocess.check_output(
            ["git", "show", f"{revision}:module.py"], cwd=repo
        )
        with zipfile.ZipFile(case_path.parent / name, "w") as archive:
            archive.writestr(
                "module.py", b"different" if mismatch and kind == "fixed" else payload
            )
            archive.writestr("resolved/requirements.lock", b"supplemental lock")
        case["dependencies"][kind] = name
    case_path.write_text(json.dumps(case))
    if mismatch:
        with pytest.raises(ValueError, match="dependency mismatch"):
            with preparation.prepare_probe(
                None, options(tmp_path, case_path), root=ROOT
            ):
                pytest.fail("mismatched dependency archive must stop before Probe")
    else:
        with preparation.prepare_probe(
            None, options(tmp_path, case_path), root=ROOT
        ) as (_, args):
            assert Path(value(args, "--fixed-root")).is_dir()
    log = (tmp_path / "outputs/preparation/check/prepare.log").read_text()
    assert "buggy.zip; 1 files matched" in log


@pytest.mark.parametrize("name", ["../outside", "/outside", "resolved/../../outside"])
def test_dependency_archive_paths_cannot_escape_checkout(tmp_path, name):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    outside = tmp_path / "outside"
    outside.write_bytes(b"same")
    archive_path = tmp_path / "dependencies.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(name, b"same")
    with (tmp_path / "log").open("w") as log:
        with pytest.raises(ValueError, match="invalid dependency path"):
            preparation.prepare_dependencies(checkout, archive_path, tmp_path / "inputs", log)


def test_dependency_archive_stages_resolved_files_without_changing_source(tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    manifest = checkout / "pyproject.toml"
    manifest.write_bytes(b"upstream manifest")
    original_lock = checkout / "requirements.lock"
    original_lock.write_bytes(b"upstream lock")
    directory = tmp_path / "inputs"
    archive_path = tmp_path / "dependencies.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("pyproject.toml", manifest.read_bytes())
        archive.writestr("requirements.lock", original_lock.read_bytes())
        archive.writestr("resolved/", b"")
        archive.writestr("resolved/requirements.lock", b"supplemental lock")
    with (tmp_path / "log").open("w") as log:
        preparation.prepare_dependencies(checkout, archive_path, directory, log)
    assert manifest.read_bytes() == b"upstream manifest"
    assert original_lock.read_bytes() == b"upstream lock"
    assert sorted(p.name for p in checkout.iterdir()) == ["pyproject.toml", "requirements.lock"]
    assert (directory / "resolved/requirements.lock").read_bytes() == b"supplemental lock"
    assert "2 files matched" in (tmp_path / "log").read_text()


@pytest.mark.parametrize("root_name", ["checkout", "inputs"])
def test_dependency_archive_rejects_symlink_escape(tmp_path, root_name):
    checkout, directory, outside = (tmp_path / name for name in ("checkout", "inputs", "outside"))
    for path in (checkout, directory, outside):
        path.mkdir()
    base = checkout if root_name == "checkout" else directory
    (base / "resolved" if root_name == "inputs" else base / "linked").symlink_to(outside)
    name = "resolved/requirements.lock" if root_name == "inputs" else "linked/requirements.txt"
    (outside / Path(name).name).write_bytes(b"original")
    archive_path = tmp_path / "dependencies.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(name, b"replacement")
    with (tmp_path / "log").open("w") as log:
        with pytest.raises(ValueError, match="invalid dependency path"):
            preparation.prepare_dependencies(checkout, archive_path, directory, log)
    assert (outside / Path(name).name).read_bytes() == b"original"


@pytest.mark.parametrize(
    "layout",
    [
        "cases/{case}/case.json",
        "cases/pr-agent/{case}.json",
        "pr-agent/benchmarkBR/cases/{case}/case.json",
    ],
)
def test_release_layouts_and_ambiguous_ids(tmp_path, layout):
    case_id = "pr-agent-fixture"
    path = tmp_path / layout.format(case=case_id)
    path.parent.mkdir(parents=True)
    path.write_text("{}")
    assert preparation.find_case(tmp_path, case_id) == path
    duplicate = tmp_path / case_id / "case.json"
    duplicate.parent.mkdir()
    duplicate.write_text("{}")
    with pytest.raises(ValueError, match="found 2"):
        preparation.find_case(tmp_path, case_id)
    with pytest.raises(ValueError, match="simple directory"):
        preparation.find_case(tmp_path, "../outside")


@pytest.mark.parametrize("project", ["pr-agent", "openclaw"])
def test_latest_files_setup_receives_revision_and_no_workflow_options(
    tmp_path, source, project
):
    repo, _, case = source
    script = tmp_path / "install dependencies.sh"
    script.write_text(
        'printf "%s\\n" "$PROBE_PROJECT" "$PROBE_REVISION_KIND" "$PROBE_REVISION" > setup_observation\n'
    )
    args = [
        "--repository",
        str(repo),
        "--revision",
        case["revisions"]["buggy"],
        "--target",
        "module.py",
        "--target",
        "module.py",
        "--setup-script",
        str(script),
        "--out-root",
        str(tmp_path / "out"),
        "--run-id",
        "latest",
    ]
    with preparation.prepare_probe(project, args, root=ROOT) as (
        _,
        forwarded,
    ):
        root = Path(value(forwarded, "--latest-root"))
        assert (root / "setup_observation").read_text().splitlines() == [
            project,
            "latest",
            case["revisions"]["buggy"],
        ]
        prepared = json.loads(Path(value(forwarded, "--case-json")).read_text())
        assert prepared["revisions"] == {"latest": case["revisions"]["buggy"]}
        assert prepared["target_units"] == [
            {
                "unit_id": "module.py::<module>@1-2:file",
                "filepath": "module.py",
                "qualname": "<module>",
                "kind": "file",
                "start_line": 1,
                "end_line": 2,
            }
        ]
        assert "--setup-script" not in forwarded and "--revision" not in forwarded
    assert not root.exists()
    assert (tmp_path / "out/preparation/latest/targets.json").exists()


def test_latest_target_json_preserves_selection(tmp_path, source):
    _, case_path, case = source
    case["target_units"] = case.pop("patch_targets")["target_units"]
    case["revisions"] = {"latest": case["revisions"]["buggy"]}
    case_path.write_text(json.dumps(case))
    with preparation.prepare_probe(
        None, options(tmp_path, case_path), root=ROOT
    ) as (_, args):
        assert value(args, "--case-json") == str(case_path)
        assert "--latest-root" in args and "--fixed-root" not in args
        assert json.loads(case_path.read_text()) == case


@pytest.mark.parametrize("script_body", ["exit 7\n", "printf 'changed' > module.py\n"])
def test_setup_failure_or_tracked_edit_never_launches_and_cleans(
    tmp_path, source, script_body
):
    _, case_path, _ = source
    script = tmp_path / "setup.sh"
    marker = tmp_path / "checkout_path"
    script.write_text(f"pwd > {shlex.quote(str(marker))}\n{script_body}")
    args = [*options(tmp_path, case_path), "--setup-script", str(script)]
    with pytest.raises(ValueError, match="preparation command exited"):
        with preparation.prepare_probe(None, args, root=ROOT):
            pytest.fail("failed preparation must not enter Probe")
    assert not Path(marker.read_text().strip()).exists()
    assert (tmp_path / "outputs/preparation/check/prepare.log").is_file()


def test_core_error_still_cleans_sources_and_keeps_evidence(tmp_path, source):
    _, case_path, _ = source
    root = None
    with pytest.raises(RuntimeError, match="core failure"):
        with preparation.prepare_probe(
            None, options(tmp_path, case_path), root=ROOT
        ) as (_, args):
            root = Path(value(args, "--buggy-root"))
            raise RuntimeError("core failure")
    assert root is not None and not root.exists()
    assert (tmp_path / "outputs/preparation/check/checkouts.json").is_file()


@pytest.mark.parametrize(
    "changes,extra,message",
    [
        ({"project": "openclaw"}, [], "does not match"),
        ({"revisions": {"buggy": "main", "fixed": "a" * 40}}, [], "full commit"),
        ({}, ["--revision", "a" * 40], "latest-revision"),
        ({"patch_targets": {"target_units": []}}, [], "no target"),
    ],
)
def test_invalid_inputs_fail_before_fetch(
    tmp_path, source, monkeypatch, changes, extra, message
):
    _, case_path, case = source
    case.update(changes)
    case_path.write_text(json.dumps(case))
    monkeypatch.setattr(
        preparation, "checkout", lambda *a: pytest.fail("unexpected checkout")
    )
    with pytest.raises(ValueError, match=message):
        with preparation.prepare_probe(
            "pr-agent",
            [*options(tmp_path, case_path), *extra],
            root=ROOT,
        ):
            pytest.fail("unexpected launch")
    assert not (tmp_path / "outputs").exists()


def test_manual_roots_validate_case_and_forward_without_preparing(tmp_path, monkeypatch):
    case_path = tmp_path / "case.json"
    case_path.write_text(json.dumps({"project": "pr-agent", "case_id": "fixture"}))
    monkeypatch.setattr(preparation, "checkout", lambda *a: pytest.fail("unexpected checkout"))
    args = [
        "--case-json",
        str(case_path),
        "--buggy-root=old",
        "--fixed-root=new",
        "--samples=2",
    ]
    with preparation.prepare_probe("pr-agent", args, root=ROOT) as (
        _,
        forwarded,
    ):
        assert forwarded == args
    with pytest.raises(ValueError, match="cannot be combined"):
        with preparation.prepare_probe(
            "pr-agent", [*args, "--setup-script=setup.sh"], root=ROOT
        ):
            pytest.fail("unexpected preparation")


@pytest.mark.parametrize("case_project", ["pr-agent", "openclaw"])
@pytest.mark.parametrize("selection", ["infer", "match", "conflict"])
@pytest.mark.parametrize("roots", [
    ["--buggy-root=old", "--fixed-root=new"],
    ["--latest-root=latest"],
])
def test_prepared_case_project_is_inferred_or_rejected(
    tmp_path, monkeypatch, case_project, selection, roots
):
    from cli import benchmark_setup

    case = tmp_path / "case.json"
    case.write_text(json.dumps({"project": case_project, "case_id": "fixture"}))

    def unexpected(*args, **kwargs):
        pytest.fail("prepared roots must not trigger preparation")

    monkeypatch.setattr(preparation, "checkout", unexpected)
    monkeypatch.setattr(preparation, "run_step", unexpected)
    monkeypatch.setattr(benchmark_setup, "install_environment", unexpected)
    monkeypatch.setattr(Path, "mkdir", unexpected)
    project = {"infer": None, "match": case_project, "conflict": "aider"}[selection]
    args = ["--case-json", str(case), *roots]
    if selection == "conflict":
        with pytest.raises(ValueError, match="--project does not match"):
            with preparation.prepare_probe(project, args, root=ROOT):
                pytest.fail("conflicting project must not reach the workflow")
    else:
        with preparation.prepare_probe(project, args, root=ROOT) as (inferred, forwarded):
            assert inferred == case_project
            assert forwarded == args


@pytest.mark.parametrize("project,case_id", [
    ("pr-agent", "pr-agent-946c3e22"),
    ("openclaw", "openclaw-2467a103"),
])
@pytest.mark.parametrize("invalid", [
    ["--modle", "gpt-5-mini"],
    ["--model-timeou=1"],
    ["--model"],
    ["--samples", "invalid"],
    ["--samples=-1"],
    ["--assets-per-sample=0"],
    ["--timeout=0"],
    ["--model-timeout=0"],
    ["--model-retries=-1"],
    ["--case-time-budget-seconds=nan"],
    ["--case-time-budget-seconds=-1"],
    ["--strategy=invalid"],
    ["--provider=invalid"],
    ["--confirmations=0"],
    ["--run-id=../escape"],
])
@pytest.mark.parametrize("latest", [False, True])
def test_invalid_workflow_options_have_no_preparation_side_effects(
    tmp_path, monkeypatch, project, case_id, invalid, latest
):
    from cli import benchmark_setup

    def unexpected(*args, **kwargs):
        pytest.fail("invalid workflow options must fail before preparation")

    monkeypatch.setattr(preparation, "checkout", unexpected)
    monkeypatch.setattr(preparation, "run_step", unexpected)
    monkeypatch.setattr(benchmark_setup, "install_environment", unexpected)
    monkeypatch.setattr(Path, "mkdir", unexpected)
    selection = (
        ["--repository", "https://example.invalid/repo.git", "--revision", "a" * 40,
         "--target", "source.py"]
        if latest else ["--case-id", case_id]
    )
    args = [*selection, "--out-root", str(tmp_path / "out"), *invalid]
    with pytest.raises((SystemExit, ValueError)):
        with preparation.prepare_probe(project, args, root=ROOT):
            pytest.fail("invalid options must not reach the workflow")
    assert not (tmp_path / "out").exists()


def test_prepared_typescript_native_numeric_options_are_preserved(tmp_path, monkeypatch):
    case = tmp_path / "case.json"
    case.write_text(json.dumps({"project": "openclaw", "case_id": "fixture"}))
    monkeypatch.setattr(preparation, "checkout", lambda *a: pytest.fail("unexpected checkout"))
    args = ["--case-json", str(case), "--buggy-root=old", "--fixed-root=new",
            "--timeout=0.5", "--samples=1.0", "--confirmations=1"]
    with preparation.prepare_probe(None, args, root=ROOT) as (project, forwarded):
        assert project == "openclaw"
        assert forwarded == args


@pytest.mark.parametrize("project", ["pr-agent", "openclaw"])
def test_invalid_numeric_options_precede_reading_missing_case(tmp_path, project):
    with pytest.raises(ValueError, match="samples"):
        with preparation.prepare_probe(
            project,
            ["--case-json", str(tmp_path / "missing.json"),
             "--buggy-root=old", "--fixed-root=new", "--samples=-1"],
            root=ROOT,
        ):
            pytest.fail("invalid options must not reach the workflow")
    assert not list(tmp_path.iterdir())


def test_missing_environment_is_explicit(tmp_path, source):
    _, case_path, _ = source
    with pytest.raises(ValueError, match="--setup-script or an existing Python"):
        with preparation.prepare_probe(
            None, ["--case-json", str(case_path)], root=ROOT
        ):
            pytest.fail("unexpected launch")


def test_file_targets_reject_escape_and_empty_sources(tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (tmp_path / "outside.py").write_text("pass\n")
    (checkout / "escape.py").symlink_to(tmp_path / "outside.py")
    for target in ["../outside.py", str(tmp_path / "outside.py"), "escape.py"]:
        with pytest.raises(ValueError, match="checkout-relative"):
            preparation.file_targets(checkout, [target])
    (checkout / "empty.py").touch()
    with pytest.raises(ValueError, match="empty"):
        preparation.file_targets(checkout, ["empty.py"])


def test_launcher_prepares_case_before_dispatch_and_cleans_after(tmp_path, source, monkeypatch):
    from types import SimpleNamespace

    launcher_spec = importlib.util.spec_from_file_location("launcher", ROOT / "run.py")
    launcher = importlib.util.module_from_spec(launcher_spec)
    launcher_spec.loader.exec_module(launcher)
    _, case_path, case = source
    run = subprocess.run
    roots = []

    def execute(command, **kwargs):
        if len(command) > 1 and command[1] == str(ROOT / "src/cli/runner.py"):
            assert value(command, "--project") == "pr-agent"
            assert value(command, "--case-json") == str(case_path)
            for kind in ("buggy", "fixed"):
                path = Path(value(command, f"--{kind}-root"))
                roots.append(path)
                assert git(path, "rev-parse", "HEAD") == case["revisions"][kind]
            return SimpleNamespace(returncode=0)
        return run(command, **kwargs)

    monkeypatch.setattr(launcher.subprocess, "run", execute)
    result = launcher.main(
        [
            "probe",
            "--case-id",
            case["case_id"],
            "--cases-root",
            str(case_path.parent.parent),
            "--python-bin",
            sys.executable,
            "--out-root",
            str(tmp_path / "output"),
        ],
    )
    assert result == 0
    assert len(roots) == 2 and all(not root.exists() for root in roots)
    assert list((tmp_path / "output/preparation").glob("*/checkouts.json"))


def test_missing_commit_stops_without_falling_back_and_cleans(
    tmp_path, source, monkeypatch
):
    _, case_path, case = source
    case["revisions"]["buggy"] = "f" * 40
    case_path.write_text(json.dumps(case))
    original = preparation.checkout
    destinations = []

    def observe(repository, revision, destination, log, env):
        destinations.append(destination)
        original(repository, revision, destination, log, env)

    monkeypatch.setattr(preparation, "checkout", observe)
    with pytest.raises(ValueError, match="preparation command exited"):
        with preparation.prepare_probe(
            None, options(tmp_path, case_path), root=ROOT
        ):
            pytest.fail("missing commits must not reach Probe")
    assert destinations and all(not path.exists() for path in destinations)
    log = (tmp_path / "outputs/preparation/check/prepare.log").read_text()
    assert "f" * 40 in log


def test_existing_latest_coordinates_cannot_be_relabelled(tmp_path, source):
    _, case_path, case = source
    revision = case["revisions"]["fixed"]
    case["target_units"] = case.pop("patch_targets")["target_units"]
    case["revisions"] = {"latest": None}
    case_path.write_text(json.dumps(case))
    with pytest.raises(ValueError, match="conflicts"):
        with preparation.prepare_probe(
            None,
            [*options(tmp_path, case_path), "--revision", revision],
            root=ROOT,
        ):
            pytest.fail("target coordinates must retain their recorded revision")
    assert not (tmp_path / "outputs").exists()


def test_preparation_timeout_stops_child_processes(tmp_path):
    marker = tmp_path / "late_write"
    child = f"import time; from pathlib import Path; time.sleep(1); Path({str(marker)!r}).touch()"
    parent = (
        "import subprocess, time; "
        f"subprocess.Popen([{sys.executable!r}, '-c', {child!r}]); time.sleep(30)"
    )
    with (tmp_path / "prepare.log").open("w") as log:
        with pytest.raises(subprocess.TimeoutExpired):
            preparation.run_step([sys.executable, "-c", parent], tmp_path, log, {}, 0.1)
    time.sleep(1.1)
    assert not marker.exists()


@pytest.mark.parametrize("body,timeout,error", [
    ("pass", 10, None),
    ("raise SystemExit(7)", 10, ValueError),
    ("import time; time.sleep(30)", 0.1, subprocess.TimeoutExpired),
])
def test_preparation_restores_sigterm_handler(tmp_path, body, timeout, error):
    previous = signal.getsignal(signal.SIGTERM)
    with (tmp_path / "prepare.log").open("w") as log:
        if error:
            with pytest.raises(error):
                preparation.run_step([sys.executable, "-c", body], tmp_path, log, {}, timeout)
        else:
            preparation.run_step([sys.executable, "-c", body], tmp_path, log, {}, timeout)
    assert signal.getsignal(signal.SIGTERM) is previous


@pytest.mark.skipif(os.name != "posix", reason="preparation uses POSIX process groups")
@pytest.mark.parametrize("stubborn", [False, True])
def test_preparation_sigterm_cleans_and_reaps_owned_processes(tmp_path, stubborn):
    command = textwrap.dedent(f"""
        import json, os, signal, subprocess, sys, time
        from pathlib import Path

        def stop(signum, frame):
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, signal.SIG_IGN if {stubborn!r} else stop)
        child = None if {stubborn!r} else subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        try:
            Path('pids.tmp').write_text(json.dumps([os.getpid(), *([child.pid] if child else [])]))
            Path('pids.tmp').replace('pids.json')
            time.sleep(60)
        finally:
            if child:
                child.terminate()
                child.wait(timeout=5)
                Path('child_reaped').touch()
    """)
    worker = textwrap.dedent(f"""
        import os, signal, sys
        from pathlib import Path
        sys.path.insert(0, {str(ROOT / 'src')!r})
        from cli.probe_checkout import run_step

        def previous(signum, frame):
            # A regression must unwind and reap too, rather than orphan the fixture.
            raise RuntimeError('previous SIGTERM handler was called')

        signal.signal(signal.SIGTERM, previous)
        try:
            with Path('prepare.log').open('w') as log:
                run_step([sys.executable, '-c', {command!r}], Path.cwd(), log, dict(os.environ), 30)
        finally:
            assert signal.getsignal(signal.SIGTERM) is previous
            Path('handler_restored').touch()
    """)
    with subprocess.Popen(
        [sys.executable, "-c", worker], cwd=tmp_path, start_new_session=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    ) as process:
        try:
            ready = tmp_path / "pids.json"
            deadline = time.monotonic() + 10
            while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            assert ready.exists(), "preparation command did not start"
            pids = json.loads(ready.read_text())
            assert os.getpgid(pids[0]) == pids[0]
            assert os.getpgid(process.pid) != pids[0]
            process.send_signal(signal.SIGTERM)
            output, _ = process.communicate(timeout=15)
            assert process.returncode == 128 + signal.SIGTERM, output
            assert (tmp_path / "handler_restored").exists()
            if not stubborn:
                assert (tmp_path / "child_reaped").exists()
            for pid in pids:
                with pytest.raises(ProcessLookupError):
                    os.kill(pid, 0)
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                process.communicate(timeout=15)
