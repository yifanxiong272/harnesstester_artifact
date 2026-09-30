# file: browser_use/skills/utils.py:66-140
# asked: {"lines": [66, 80, 82, 84, 85, 86, 88, 90, 91, 94, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 108, 109, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 125, 126, 127, 130, 131, 132, 134, 135, 137, 140], "branches": [[80, 82], [80, 84], [88, 90], [88, 140], [96, 97], [96, 98], [98, 99], [98, 100], [100, 101], [100, 102], [102, 103], [102, 104], [104, 105], [104, 106], [106, 108], [106, 125], [111, 112], [111, 113], [113, 114], [113, 115], [115, 116], [115, 117], [117, 118], [117, 119], [119, 120], [119, 122], [126, 127], [126, 130], [131, 132], [131, 134], [134, 135], [134, 137]]}
# gained: {"lines": [66, 80, 82, 84, 85, 86, 88, 90, 91, 94, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 108, 109, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 125, 126, 127, 130, 131, 132, 134, 135, 137, 140], "branches": [[80, 82], [80, 84], [88, 90], [88, 140], [96, 97], [96, 98], [98, 99], [98, 100], [100, 101], [100, 102], [102, 103], [102, 104], [104, 105], [104, 106], [106, 108], [111, 112], [111, 113], [113, 114], [113, 115], [115, 116], [115, 117], [117, 118], [117, 119], [119, 120], [119, 122], [126, 127], [126, 130], [131, 132], [131, 134], [134, 135], [134, 137]]}

import pytest
from pydantic import ValidationError, BaseModel
from browser_use.skills.utils import convert_json_schema_to_pydantic


def _get_model_schema(Model):
    # pydantic v2 uses model_json_schema, v1 uses schema
    if hasattr(Model, "model_json_schema"):
        return Model.model_json_schema()
    return Model.schema()


def test_empty_schema_returns_empty_model():
    Model = convert_json_schema_to_pydantic({})
    assert isinstance(Model, type)
    assert issubclass(Model, BaseModel)

    schema = _get_model_schema(Model)
    # Schema should have no properties for an empty model
    props = schema.get("properties", {})
    assert props == {}

    # Schema without 'properties' key should also return empty model
    Model2 = convert_json_schema_to_pydantic({"type": "object"})
    assert isinstance(Model2, type)
    assert issubclass(Model2, BaseModel)
    schema2 = _get_model_schema(Model2)
    assert schema2.get("properties", {}) == {}


def test_basic_types_required_and_optional_fields_and_descriptions():
    schema = {
        "type": "object",
        "properties": {
            "s": {"type": "string", "description": "string field"},
            "n": {"type": "number"},
            "i": {"type": "integer"},
            "b": {"type": "boolean", "description": "bool field"},
            "o": {"type": "object", "description": "object field"},
            "arr_str": {"type": "array", "items": {"type": "string"}},
            "arr_num": {"type": "array", "items": {"type": "number"}},
            "arr_int": {"type": "array", "items": {"type": "integer"}},
            "arr_bool": {"type": "array", "items": {"type": "boolean"}},
            "arr_obj": {"type": "array", "items": {"type": "object"}},
            "arr_any": {"type": "array", "items": {"type": "something_else"}},
        },
        "required": ["s", "n", "arr_int", "arr_any"],
    }

    Model = convert_json_schema_to_pydantic(schema, model_name="TestModel")
    assert issubclass(Model, BaseModel)

    model_schema = _get_model_schema(Model)
    props = model_schema.get("properties", {})
    expected_field_names = {
        "s",
        "n",
        "i",
        "b",
        "o",
        "arr_str",
        "arr_num",
        "arr_int",
        "arr_bool",
        "arr_obj",
        "arr_any",
    }
    assert set(props.keys()) == expected_field_names

    # Descriptions should be present in the schema
    assert props["s"].get("description") == "string field"
    assert props["b"].get("description") == "bool field"
    assert props["o"].get("description") == "object field"

    # Check required list in the schema
    required_list = set(model_schema.get("required", []))
    assert {"s", "n", "arr_int", "arr_any"}.issubset(required_list)

    # Validate parsing with correct types for required fields included
    valid_input = {
        "s": "hello",
        "n": 3.14,
        "arr_int": [1, 2, 3],
        "arr_any": [1, "two", {"three": 3}],
    }
    inst = Model.parse_obj(valid_input)
    assert inst.s == "hello"
    assert isinstance(inst.n, (float, int))  # pydantic may coerce ints to float or keep int
    assert inst.arr_int == [1, 2, 3]
    assert inst.arr_any == [1, "two", {"three": 3}]

    # Optional fields not provided should be None on the instance
    assert getattr(inst, "i") is None
    assert getattr(inst, "b") is None
    assert getattr(inst, "o") is None

    # For required fields missing, pydantic should raise ValidationError
    with pytest.raises(ValidationError):
        Model.parse_obj({"n": 1.0, "arr_int": [1], "arr_any": [1]})  # missing 's'


def test_array_item_type_branches_accept_and_validate_items():
    schema = {
        "type": "object",
        "properties": {
            "as_str": {"type": "array", "items": {"type": "string"}},
            "as_num": {"type": "array", "items": {"type": "number"}},
            "as_int": {"type": "array", "items": {"type": "integer"}},
            "as_bool": {"type": "array", "items": {"type": "boolean"}},
            "as_obj": {"type": "array", "items": {"type": "object"}},
            "as_any": {"type": "array", "items": {"type": "unknown_type"}},
        },
        "required": ["as_str", "as_num", "as_int", "as_bool", "as_obj", "as_any"],
    }

    Model = convert_json_schema_to_pydantic(schema, model_name="ArrayModel")
    payload = {
        "as_str": ["a", "b"],
        "as_num": [1.5, 2.5],
        "as_int": [1, 2],
        "as_bool": [True, False],
        "as_obj": [{"x": 1}, {"y": 2}],
        "as_any": [1, "two", {"three": 3}],
    }

    inst = Model.parse_obj(payload)

    assert inst.as_str == ["a", "b"]
    assert all(isinstance(x, str) for x in inst.as_str)
    assert inst.as_num == [1.5, 2.5]
    # numbers might be coerced to float
    assert all(isinstance(x, (float, int)) for x in inst.as_num)
    assert inst.as_int == [1, 2]
    assert all(isinstance(x, int) for x in inst.as_int)
    assert inst.as_bool == [True, False]
    assert all(isinstance(x, bool) for x in inst.as_bool)
    assert inst.as_obj == [{"x": 1}, {"y": 2}]
    assert inst.as_any == [1, "two", {"three": 3}]

    # Ensure missing a required array raises an error
    bad_payload = payload.copy()
    bad_payload.pop("as_int")
    with pytest.raises(ValidationError):
        Model.parse_obj(bad_payload)
