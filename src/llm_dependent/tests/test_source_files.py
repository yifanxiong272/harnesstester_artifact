"""An explicit scope includes exactly its listed Python files."""

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from llm_dependent.python.flow import analyze_flow_project_outputs
from llm_dependent.python.runner import load_source_files


def manifest(root, payload):
    path = root / "source_files.json"
    path.write_text(json.dumps(payload))
    return path


@pytest.mark.parametrize("shape", ["files", "locations"])
def test_explicit_scope_preserves_cross_file_flow_without_name_filters(tmp_path, shape):
    sources = {
        "agent.py": (
            "from vendor.test_provider import request\n"
            "def run():\n    response = request()\n    return response.text\n"
        ),
        "vendor/test_provider.py": (
            "from litellm import completion\n"
            "def request():\n"
            "    response = completion(model='fixture', messages=[])\n"
            "    return response\n"
        ),
        "unlisted.py": "from litellm import completion\nother = completion()\n",
    }
    for name, text in sources.items():
        file = tmp_path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)
    listed = ["vendor/test_provider.py", "agent.py"]
    payload = {
        shape: listed if shape == "files" else [{"file": name} for name in listed]
    }
    files = load_source_files(tmp_path, manifest(tmp_path, payload))
    assert files == [tmp_path / name for name in sorted(listed)]
    result = analyze_flow_project_outputs(tmp_path, files, "fixture")["none"]
    assert {row["location"]["filepath"] for row in result["sources"]} == {
        "vendor/test_provider.py"
    }
    dependencies = {row["location"]["filepath"] for row in result["data_dependence"]}
    assert "agent.py" in dependencies
    assert "unlisted.py" not in dependencies


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"files": []},
        {"files": "agent.py"},
        {"files": [None]},
        {"files": [""]},
        {"files": ["missing.py"]},
        {"files": ["source.ts"]},
        {"files": ["agent.py", "./agent.py"]},
        {"locations": [{}]},
    ],
)
def test_invalid_scope_is_reported(tmp_path, payload):
    (tmp_path / "agent.py").write_text("pass\n")
    (tmp_path / "source.ts").write_text("export {};\n")
    with pytest.raises(ValueError):
        load_source_files(tmp_path, manifest(tmp_path, payload))


@pytest.mark.parametrize("path", ["../outside.py", "/tmp/outside.py"])
def test_paths_must_be_checkout_relative(tmp_path, path):
    with pytest.raises(SystemExit, match="unsafe relative path"):
        load_source_files(tmp_path, manifest(tmp_path, {"files": [path]}))


def test_symlink_escape_is_reported(tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("pass\n")
    (checkout / "linked.py").symlink_to(outside)
    with pytest.raises(SystemExit, match="escapes checkout"):
        load_source_files(checkout, manifest(tmp_path, {"files": ["linked.py"]}))
