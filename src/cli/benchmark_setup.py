"""Install the recorded dependencies of a bundled historical revision."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import tempfile


def node_version(root: Path) -> str | None:
    """Read an exact Node pin; engine ranges are checked during installation."""
    for name in (".nvmrc", ".node-version"):
        path = root / name
        if path.is_file():
            version = path.read_text().strip().removeprefix("v")
            if not re.fullmatch(r"\d+\.\d+\.\d+", version):
                raise ValueError(f"{name} must pin an exact Node version: {version}")
            return version
    manifest = json.loads((root / "package.json").read_text())
    version = manifest.get("engines", {}).get("node", "").removeprefix("v")
    return version if re.fullmatch(r"\d+\.\d+\.\d+", version) else None


def prepare_node(root: Path, log, env: dict[str, str], run_step) -> Path:
    """Resolve the revision's Node executable without changing global settings."""
    version = node_version(root)
    with tempfile.TemporaryDirectory(prefix="probe_node_") as temporary:
        directory = Path(temporary)
        (directory / "package.json").write_text("{}\n")
        executable = directory / "node_path"
        command = ["node"]
        if version:
            command = [
                "pnpm",
                "--config.manage-package-manager-versions=false",
                f"--config.use-node-version={version}",
                "node",
            ]
        run_step(
            [
                *command,
                "-e",
                "require('node:fs').writeFileSync(process.argv[1], process.execPath); "
                "console.log('Node runtime:', process.version, process.execPath)",
                str(executable),
            ],
            directory, log, env, 1800,
        )
        return Path(executable.read_text()).resolve(strict=True)


def setup_profiles(benchmark: Path, case_path: Path, case: dict) -> dict:
    """Select both revision recipes by their archived dependency inputs."""
    if not case_path.resolve().is_relative_to((benchmark / "cases").resolve()):
        raise ValueError(
            "automatic environment setup requires a bundled benchmark case; "
            "provide --setup-script or an existing Python --python-bin for external cases"
        )
    settings = json.loads((benchmark / "setup.json").read_text())
    selected = {}
    for kind in ("buggy", "fixed"):
        dependency = case.get("dependencies", {}).get(kind)
        if not isinstance(dependency, str):
            raise ValueError(f"missing {kind} benchmark dependency archive")
        archive = (case_path.parent / dependency).resolve()
        name = archive.relative_to((benchmark / "dependencies").resolve()).as_posix()
        profile = settings["snapshots"].get(name)
        if profile is None:
            raise ValueError(
                f"no recorded setup for {name}; provide --python-bin or --setup-script"
            )
        commands = settings["profiles"][profile]
        if not commands or any(
            not isinstance(command, list)
            or not command
            or any(not isinstance(arg, str) or not arg for arg in command)
            for command in commands
        ):
            raise ValueError(f"invalid installation commands in profile {profile}")
        selected[kind] = {"profile": profile, "commands": commands}
    return selected


def install_environment(
    root: Path,
    dependencies: Path,
    recipe: dict,
    language: str,
    log,
    env: dict[str, str],
    run_step,
) -> None:
    """Install into the temporary checkout and record its resulting packages."""
    setup_env = {
        key: value
        for key, value in env.items()
        if key
        not in {"VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH", "UV_PROJECT_ENVIRONMENT"}
    }
    setup_env.update(HUSKY="0", SKIP_INSTALL_SIMPLE_GIT_HOOKS="1")
    new_locks = [
        root / name
        for name in ("pnpm-lock.yaml", "poetry.lock", "uv.lock", "Pipfile.lock")
        if not (root / name).exists()
    ]
    if language == "python":
        setup_env.update(
            VIRTUAL_ENV=str(root / ".venv"),
            UV_PROJECT_ENVIRONMENT=str(root / ".venv"),
            POETRY_VIRTUALENVS_IN_PROJECT="true",
            PATH=str(root / ".venv/bin") + os.pathsep + env.get("PATH", ""),
        )
    else:
        node = prepare_node(root, log, setup_env, run_step)
        setup_env["PATH"] = str(node.parent) + os.pathsep + setup_env.get("PATH", "")
    log.write(f"Environment profile: {recipe['profile']}\n")
    log.flush()
    for command in recipe["commands"]:
        expanded = [
            arg.replace("{dependencies}", str(dependencies.resolve())) for arg in command
        ]
        run_step(expanded, root, log, setup_env, 1800)
    if language == "python":
        inspection = [
            str(root / ".venv/bin/python"),
            "-c",
            "import importlib.metadata as m,json,platform,pytest; "
            "print(json.dumps({'python':platform.python_version(),"
            "'packages':sorted((d.metadata['Name'],d.version) for d in m.distributions())}))",
        ]
    else:
        # Isolated validation links node_modules, retaining this runtime too.
        local_node = root / "node_modules/.bin/node"
        local_node.parent.mkdir(parents=True, exist_ok=True)
        local_node.unlink(missing_ok=True)
        local_node.symlink_to(node)
        inspection = ["pnpm", "list", "--depth", "0", "--json"]
    run_step(inspection, root, log, setup_env, 60)
    for lock in new_locks:
        if lock.is_file():
            destination = Path(log.name).parent / root.name / lock.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(lock, destination)
