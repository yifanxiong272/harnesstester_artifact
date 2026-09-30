import copy
from browser_use.llm.vercel.chat import ChatVercel


def test_resolve_and_merge_refs_round_039():
    # $defs resolution and merging of extra properties; empty properties should become placeholder
    schema = {
        "$defs": {
            "MyType": {"type": "object", "properties": {}}
        },
        "root": {"$ref": "#/$defs/MyType", "extra": "value"},
    }

    # Use a deep copy so the original input isn't relied on after in-place pops
    inp = copy.deepcopy(schema)
    out = ChatVercel._fix_gemini_schema(None, inp)

    # The $ref should be resolved (no '$ref' at this location) and merged 'extra' preserved
    assert isinstance(out.get("root"), dict)
    assert "$ref" not in out["root"]
    assert out["root"].get("extra") == "value"

    # Because the resolved definition had empty properties and type 'object',
    # a '_placeholder' property should have been added by clean_schema
    props = out["root"].get("properties")
    assert isinstance(props, dict)
    assert "_placeholder" in props
    assert props["_placeholder"]["type"] == "string"


def test_unresolved_ref_preserved_round_039():
    # If a $ref name is not present in $defs, it should be left as-is
    schema = {"$defs": {}, "elem": {"$ref": "#/some/Unknown"}}
    out = ChatVercel._fix_gemini_schema(None, copy.deepcopy(schema))

    # The unresolved $ref should still be present (clean_schema does not remove arbitrary keys)
    assert out.get("elem") and out["elem"].get("$ref") == "#/some/Unknown"


def test_list_ref_resolution_round_039():
    # resolve_refs should correctly process lists containing $ref entries
    schema = {"$defs": {"T": {"type": "string"}}, "arr": [{"$ref": "#/$defs/T"}]}
    out = ChatVercel._fix_gemini_schema(None, copy.deepcopy(schema))

    assert isinstance(out.get("arr"), list)
    first = out["arr"][0]
    # The referenced definition becomes the resolved dict
    assert isinstance(first, dict)
    assert first.get("type") == "string"


def test_cleaning_additional_and_required_round_039():
    # Removal of unsupported properties and cleaning of required list
    schema = {
        "type": "object",
        "properties": {},
        "additionalProperties": True,
        "title": "MyTitle",
        "default": 123,
        "required": ["title", "other"],
    }

    out = ChatVercel._fix_gemini_schema(None, copy.deepcopy(schema))

    # 'additionalProperties', 'title', and 'default' should be removed at the top level
    assert "additionalProperties" not in out
    assert "title" not in out
    assert "default" not in out

    # Empty properties should be replaced with a placeholder
    assert "properties" in out and "_placeholder" in out["properties"]
    assert out["properties"]["_placeholder"]["type"] == "string"

    # 'title' should have been removed from the required list
    assert "required" in out and isinstance(out["required"], list)
    assert "title" not in out["required"]
    assert "other" in out["required"]
