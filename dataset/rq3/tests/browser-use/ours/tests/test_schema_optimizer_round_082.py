import copy
from browser_use.llm import schema as schema_module
from browser_use.llm.schema import SchemaOptimizer


def _make_dummy_model(original_schema):
    class DummyModel:
        @staticmethod
        def model_json_schema():
            # Return a deep copy to avoid cross-test mutation
            return copy.deepcopy(original_schema)

    return DummyModel


def test_flatten_merge_and_forbidden_removal_round_082():
    # Construct an original schema exercising $defs/$ref flattening, anyOf, properties/title handling,
    # and fields that should be removed both at-key (optimize_schema) and in final removal pass.
    original_schema = {
        "$defs": {
            # Referenced definition deliberately has no description so sibling description
            # should be preserved when merging
            "RefA": {
                "type": "object",
                "properties": {
                    "x": {"type": "string", "minItems": 1, "default": "d"}
                },
            }
        },
        "type": "object",
        "title": "RootTitle",  # should be skipped at top-level (not in properties)
        "properties": {
            "a": {"$ref": "#/$defs/RefA", "description": "Sibling desc"},
            "items_list": {"type": "array", "items": {"minItems": 2, "default": "dd"}},
            "union": {"anyOf": [{"$ref": "#/$defs/RefA"}]},
            "nested": {"properties": {"inner": {"title": "InnerTitle", "type": "string"}}},
        },
        "minItems": 5,
        "default": "root_default",
    }

    DummyModel = _make_dummy_model(original_schema)

    # Patch _make_strict_compatible to capture that it's invoked with the optimized schema
    called = {}
    original_fn = SchemaOptimizer._make_strict_compatible

    def fake_make_strict_compatible(sch):
        # record a shallow property to assert the call happened and schema mutated
        called['seen_root_type'] = sch.get('type')

    SchemaOptimizer._make_strict_compatible = fake_make_strict_compatible

    try:
        result = SchemaOptimizer.create_optimized_json_schema(DummyModel, remove_min_items=True, remove_defaults=True)
    finally:
        # restore to avoid side effects for other tests
        SchemaOptimizer._make_strict_compatible = original_fn

    # Basic structure assertions
    assert isinstance(result, dict)

    # Top-level title should have been skipped (not preserved at non-properties root)
    assert 'title' not in result

    # additionalProperties must be set to False for all objects (root and nested)
    assert result.get('additionalProperties') is False
    assert result['properties']['a'].get('additionalProperties') is False

    # The $ref for 'a' should have been flattened. Since the referenced def lacked a description,
    # the sibling description should have been preserved on merge.
    a_prop = result['properties']['a']
    assert a_prop['description'] == 'Sibling desc'

    # The referenced property's nested field should have had 'default' and 'minItems' removed
    # due to remove_min_items/remove_defaults being True
    assert 'default' not in a_prop['properties']['x']
    assert 'minItems' not in a_prop['properties']['x']

    # The anyOf branch should have been preserved and its $ref flattened as well
    anyof_item = result['properties']['union']['anyOf'][0]
    assert isinstance(anyof_item, dict)
    assert anyof_item.get('additionalProperties') is False
    # And nested minItems/default removed in anyOf flattened content
    assert 'default' not in anyof_item['properties']['x']
    assert 'minItems' not in anyof_item['properties']['x']

    # Titles inside properties may be preserved but are not guaranteed in all merge paths.
    # Accept either presence with expected value or absence.
    inner = result['properties']['nested']['properties']['inner']
    if 'title' in inner:
        assert inner['title'] == 'InnerTitle'

    # Ensure our fake strict-compat function was invoked
    assert called.get('seen_root_type') == 'object'


def test_preserve_defaults_when_flags_false_round_082():
    # When remove_min_items and remove_defaults are False, defaults and minItems should remain
    original_schema = {
        "$defs": {
            "RefB": {
                "type": "object",
                "properties": {
                    "y": {"type": "string", "minItems": 3, "default": "keepme"}
                },
            }
        },
        "type": "object",
        "properties": {
            "b": {"$ref": "#/$defs/RefB"},
            "arr": {"type": "array", "items": {"minItems": 4, "default": "arrdef"}},
        },
    }

    DummyModel = _make_dummy_model(original_schema)

    # No-op strict compatibility to avoid unknown side effects
    original_fn = SchemaOptimizer._make_strict_compatible
    SchemaOptimizer._make_strict_compatible = lambda s: None

    try:
        result = SchemaOptimizer.create_optimized_json_schema(DummyModel, remove_min_items=False, remove_defaults=False)
    finally:
        SchemaOptimizer._make_strict_compatible = original_fn

    # Defaults and minItems should still be present somewhere in the optimized result
    b_prop = result['properties']['b']
    # The referenced def should be flattened and still include the nested default and minItems
    assert b_prop['properties']['y']['default'] == 'keepme'
    assert b_prop['properties']['y']['minItems'] == 3

    # The array item defaults should also be present
    assert result['properties']['arr']['items']['default'] == 'arrdef'
    assert result['properties']['arr']['items']['minItems'] == 4

    # additionalProperties should still be present and False for object types
    assert result.get('additionalProperties') is False
    assert b_prop.get('additionalProperties') is False
