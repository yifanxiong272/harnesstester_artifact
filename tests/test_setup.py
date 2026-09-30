"""Paper setup uses one Python default and preserves dependency versions."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("project", [
    "aider", "browser-use", "gpt-researcher", "openhands",
    "pr-agent", "rd-agent", "swe-agent",
])
@pytest.mark.parametrize("override", [False, True])
def test_setup_interpreter_and_install_commands(tmp_path, project, override):
    root = tmp_path / "artifact"
    (root / "src/cli").mkdir(parents=True)
    (root / "resources/subjects" / project).mkdir(parents=True)
    shutil.copy2(ROOT / "src/cli/setup.sh", root / "src/cli/setup.sh")
    commands = tmp_path / "commands.jsonl"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    recorder = (
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "with Path(os.environ['COMMAND_LOG']).open('a') as log:\n"
        "    log.write(json.dumps(sys.argv) + '\\n')\n"
    )
    uv = bin_dir / "uv"
    uv.write_text(
        recorder
        + "python = Path(sys.argv[-1]) / 'bin/python'\n"
        + "python.parent.mkdir(parents=True, exist_ok=True)\n"
        + f"python.write_text({recorder!r})\n"
        + "python.chmod(0o755)\n"
    )
    uv.chmod(0o755)
    env = {key: value for key, value in os.environ.items() if key != "PYTHON"}
    env.update(PATH=str(bin_dir) + os.pathsep + env["PATH"], COMMAND_LOG=str(commands))
    if override:
        env["PYTHON"] = sys.executable
    result = subprocess.run(
        ["bash", str(root / "src/cli/setup.sh"), project],
        env=env, text=True, capture_output=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in commands.read_text().splitlines()]
    assert calls[0][1:] == [
        "venv", "--no-project", "--seed", "--allow-existing", "--python",
        sys.executable if override else "3.12.13", str(root / ".venvs" / project),
    ]
    assert calls[1][1:] == [
        "-m", "pip", "install", "--disable-pip-version-check", "--no-deps",
        "-r", str(root / "resources/inputs" / project / "requirements.txt"),
    ]
    assert calls[2][1:] == [
        "-m", "pip", "install", "--disable-pip-version-check", "--no-deps",
        "-e", str(root / "resources/subjects" / project),
    ]
    assert calls[3][1:] == ["-c", 'import pytest, coverage; print("Test environment ready")']


@pytest.mark.parametrize("name", ["audioop-lts", "pyyaml-ft"])
def test_openhands_python_specific_dependencies(name):
    requirements = [
        Requirement(line) for line in
        (ROOT / "resources/inputs/openhands/requirements.txt").read_text().splitlines()
        if line and not line.startswith("#")
    ]
    marker = next(item.marker for item in requirements if item.name == name)
    assert marker is not None
    assert not marker.evaluate({"python_version": "3.12"})
    assert marker.evaluate({"python_version": "3.13"})


@pytest.mark.parametrize("system,machine", [
    ("Linux", "x86_64"), ("Linux", "aarch64"), ("Darwin", "arm64"),
    ("Windows", "AMD64"),
])
def test_aider_platform_specific_dependencies(system, machine):
    requirements = [
        Requirement(line) for line in
        (ROOT / "resources/inputs/aider/requirements.txt").read_text().splitlines()
        if line and not line.startswith("#")
    ]
    accelerator = [item for item in requirements
                   if item.name.startswith(("cuda-", "nvidia-")) or item.name == "triton"]
    assert accelerator
    for item in accelerator:
        assert item.marker is not None
        assert item.marker.evaluate({"platform_system": system, "platform_machine": machine}) == (
            system == "Linux" and machine == "x86_64"
        )
    watchdog = next(item for item in requirements if item.name == "watchdog")
    assert watchdog.marker is not None
    assert not watchdog.marker.evaluate({"sys_platform": "darwin"})
    assert watchdog.marker.evaluate({"sys_platform": "linux"})
