"""Recorded setup belongs to historical benchmark preparation, not generation."""

import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import sysconfig
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
spec = importlib.util.spec_from_file_location(
    "benchmark_setup", ROOT / "src/cli/benchmark_setup.py"
)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


def test_every_bundled_revision_has_a_recorded_recipe():
    benchmark = ROOT / "resources/benchmark"
    settings = json.loads((benchmark / "setup.json").read_text())
    used = set()
    cases = list((benchmark / "cases").glob("*/*.json"))
    assert len(cases) == 250
    for path in cases:
        case = json.loads(path.read_text())
        recipes = setup.setup_profiles(benchmark, path, case)
        assert set(recipes) == {"buggy", "fixed"}
        for kind, recipe in recipes.items():
            archive = (path.parent / case["dependencies"][kind]).resolve()
            used.add(archive)
            with zipfile.ZipFile(archive) as z:
                commands = recipe["commands"]
                if recipe["profile"].startswith("pnpm_"):
                    assert ("--frozen-lockfile" in commands[0]) == (
                        "pnpm-lock.yaml" in z.namelist()
                    )
                for command in commands:
                    for index, arg in enumerate(command):
                        if arg == "-r":
                            assert command[index + 1] in z.namelist()
                        if arg.startswith("{dependencies}/"):
                            assert arg.removeprefix("{dependencies}/") in z.namelist()
                            if arg.endswith("/requirements.lock"):
                                assert "--require-hashes" in command
                                assert commands[0][:2] == ["uv", "venv"]
                    assert all("/Users/" not in arg for arg in command)
    assert used == {p.resolve() for p in (benchmark / "dependencies").glob("*/*.zip")}
    assert set(settings["snapshots"]) == {
        p.relative_to((benchmark / "dependencies").resolve()).as_posix() for p in used
    }
    assert set(settings["profiles"]) == set(settings["snapshots"].values())


def test_external_case_cannot_enable_bundled_setup(tmp_path):
    with pytest.raises(ValueError, match="bundled benchmark case"):
        setup.setup_profiles(ROOT / "resources/benchmark", tmp_path / "case.json", {})


def test_unconfigured_archive_fails_before_installation(tmp_path):
    (tmp_path / "cases/project").mkdir(parents=True)
    (tmp_path / "setup.json").write_text(json.dumps({"profiles": {}, "snapshots": {}}))
    case = {"dependencies": {"buggy": "../../dependencies/project/input.zip"}}
    with pytest.raises(ValueError, match="no recorded setup"):
        setup.setup_profiles(tmp_path, tmp_path / "cases/project/case.json", case)


@pytest.mark.parametrize("language", ["python", "typescript"])
def test_installer_uses_recorded_commands_and_isolated_environment(tmp_path, language, monkeypatch):
    commands = []
    inherited = {
        **os.environ,
        "PYTHONPATH": "external",
        "VIRTUAL_ENV": "external",
        "UV_PROJECT_ENVIRONMENT": "external",
    }
    original = dict(inherited)
    recipe = {
        "profile": "fixture",
        "commands": [["tool", "{dependencies}/input with spaces", "literal;$HOME"]],
    }
    node = Path(shutil.which("node")).resolve()
    monkeypatch.setattr(setup, "prepare_node", lambda *args: node)
    prior_node = tmp_path / "dependency_node"
    if language == "typescript":
        prior_node.write_text("dependency-supplied executable")
        bin_dir = tmp_path / "node_modules/.bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "node").symlink_to(prior_node)

    def run(command, cwd, log, env, timeout):
        commands.append(command)
        assert cwd == tmp_path and timeout in (60, 1800)
        assert "PYTHONPATH" not in env
        if language == "python":
            assert env["VIRTUAL_ENV"] == str(tmp_path / ".venv")
            assert env["PATH"].split(os.pathsep)[0] == str(tmp_path / ".venv/bin")
        else:
            assert "VIRTUAL_ENV" not in env
            assert env["PATH"].split(os.pathsep)[0] == str(node.parent)

    log = io.StringIO()
    setup.install_environment(
        tmp_path, ROOT / "resources/benchmark", recipe, language, log, inherited, run
    )
    assert commands[0] == [
        "tool",
        str(ROOT / "resources/benchmark/input with spaces"),
        "literal;$HOME",
    ]
    assert len(commands) == 2
    assert inherited == original
    assert "fixture" in log.getvalue()
    if language == "typescript":
        assert (tmp_path / "node_modules/.bin/node").resolve() == node
        assert (tmp_path / "node_modules/.bin/node").is_symlink()
        assert prior_node.read_text() == "dependency-supplied executable"


def test_installer_stops_at_first_failure(tmp_path):
    called = []

    def fail(command, *args):
        called.append(command)
        raise ValueError("install failed")

    recipe = {"profile": "fixture", "commands": [["first"], ["second"]]}
    with pytest.raises(ValueError, match="install failed"):
        setup.install_environment(
            tmp_path, ROOT / "resources/benchmark", recipe, "python", io.StringIO(), {}, fail
        )
    assert called == [["first"]]


def test_installer_preserves_new_lock_without_copying_existing_ones(tmp_path, monkeypatch):
    root = tmp_path / "buggy"
    root.mkdir()
    (root / "poetry.lock").write_text("upstream lock")
    records = tmp_path / "records"
    records.mkdir()
    monkeypatch.setattr(setup, "prepare_node", lambda *args: Path(shutil.which("node")))

    def install(command, *args):
        (root / "pnpm-lock.yaml").write_text("resolved dependencies")

    recipe = {"profile": "fixture", "commands": [["installer"]]}
    with (records / "prepare.log").open("w") as log:
        setup.install_environment(
            root, ROOT / "resources/benchmark", recipe, "typescript", log, {}, install
        )
    assert (records / "buggy/pnpm-lock.yaml").read_text() == "resolved dependencies"
    assert not (records / "buggy/poetry.lock").exists()


@pytest.mark.parametrize(
    "pin_file,pin,engine,expected",
    [
        (".nvmrc", "v20.19.2\n", ">=20", "20.19.2"),
        (".node-version", "24.15.0", ">=22", "24.15.0"),
        (None, None, "20.18.1", "20.18.1"),
        (None, None, ">=22.12.0", None),
        (None, None, "^20 || >=24", None),
    ],
)
def test_node_selection_uses_revision_metadata(tmp_path, pin_file, pin, engine, expected):
    (tmp_path / "package.json").write_text(json.dumps({"engines": {"node": engine}}))
    if pin_file:
        (tmp_path / pin_file).write_text(pin)
    assert setup.node_version(tmp_path) == expected


def test_non_exact_node_pin_fails_before_installing(tmp_path):
    (tmp_path / ".nvmrc").write_text("lts/*")
    with pytest.raises(ValueError, match="exact Node version"):
        setup.node_version(tmp_path)


@pytest.mark.parametrize("version", [None, "20.19.2"])
def test_node_preparation_is_private_and_preserves_source(tmp_path, version):
    manifest = tmp_path / "package.json"
    manifest.write_text(json.dumps({"engines": {"node": version or ">=20"}}))
    original = manifest.read_bytes()
    executable = Path(shutil.which("node")).resolve()
    calls = []
    env = {"PATH": "fixture"}

    def run(command, cwd, log, received_env, timeout):
        assert received_env is env and timeout == 1800
        assert cwd != tmp_path and json.loads((cwd / "package.json").read_text()) == {}
        Path(command[-1]).write_text(str(executable))
        calls.append((command, cwd))

    assert setup.prepare_node(tmp_path, io.StringIO(), env, run) == executable
    command, cwd = calls[0]
    if version:
        assert command[:4] == [
            "pnpm", "--config.manage-package-manager-versions=false",
            f"--config.use-node-version={version}", "node",
        ]
    else:
        assert command[0] == "node"
    assert not cwd.exists()
    assert manifest.read_bytes() == original
    assert list(tmp_path.iterdir()) == [manifest]


def test_all_bundled_ts_pins_match_their_engines(tmp_path):
    pins = set()
    for project in ("roo-code", "kimi-code", "openclaw"):
        for archive in (ROOT / "resources/benchmark/dependencies" / project).glob("*.zip"):
            with zipfile.ZipFile(archive) as z:
                root = tmp_path / archive.stem
                root.mkdir(exist_ok=True)
                for name in ("package.json", ".nvmrc", ".node-version"):
                    if name in z.namelist():
                        (root / name).write_bytes(z.read(name))
                pin = setup.node_version(root)
                pins.add(pin)
                engine = json.loads((root / "package.json").read_text())["engines"]["node"]
                assert engine == pin or engine.startswith(">=")
    assert pins == {None, "20.18.1", "20.19.2", "24.15.0"}


def test_real_python_environment_installs_local_dependency(tmp_path):
    checkout_spec = importlib.util.spec_from_file_location(
        "checkout", ROOT / "src/cli/probe_checkout.py"
    )
    checkout = importlib.util.module_from_spec(checkout_spec)
    checkout_spec.loader.exec_module(checkout)
    wheel = tmp_path / "fixture_dependency-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("fixture_dependency.py", "VALUE = 42\n")
        archive.writestr(
            "fixture_dependency-1.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: fixture-dependency\nVersion: 1.0\n",
        )
        archive.writestr(
            "fixture_dependency-1.0.dist-info/WHEEL",
            "Wheel-Version: 1.0\nGenerator: fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        archive.writestr("fixture_dependency-1.0.dist-info/RECORD", "")
    recipe = {
        "profile": "offline_fixture",
        "commands": [
            [sys.executable, "-m", "venv", "--system-site-packages", ".venv"],
            [
                ".venv/bin/python",
                "-c",
                "from pathlib import Path; import site; "
                "Path(site.getsitepackages()[0], 'fixture.pth').write_text("
                + repr(sysconfig.get_path("purelib") + "\n")
                + ")",
            ],
            [".venv/bin/python", "-m", "pip", "install", "--no-index", str(wheel)],
            [
                ".venv/bin/python",
                "-c",
                "import fixture_dependency; assert fixture_dependency.VALUE == 42",
            ],
        ],
    }
    with (tmp_path / "prepare.log").open("w") as log:
        setup.install_environment(
            tmp_path,
            ROOT / "resources/benchmark",
            recipe,
            "python",
            log,
            dict(os.environ),
            checkout.run_step,
        )
    assert (tmp_path / ".venv/bin/python").is_file()
    assert '"fixture-dependency", "1.0"' in (tmp_path / "prepare.log").read_text()
