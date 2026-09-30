"""Execute the standalone collector against passing and failing pytest suites."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

COLLECTOR = Path(__file__).resolve().parents[1] / "python.py"


def collect(tmp_path, test, timeout=30, coverage_config=None):
    root = tmp_path / "project"
    (root / "pkg").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "pkg/__init__.py").write_text("")
    (root / "pkg/agent.py").write_text(
        "def choose(value):\n    if value:\n        return 'yes'\n    return 'no'\n"
    )
    (root / "pkg/unreached.py").write_text("def untouched():\n    return 42\n")
    (root / "tests/test_agent.py").write_text(test)
    if coverage_config:
        (root / ".coveragerc").write_text(coverage_config)
    scope = tmp_path / "source_files.json"
    scope.write_text(json.dumps({"files": ["pkg/agent.py", "pkg/unreached.py"]}))
    output = tmp_path / "output"
    result = subprocess.run(
        [sys.executable, str(COLLECTOR), "--project-root", str(root),
         "--source-files", str(scope), "--out-dir", str(output),
         "--timeout", str(timeout), "--", "tests", "-q"],
        env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        capture_output=True, text=True, timeout=timeout + 15,
    )
    return root, output, result


@pytest.mark.parametrize("expected,status", [("yes", "passed"), ("wrong", "failed")])
def test_test_failure_retains_measured_coverage(tmp_path, expected, status):
    root, output, result = collect(tmp_path, f"from pkg.agent import choose\ndef test_value():\n    assert choose(True) == '{expected}'\n")
    assert result.returncode == 0, result.stdout + result.stderr
    record = json.loads((output / "run.json").read_text())
    assert record["status"] == status
    assert record["coverage_available"] is True
    coverage = json.loads((output / "coverage.json").read_text())["files"]
    assert coverage["pkg/agent.py"]["executed_lines"] == [1, 2, 3]
    assert coverage["pkg/agent.py"]["missing_lines"] == [4]
    assert coverage["pkg/agent.py"]["executed_branches"] == [[2, 3]]
    assert coverage["pkg/agent.py"]["missing_branches"] == [[2, 4]]
    assert coverage["pkg/unreached.py"]["executed_lines"] == []
    assert coverage["pkg/unreached.py"]["missing_lines"] == [1, 2]
    assert not (root / ".coverage").exists()
    assert (output / "raw/.coverage").exists()


def test_crash_without_saved_coverage_is_not_zero_coverage(tmp_path):
    _, output, result = collect(tmp_path, "import os\ndef test_crash():\n    os._exit(4)\n")
    assert result.returncode == 1
    record = json.loads((output / "run.json").read_text())
    assert record["status"] == "failed"
    assert record["coverage_available"] is False
    assert not (output / "coverage.json").exists()


def test_native_exclusion_rules_and_explicit_source_scope(tmp_path):
    _, output, result = collect(tmp_path,
        "from pkg.agent import choose\ndef test_value():\n    assert choose(True) == 'yes'\n",
        coverage_config="[run]\nsource_dirs = tests\nrelative_files = true\n[report]\nexclude_lines =\n    return 42\n")
    assert result.returncode == 0, result.stdout + result.stderr
    files = json.loads((output / "coverage.json").read_text())["files"]
    assert set(files) == {"pkg/agent.py", "pkg/unreached.py"}
    assert files["pkg/agent.py"]["executed_lines"] == [1, 2, 3]
    assert files["pkg/unreached.py"]["missing_lines"] == [1]


@pytest.mark.skipif(os.name != "posix", reason="coverage.py SIGTERM saving is POSIX-only")
def test_timeout_records_status_and_preserves_flushed_coverage(tmp_path):
    _, output, result = collect(tmp_path,
        "from pkg.agent import choose\nimport time\ndef test_wait():\n    choose(True)\n    time.sleep(60)\n", timeout=2)
    assert result.returncode == 0, result.stdout + result.stderr
    record = json.loads((output / "run.json").read_text())
    assert record["status"] == "timeout"
    assert record["coverage_available"] is True
    assert 3 in json.loads((output / "coverage.json").read_text())["files"]["pkg/agent.py"]["executed_lines"]
