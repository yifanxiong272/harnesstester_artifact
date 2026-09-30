# file: rdagent/scenarios/data_science/scen/utils.py:189-269
# asked: {"lines": [191, 192, 194, 196, 198, 199, 200, 203, 204, 206, 207, 208, 209, 211, 213, 215, 216, 219, 220, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 235, 236, 238, 239, 242, 243, 244, 245, 246, 247, 248, 250, 251, 252, 253, 254, 255, 256, 258, 261, 262, 264, 266, 267, 269], "branches": [[203, 204], [203, 213], [213, 215], [213, 235], [223, 224], [223, 269], [224, 225], [224, 227], [227, 223], [227, 228], [242, 243], [242, 251], [244, 245], [244, 258], [245, 246], [245, 247], [247, 248], [247, 250], [251, 252], [251, 258], [253, 254], [253, 258], [255, 256], [255, 258]]}
# gained: {"lines": [191, 192, 194, 196, 198, 199, 200, 203, 204, 206, 207, 208, 213, 215, 216, 219, 220, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 235, 236, 238, 239, 242, 243, 244, 245, 246, 247, 248, 250, 251, 252, 253, 254, 255, 256, 258, 261, 262, 264, 266, 267, 269], "branches": [[203, 204], [203, 213], [213, 215], [213, 235], [223, 224], [224, 225], [224, 227], [227, 228], [242, 243], [242, 251], [244, 245], [244, 258], [245, 246], [245, 247], [247, 248], [247, 250], [251, 252], [253, 254], [255, 256]]}

import json
from pathlib import Path

import pytest

from rdagent.scenarios.data_science.scen.utils import preview_json


def test_preview_json_single_object_dict(tmp_path):
    # Create a JSON file with a dict containing a list, a dict, and a simple type
    data = {"a": [1, 2], "b": {"x": 1, "y": 2}, "c": 42}
    p = tmp_path / "single_obj.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    out = preview_json(p, p.name)

    # Basic header and format
    assert out.startswith(f"### {p.name}:"), out
    assert "#### 1.Format: Single JSON object" in out
    assert "#### 2.Structure overview:" in out

    # Type line and keys
    assert "Type: Object with 3 keys" in out
    # Specific key descriptions
    assert "  - a: array[2]" in out
    assert "  - b: object{2 keys}" in out
    assert "  - c: int" in out

    # Content preview present (reprlib)
    assert "#### 3.Content preview (reprlib):" in out
    # reprlib should include representation of the top-level object
    assert "{'a': [1, 2], 'b': {'x': 1, 'y': 2}, 'c': 42" in out or '"a": [1, 2]' in out


def test_preview_json_single_array_with_sample_dict(tmp_path):
    # Create a JSON file with an array whose first item is a dict
    data = [{"k1": 1, "k2": 2}, {"k1": 3}]
    p = tmp_path / "array.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    out = preview_json(p, p.name)

    assert f"### {p.name}:" in out
    assert "#### 1.Format: Single JSON object" in out
    # Array type line
    assert "Type: Array with 2 items" in out
    # Sample item keys should be reported
    assert "Sample item keys: ['k1', 'k2']" in out or 'Sample item keys: ["k1", "k2"]' in out
    assert "#### 3.Content preview (reprlib):" in out
    # reprlib preview of the array should appear
    assert ("{'k1': 1, 'k2': 2}" in out) or ('"k1": 1' in out)


def test_preview_json_jsonl_including_invalid_line_and_truncation(tmp_path):
    # Create a JSONL file where first two lines are valid JSON objects,
    # third line is invalid JSON, and there is a fourth valid line to ensure truncation message appears.
    lines = [
        json.dumps({"x": 1}),
        json.dumps({"y": 2}),
        "not a json",
        json.dumps({"z": 3}),
    ]
    p = tmp_path / "sample.jsonl"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    out = preview_json(p, p.name)

    # Header and format identification
    assert f"### {p.name}:" in out
    assert "#### 1.Format: JSONL (JSON Lines)" in out
    assert "#### 2.Content preview (first few objects):" in out

    # Objects 1 and 2 should be shown as parsed
    assert "Object 1:" in out
    assert "Object 2:" in out

    # Object 3 was invalid JSON
    assert "Object 3: Invalid JSON" in out

    # Because there is a fourth line, the function should show the truncation message when reaching i >= 3
    assert "... (showing first 3 JSONL objects)" in out


def test_preview_json_exception_on_bad_single_json(tmp_path):
    # Create a file that is not valid JSON (single-line incomplete JSON) to trigger the outer exception handling
    p = tmp_path / "bad.json"
    p.write_text("{", encoding="utf-8")  # invalid JSON

    out = preview_json(p, p.name)

    # Should include the Error processing JSON message
    assert "Error processing JSON:" in out
    # The message should include at least some part of the underlying error text (truncate applied in function)
    assert len(out.splitlines()[-1]) > len("Error processing JSON:")


