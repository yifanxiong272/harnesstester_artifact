# file: gpt_researcher/mcp/research.py:158-271
# asked: {"lines": [158, 169, 171, 173, 174, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 188, 189, 190, 191, 192, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 207, 209, 210, 211, 212, 214, 215, 216, 217, 218, 220, 223, 225, 226, 228, 229, 230, 231, 232, 234, 237, 238, 239, 240, 242, 244, 246, 247, 248, 249, 251, 254, 255, 256, 257, 259, 261, 262, 264, 265, 266, 267, 269, 271], "branches": [[173, 174], [173, 223], [177, 178], [177, 195], [179, 180], [179, 188], [180, 181], [180, 195], [181, 180], [181, 182], [188, 189], [188, 195], [195, 196], [195, 220], [197, 198], [197, 211], [199, 200], [199, 210], [200, 201], [200, 209], [201, 202], [201, 203], [203, 204], [203, 207], [211, 212], [211, 214], [223, 225], [223, 244], [225, 226], [225, 271], [226, 225], [226, 228], [228, 229], [228, 237], [244, 246], [244, 254]]}
# gained: {"lines": [158, 169, 171, 173, 174, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 188, 189, 190, 191, 192, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 207, 209, 210, 211, 212, 215, 216, 217, 218, 220, 223, 225, 226, 228, 229, 230, 231, 232, 234, 237, 238, 239, 240, 242, 244, 246, 247, 248, 249, 251, 254, 255, 256, 257, 259, 261, 262, 264, 265, 266, 267, 269, 271], "branches": [[173, 174], [173, 223], [177, 178], [177, 195], [179, 180], [179, 188], [180, 181], [180, 195], [181, 182], [188, 189], [195, 196], [195, 220], [197, 198], [197, 211], [199, 200], [199, 210], [200, 201], [200, 209], [201, 202], [201, 203], [203, 204], [203, 207], [211, 212], [223, 225], [223, 244], [225, 226], [225, 271], [226, 225], [226, 228], [228, 229], [228, 237], [244, 246], [244, 254]]}

import pytest
from typing import Any, Dict, List

from gpt_researcher.mcp.research import MCPResearchSkill


def _skill_instance():
    # Create instance without calling __init__ to avoid unexpected init requirements
    return object.__new__(MCPResearchSkill)


def test_structured_content_with_results_and_fallback_title_href_body():
    skill = _skill_instance()
    tool_name = "toolA"
    result = {
        "structured_content": {
            "results": [
                {"title": "Title1", "href": "http://a/1", "body": "Body1"},
                {"url": "http://a/2", "content": "Content2"},
                {"title": "Title3", "url": "http://a/3", "content": "Content3"},
            ]
        }
    }

    out = skill._process_tool_result(tool_name, result)
    # Expect 3 processed items
    assert isinstance(out, list) and len(out) == 3

    # First item should preserve title, href, body
    assert out[0]["title"] == "Title1"
    assert out[0]["href"] == "http://a/1"
    assert out[0]["body"] == "Body1"

    # Second item had no title; title must be auto-generated with #2 (i+1)
    assert "Result from toolA #2" in out[1]["title"]
    # href should come from url field
    assert out[1]["href"] == "http://a/2"
    # body should equal content
    assert out[1]["body"] == "Content2"

    # Third item had title and url/content: title preserved, href from url, body from content
    assert out[2]["title"] == "Title3"
    assert out[2]["href"] == "http://a/3"
    assert out[2]["body"] == "Content3"


def test_structured_content_single_dict_when_no_results_list():
    skill = _skill_instance()
    tool_name = "toolB"
    structured = {
        "title": "OnlyOne",
        "href": "mcp://only",
        "body": "SingleBody"
    }
    result = {"structured_content": structured}

    out = skill._process_tool_result(tool_name, result)
    assert isinstance(out, list) and len(out) == 1
    assert out[0]["title"] == "OnlyOne"
    assert out[0]["href"] == "mcp://only"
    assert out[0]["body"] == "SingleBody"


def test_content_list_with_various_parts_and_string_content():
    skill = _skill_instance()
    tool_name = "toolC"
    result = {
        "content": [
            {"type": "text", "text": "hello"},
            {"text": 123},
            {"foo": "bar"},
            "plain string",
            999  # non-dict content part
        ]
    }

    out = skill._process_tool_result(tool_name, result)
    assert isinstance(out, list) and len(out) == 1
    body = out[0]["body"]
    # Check that text parts are joined by double newlines and stringified
    assert "hello" in body
    assert "123" in body
    assert "{'foo': 'bar'}" in body or '{"foo": "bar"}' in body  # dict string repr may vary spacing
    assert "plain string" in body
    assert "999" in body

    # Now test content being a plain string
    out2 = skill._process_tool_result(tool_name, {"content": "just text"})
    assert len(out2) == 1
    assert out2[0]["body"] == "just text"


def test_result_list_mixed_items_and_non_dicts_ignored():
    skill = _skill_instance()
    tool_name = "toolD"
    lst = [
        {"title": "HasTitle", "content": "C1"},
        {"url": "http://x", "other": "v"},
        42,
        "a string"
    ]

    out = skill._process_tool_result(tool_name, lst)
    # Only the dict entries are processed; non-dict items in the list are ignored by the loop
    # First item becomes one result; second dict has no title/content/body so becomes generic result
    assert isinstance(out, list)
    # Expect 2 results (two dicts processed)
    assert len(out) == 2

    assert out[0]["title"] == "HasTitle"
    assert out[0]["body"] == "C1"
    # second result should have generic title and href with index 1
    assert out[1]["title"] == f"Result from {tool_name}"
    assert out[1]["href"].endswith("/1")
    # body should be stringified dict
    assert "http" in out[1]["body"] or "url" in out[1]["body"]


def test_non_mcp_dict_and_other_types_handled():
    skill = _skill_instance()
    tool_name = "toolE"

    # Non-MCP dict (no structured_content/content)
    d = {"title": "Custom", "href": "http://h", "body": "B"}
    out = skill._process_tool_result(tool_name, d)
    assert len(out) == 1
    assert out[0]["title"] == "Custom"
    assert out[0]["href"] == "http://h"
    assert out[0]["body"] == "B"

    # Other type (int) should produce stringified body
    out2 = skill._process_tool_result(tool_name, 12345)
    assert len(out2) == 1
    assert out2[0]["body"] == "12345"


def test_exception_in_processing_triggers_fallback(monkeypatch):
    skill = _skill_instance()
    tool_name = "toolF"

    class BadDict(dict):
        def get(self, *args, **kwargs):
            raise RuntimeError("boom")

    bad = BadDict(a=1)

    # Ensure that logger.error does not raise; patch to capture call
    calls = []

    import logging

    # Attempt to find logger used by module; fallback to root logger if not present
    try:
        from gpt_researcher.mcp import research as research_mod
        logger_obj = getattr(research_mod, "logger", logging.getLogger("test"))
    except Exception:
        logger_obj = logging.getLogger("test")

    def fake_error(msg):
        calls.append(msg)

    monkeypatch.setattr(logger_obj, "error", fake_error, raising=False)

    out = skill._process_tool_result(tool_name, bad)
    # Because BadDict.get raises, the except branch should be taken and a fallback result appended
    assert isinstance(out, list) and len(out) == 1
    assert out[0]["title"] == f"Result from {tool_name}"
    assert out[0]["href"] == f"mcp://{tool_name}"
    # body should be str(bad)
    assert str(bad) in out[0]["body"]
    # logger.error should have been called at least once
    assert any("Error processing tool result" in c or "boom" in c for c in calls)
