# file: browser_use/sandbox/sandbox.py:533-669
# asked: {"lines": [552, 556, 557, 558, 563, 566, 570, 571, 572, 574, 575, 577, 578, 579, 580, 584, 585, 586, 587, 588, 592, 593, 594, 595, 596, 597, 612, 631, 635, 636, 638, 639, 640, 641, 642, 643, 644, 646, 661, 662, 663, 664], "branches": [[550, 558], [551, 552], [553, 550], [562, 563], [564, 566], [569, 570], [570, 571], [570, 572], [572, 574], [572, 580], [575, 577], [575, 579], [583, 584], [584, 585], [584, 586], [586, 587], [586, 588], [591, 592], [592, 593], [592, 597], [611, 612], [614, 631], [626, 629], [634, 635], [635, 636], [635, 638], [638, 639], [638, 646], [640, 641], [640, 644], [641, 640], [641, 642], [660, 661]]}
# gained: {"lines": [563, 570, 571, 572, 574, 575, 577, 578, 579, 580, 584, 585, 586, 587, 592, 593, 594, 595, 596, 597, 612, 631, 635, 638, 639, 640, 641, 642, 643, 644, 646, 661, 662, 663, 664], "branches": [[562, 563], [569, 570], [570, 571], [570, 572], [572, 574], [572, 580], [575, 577], [575, 579], [583, 584], [584, 585], [584, 586], [586, 587], [591, 592], [592, 593], [592, 597], [611, 612], [614, 631], [634, 635], [635, 638], [638, 639], [638, 646], [640, 641], [640, 644], [641, 642], [660, 661]]}

import importlib
import enum
import dataclasses
import typing

import pytest


@pytest.fixture
def sandbox_module():
    return importlib.import_module("browser_use.sandbox.sandbox")


def test_union_none_and_simple_union(sandbox_module):
    sb = sandbox_module
    # Union with None and data None should return None (line 552)
    U = typing.Union[int, type(None)]
    assert sb._parse_with_type_annotation(None, U) is None

    # Simple Union where first arg doesn't change data -> should return the input data
    U2 = typing.Union[int, str]
    assert sb._parse_with_type_annotation("hello", U2) == "hello"


def test_list_tuple_dict_and_enum_handling(sandbox_module):
    sb = sandbox_module
    # List: non-list returns input
    ListInt = typing.List[int]
    assert sb._parse_with_type_annotation("notalist", ListInt) == "notalist"
    # List with args returns list of parsed items (int parsing does no change)
    assert sb._parse_with_type_annotation([1, 2, 3], ListInt) == [1, 2, 3]

    # Tuple: non-iterable returns input
    TupleIntStr = typing.Tuple[int, str]
    assert sb._parse_with_type_annotation(123, TupleIntStr) == 123
    # Tuple with args parses each element and returns tuple
    assert sb._parse_with_type_annotation([1, "x"], TupleIntStr) == (1, "x")
    # Tuple with single arg uses last arg for extras
    TupleIntOnly = typing.Tuple[int]
    assert sb._parse_with_type_annotation([1, 2, 3], TupleIntOnly) == (1, 2, 3)
    # Tuple with no args (typing.Tuple) should convert list to tuple
    TupleNoArgs = typing.Tuple
    assert sb._parse_with_type_annotation([1, 2], TupleNoArgs) == (1, 2)

    # Dict: non-dict returns input
    DictStrInt = typing.Dict[str, int]
    assert sb._parse_with_type_annotation("notadict", DictStrInt) == "notadict"
    # Dict with args: parse keys and values
    d = {"k": "v"}
    parsed = sb._parse_with_type_annotation(d, typing.Dict[str, str])
    assert isinstance(parsed, dict) and parsed == {"k": "v"}

    # Enum handling
    class E1(enum.Enum):
        A = 1
        B = 2

    # Name-based lookup
    assert sb._parse_with_type_annotation("A", E1) is E1.A
    # Value-based lookup (non-str goes to annotation(data))
    assert sb._parse_with_type_annotation(2, E1) is E1.B

    # For string that's actually a value but not a name, ensure KeyError path is handled:
    class E2(enum.Enum):
        X = "vx"

    # 'X' -> name
    assert sb._parse_with_type_annotation("X", E2) is E2.X
    # 'vx' -> not a name, should go to annotation(data)
    assert sb._parse_with_type_annotation("vx", E2) is E2.X


def test_pydantic_v2_model_construct_and_agent_history_list_handling(sandbox_module):
    sb = sandbox_module

    # Create a fake pydantic v2-style class with model_fields and model_construct
    class DummyField:
        def __init__(self, ann):
            self.annotation = ann

    class AgentHistoryList:
        model_fields = {"val": DummyField(int)}

        def __init__(self, **kwargs):
            # store values for assertions
            self.__dict__.update(kwargs)

        @classmethod
        def model_construct(cls, **kwargs):
            return cls(**kwargs)

    # Output model schema class with model_validate_json attribute to trigger _output_model_schema set
    class OutputModel:
        @staticmethod
        def model_validate_json(x):
            return x

    # Create an annotation object exposing __pydantic_generic_metadata__
    class Annot:
        __pydantic_generic_metadata__ = {"origin": AgentHistoryList, "args": (OutputModel,)}

    # Passing non-dict should return data
    assert sb._parse_with_type_annotation("x", Annot) == "x"

    # Passing dict should construct and set _output_model_schema
    res = sb._parse_with_type_annotation({"val": 7}, Annot)
    assert isinstance(res, AgentHistoryList)
    assert getattr(res, "val") == 7
    assert getattr(res, "_output_model_schema") is OutputModel

    # Now test fallback when model_fields not present: class with only model_construct
    class SimpleModel:
        def __init__(self, **kwargs):
            self.kw = kwargs

        @classmethod
        def model_construct(cls, **kwargs):
            return cls(**kwargs)

    # Annotation without pydantic meta but points directly to the class
    res2 = sb._parse_with_type_annotation({"a": 1}, SimpleModel)
    # should return the result of model_construct
    assert isinstance(res2, SimpleModel) and res2.kw == {"a": 1}


def test_pydantic_v1_construct_handling(sandbox_module):
    sb = sandbox_module

    # Fake pydantic v1 class with __fields__ mapping
    class FieldObj:
        def __init__(self, outer_type_):
            self.outer_type_ = outer_type_

    class PydV1:
        __fields__ = {"x": FieldObj(int)}

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        @classmethod
        def construct(cls, **kwargs):
            return cls(**kwargs)

    parsed = sb._parse_with_type_annotation({"x": 5}, PydV1)
    assert isinstance(parsed, PydV1)
    assert parsed.x == 5

    # Fallback without __fields__
    class PydV1NoFields:
        def __init__(self, **kwargs):
            self.kw = kwargs

        @classmethod
        def construct(cls, **kwargs):
            return cls(**kwargs)

    parsed2 = sb._parse_with_type_annotation({"y": 9}, PydV1NoFields)
    assert isinstance(parsed2, PydV1NoFields)
    assert parsed2.kw == {"y": 9}


def test_dataclass_and_regular_class_handling(sandbox_module):
    sb = sandbox_module

    @dataclasses.dataclass
    class DC:
        a: int
        b: str

    data = {"a": 1, "b": "two"}
    dc = sb._parse_with_type_annotation(data, DC)
    assert isinstance(dc, DC)
    assert dc.a == 1 and dc.b == "two"

    # Regular class that accepts kwargs
    class Good:
        def __init__(self, **kwargs):
            self.kw = kwargs

    obj = sb._parse_with_type_annotation({"one": 1}, Good)
    assert isinstance(obj, Good) and obj.kw == {"one": 1}

    # Regular class that raises on init should result in function returning the original data
    class Bad:
        def __init__(self, **kwargs):
            raise RuntimeError("bad init")

    res = sb._parse_with_type_annotation({"k": "v"}, Bad)
    # Since constructor raised, parsing falls through to returning the original data
    assert res == {"k": "v"}
