# file: browser_use/llm/google/chat.py:561-635
# asked: {"lines": [570, 571, 573, 574, 575, 576, 577, 578, 580, 582, 583, 584, 585, 586, 589, 590, 591, 592, 594, 597, 598, 600, 601, 604, 605, 606, 609, 610, 611, 612, 613, 616, 618, 622, 623, 624, 625, 626, 628, 630, 631, 632, 633, 635], "branches": [[570, 571], [570, 597], [574, 575], [574, 590], [575, 576], [575, 589], [578, 580], [578, 586], [582, 583], [582, 585], [583, 582], [583, 584], [590, 591], [590, 592], [598, 600], [598, 631], [601, 604], [601, 621], [605, 601], [605, 606], [608, 616], [608, 618], [621, 628], [621, 630], [631, 632], [631, 633]]}
# gained: {"lines": [570, 571, 573, 574, 575, 576, 577, 578, 580, 582, 583, 584, 585, 586, 589, 590, 592, 594, 597, 598, 600, 601, 604, 605, 606, 609, 610, 611, 612, 613, 616, 618, 622, 623, 624, 625, 626, 628, 630, 631, 633, 635], "branches": [[570, 571], [570, 597], [574, 575], [574, 590], [575, 576], [575, 589], [578, 580], [578, 586], [582, 583], [582, 585], [583, 584], [590, 592], [598, 600], [598, 631], [601, 604], [601, 621], [605, 601], [605, 606], [608, 616], [608, 618], [621, 628], [621, 630], [631, 633]]}

import copy
import pytest

from browser_use.llm.google.chat import ChatGoogle


def test_fix_gemini_schema_resolve_and_clean():
    cg = ChatGoogle(model="test-model")

    schema = {
        "$defs": {
            "Foo": {
                "type": "OBJECT",
                "properties": {"a": {"type": "string"}},
                "additionalProperties": True,
                "title": "FooTitle",
            }
        },
        "type": "OBJECT",
        "title": "TopTitle",
        "properties": {
            "refed": {"$ref": "#/$defs/Foo", "description": "adds"},
            "emptyprops": {"type": "OBJECT", "properties": {}},
            "unknown_ref": {"$ref": "#/$defs/Bar", "x": "y"},
        },
        "additionalProperties": False,
        "default": "remove me",
    }

    schema_copy = copy.deepcopy(schema)
    out = cg._fix_gemini_schema(schema_copy)

    # Top-level metadata fields removed
    assert "title" not in out
    assert "additionalProperties" not in out
    assert "default" not in out

    # Properties exist
    assert "properties" in out and isinstance(out["properties"], dict)
    props = out["properties"]

    # Resolved reference: 'refed' should have merged fields from the def and the referencing object
    assert "refed" in props
    refed = props["refed"]
    assert isinstance(refed, dict)
    # Type from the def preserved
    assert "type" in refed and refed["type"].upper() == "OBJECT"
    # Merged extra field from the referencing object
    assert refed.get("description") == "adds"
    # The 'title' that was in the $defs entry should have been removed as metadata
    assert "title" not in refed

    # Empty properties inside an OBJECT should get a placeholder
    assert "emptyprops" in props
    emptyprops = props["emptyprops"]
    assert "properties" in emptyprops
    assert emptyprops["properties"] == {"_placeholder": {"type": "string"}}

    # Unknown $ref should be popped (the $ref key removed) and remaining keys preserved
    assert "unknown_ref" in props
    unknown = props["unknown_ref"]
    assert "$ref" not in unknown
    assert unknown.get("x") == "y"


def test_fix_gemini_schema_second_placeholder_branch():
    """
    Craft a dict subclass to make obj.get('type') return a non-string at the moment
    the 'properties' key is processed (so the first placeholder insertion in-loop is skipped),
    but the actual 'type' value (accessed via iteration) is 'OBJECT', so after the loop
    the second placeholder insertion branch should run.
    """

    cg = ChatGoogle(model="test-model")

    class FakeDict(dict):
        def get(self, key, default=None):
            # When clean_schema checks obj.get('type', ''), return None to skip the in-loop placeholder.
            # However the underlying stored value for 'type' remains 'OBJECT' so when the 'type'
            # key is later processed it will be copied into the cleaned dict.
            if key == "type":
                return None
            return super().get(key, default)

    schema = FakeDict({"properties": {}, "type": "OBJECT"})
    out = cg._fix_gemini_schema(schema)

    # After processing, the second placeholder branch should have added the placeholder
    assert out.get("type") == "OBJECT"
    assert "properties" in out
    assert out["properties"] == {"_placeholder": {"type": "string"}}
