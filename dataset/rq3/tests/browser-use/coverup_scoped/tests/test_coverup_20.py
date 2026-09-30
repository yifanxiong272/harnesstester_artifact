# file: browser_use/llm/vercel/chat.py:402-477
# asked: {"lines": [402, 411, 412, 414, 415, 416, 417, 418, 419, 421, 423, 424, 425, 426, 427, 430, 431, 432, 433, 435, 438, 439, 441, 442, 443, 444, 447, 448, 449, 450, 451, 454, 456, 460, 461, 462, 463, 464, 466, 469, 470, 472, 473, 474, 475, 477], "branches": [[411, 412], [411, 438], [415, 416], [415, 431], [416, 417], [416, 430], [419, 421], [419, 427], [423, 424], [423, 426], [424, 423], [424, 425], [431, 432], [431, 433], [439, 441], [439, 473], [442, 443], [442, 459], [443, 442], [443, 444], [446, 454], [446, 456], [459, 466], [459, 469], [469, 470], [469, 472], [473, 474], [473, 475]]}
# gained: {"lines": [402, 411, 412, 414, 415, 416, 417, 418, 419, 421, 423, 424, 425, 426, 427, 430, 431, 432, 433, 435, 438, 439, 441, 442, 443, 444, 447, 448, 449, 450, 451, 454, 456, 460, 461, 462, 463, 464, 469, 470, 472, 473, 474, 475, 477], "branches": [[411, 412], [415, 416], [415, 431], [416, 417], [416, 430], [419, 421], [419, 427], [423, 424], [423, 426], [424, 425], [431, 432], [431, 433], [439, 441], [439, 473], [442, 443], [442, 459], [443, 442], [443, 444], [446, 454], [446, 456], [459, 469], [469, 470], [469, 472], [473, 474], [473, 475]]}

import copy
import pytest

from browser_use.llm.vercel.chat import ChatVercel


def _deep_get(d, path):
    """Helper to get nested dictionary value by path list."""
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def test_fix_gemini_schema_resolve_and_clean():
    # Create an instance without calling __init__
    inst = object.__new__(ChatVercel)

    schema = {
        "$defs": {
            "MyType": {
                "type": "OBJECT",
                "properties": {},  # empty -> should become placeholder
                "additionalProperties": True,
                "title": "SomeTitle",
                "required": ["title", "x"],
            }
        },
        "type": "object",
        "properties": {
            "a": {"$ref": "#/$defs/MyType", "extra": "val"}
        },
        "default": "something",
    }

    # Work on a copy to ensure our test's input isn't accidentally reused elsewhere
    schema_in = copy.deepcopy(schema)
    result = inst._fix_gemini_schema(schema_in)

    # Top-level 'default' must be removed
    assert "default" not in result

    # The $defs should have been resolved and merged into the 'a' property
    assert "properties" in result
    assert "a" in result["properties"]

    a_obj = result["properties"]["a"]

    # The extra key from the object that referenced the def must be merged
    assert a_obj.get("extra") == "val"

    # The 'type' from the def should be preserved
    assert a_obj.get("type") == "OBJECT"

    # additionalProperties and title should be removed from the resolved object
    assert "additionalProperties" not in a_obj
    assert "title" not in a_obj

    # The required list should have 'title' removed, leaving 'x'
    assert a_obj.get("required") == ["x"]

    # The empty properties in the resolved object should have been replaced by the placeholder
    assert a_obj.get("properties") == {"_placeholder": {"type": "string"}}


def test_fix_gemini_schema_ref_not_found_and_list_cleaning():
    # Create an instance without calling __init__
    inst = object.__new__(ChatVercel)

    schema = {
        "$defs": {
            "Exists": {"type": "OBJECT", "properties": {}, "required": ["title"]}
        },
        # items is a list to exercise list handling in clean_schema
        "items": [
            {"$ref": "#/$defs/NotExists", "foo": "bar"},
            {"type": "string", "title": "T", "default": "d"},
        ],
        "required": ["title", "other"],
        "title": "TopTitle",
        "additionalProperties": False,
    }

    schema_in = copy.deepcopy(schema)
    result = inst._fix_gemini_schema(schema_in)

    # Top-level title and additionalProperties should be removed
    assert "title" not in result
    assert "additionalProperties" not in result

    # The first item referenced a non-existent def; resolve_refs pops $ref and returns the obj,
    # so final cleaned first item should have no '$ref' but should keep other keys.
    assert isinstance(result.get("items"), list)
    assert result["items"][0] == {"foo": "bar"}

    # The second item should have had 'title' and 'default' removed by clean_schema
    assert result["items"][1] == {"type": "string"}

    # The top-level required should have 'title' removed
    assert result.get("required") == ["other"]
