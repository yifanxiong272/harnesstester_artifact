import pytest
from gpt_researcher.mcp import research

# Create instances without invoking __init__ to avoid constructor dependencies
def _new_skill():
    return research.MCPResearchSkill.__new__(research.MCPResearchSkill)

class BadDict(dict):
    """A dict subclass whose .get() raises to force an exception path inside _process_tool_result."""
    def get(self, *args, **kwargs):
        raise RuntimeError("boom")


def test_structured_items_round_006():
    skill = _new_skill()
    tool = "toolA"
    result = {
        "structured_content": {
            "results": [
                {"title": "T1", "href": "H1", "body": "B1"},
                {"url": "U2", "content": "C2"}
            ]
        }
    }

    out = skill._process_tool_result(tool, result)

    # Two items should be returned and fields should be drawn from provided keys
    assert isinstance(out, list) and len(out) == 2
    assert out[0]["title"] == "T1"
    assert out[0]["href"] == "H1"
    assert out[0]["body"] == "B1"

    # Second item: title falls back to generated, href comes from url, body from content
    assert out[1]["title"] == "Result from toolA #2"
    assert out[1]["href"] == "U2"
    assert out[1]["body"] == "C2"


def test_structured_single_round_006():
    skill = _new_skill()
    tool = "toolB"
    result = {"structured_content": {"title": "Single", "url": "u", "content": "body"}}

    out = skill._process_tool_result(tool, result)

    assert isinstance(out, list) and len(out) == 1
    assert out[0]["title"] == "Single"
    assert out[0]["href"] == "u"
    assert out[0]["body"] == "body"


def test_content_list_parts_round_006():
    skill = _new_skill()
    tool = "toolC"
    result = {
        "content": [
            {"type": "text", "text": "alpha"},
            {"text": 123},
            {"foo": "bar"},
            42,
        ]
    }

    out = skill._process_tool_result(tool, result)

    assert isinstance(out, list) and len(out) == 1
    # The pieces should be stringified and joined with double newlines in the same order
    expected_body = "alpha\n\n123\n\n{" + "'foo': 'bar'" + "}\n\n42"
    # Build expected deterministically to avoid formatting surprises
    expected_body = "alpha\n\n123\n\n{'foo': 'bar'}\n\n42"
    assert out[0]["body"] == expected_body
    assert out[0]["title"] == "Result from toolC"
    assert out[0]["href"] == "mcp://toolC"


def test_list_result_mixed_round_006():
    skill = _new_skill()
    tool = "toolD"
    result = [
        {"title": "T1", "content": "C1"},
        {"foo": "bar"}
    ]

    out = skill._process_tool_result(tool, result)

    assert isinstance(out, list) and len(out) == 2
    assert out[0]["title"] == "T1"
    assert out[0]["body"] == "C1"
    # Second item is generic
    assert out[1]["title"] == "Result from toolD"
    assert out[1]["href"] == "mcp://toolD/1"
    assert out[1]["body"] == str({"foo": "bar"})


def test_non_mcp_dict_round_006():
    skill = _new_skill()
    tool = "toolE"
    result = {"title": "X", "url": "Y", "content": "Z"}

    out = skill._process_tool_result(tool, result)

    assert isinstance(out, list) and len(out) == 1
    assert out[0]["title"] == "X"
    assert out[0]["href"] == "Y"
    assert out[0]["body"] == "Z"


def test_non_dict_other_round_006():
    skill = _new_skill()
    tool = "toolF"
    result = 12345

    out = skill._process_tool_result(tool, result)

    assert isinstance(out, list) and len(out) == 1
    assert out[0]["title"] == "Result from toolF"
    assert out[0]["href"] == "mcp://toolF"
    assert out[0]["body"] == str(12345)


def test_exception_in_item_get_round_006():
    skill = _new_skill()
    tool = "toolG"
    # Make a structured_content where an item is a dict-like whose .get() raises
    bad = BadDict({"title": "hidden"})
    result = {"structured_content": {"results": [bad]}}

    out = skill._process_tool_result(tool, result)

    # An exception inside processing should be caught and a fallback result appended
    assert isinstance(out, list) and len(out) == 1
    assert out[0]["title"] == "Result from toolG"
    assert out[0]["href"] == "mcp://toolG"
    # Body should be the stringified original result (deterministic)
    assert out[0]["body"] == str(result)
