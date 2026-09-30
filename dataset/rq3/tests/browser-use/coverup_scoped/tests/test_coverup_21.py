# file: browser_use/tools/registry/service.py:74-271
# asked: {"lines": [120, 122, 182, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 224, 226, 227, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 243, 248, 249, 251, 257], "branches": [[119, 120], [181, 182], [192, 191], [194, 199], [207, 226], [210, 211], [211, 212], [211, 213], [213, 214], [213, 215], [215, 216], [215, 217], [217, 218], [217, 219], [219, 220], [219, 221], [221, 222], [221, 224], [226, 227], [226, 230], [230, 231], [230, 232], [232, 233], [232, 234], [234, 235], [234, 236], [236, 237], [236, 238], [238, 239], [238, 240], [240, 241], [240, 243], [246, 248], [248, 249], [248, 251], [254, 257]]}
# gained: {"lines": [120, 122, 182, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 226, 227, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 248, 251, 257], "branches": [[119, 120], [181, 182], [192, 191], [194, 199], [207, 226], [210, 211], [211, 212], [211, 213], [213, 214], [213, 215], [215, 216], [215, 217], [217, 218], [217, 219], [219, 220], [226, 227], [226, 230], [230, 231], [230, 232], [232, 233], [232, 234], [234, 235], [234, 236], [236, 237], [236, 238], [238, 239], [246, 248], [248, 251], [254, 257]]}

import asyncio
import inspect
from inspect import Parameter
from typing import Optional

import pytest
from pydantic import create_model

from browser_use.tools.registry.service import Registry
from browser_use.tools.registry.views import ActionModel


class DummySelf:
    def __init__(self, special_map):
        self._special = special_map

    def _get_special_param_types(self):
        return self._special


@pytest.mark.asyncio
async def test_optional_union_special_param_and_to_thread(monkeypatch):
    # Special param 's' annotated as Optional[list], expected_type is list -> Union handling branch
    dummy = DummySelf({'s': list})

    called = {}

    # sync function to force asyncio.to_thread path (line 257)
    def action(s: Optional[list]):
        called['val'] = s
        return "result-sync"

    wrapped, param_model = Registry._normalize_action_function_signature(dummy, action, "desc")
    # call wrapped with special param provided; should call sync func via to_thread and set called['val']
    res = await wrapped(params=None, s=[1, 2, 3])
    assert res == "result-sync"
    assert called['val'] == [1, 2, 3]
    # Ensure param_model was constructed (should be empty ActionModel-derived)
    assert hasattr(param_model, "__name__")


@pytest.mark.asyncio
async def test_param_model_provided_missing_params_raises():
    # When param_model is provided and first parameter is not special, missing params should raise (line 182)
    dummy = DummySelf({})  # no special params

    async def f(p):
        return p

    # create an explicit param_model to indicate Type 1 pattern
    ProvidedModel = create_model("ProvidedModel", __base__=ActionModel, p=(int, ...))
    wrapped, _ = Registry._normalize_action_function_signature(dummy, f, "desc", param_model=ProvidedModel)

    with pytest.raises(ValueError) as exc:
        await wrapped()  # not passing params -> should raise
    assert "missing required 'params' argument" in str(exc.value)


@pytest.mark.asyncio
async def test_action_params_unpacked_from_kwargs_and_params_model_dump():
    # Test Type 2: action params unpacked from kwargs into generated param_model (lines 191-199)
    dummy = DummySelf({})  # no special params

    async def f(x: int, y: int):
        return x, y

    wrapped, param_model = Registry._normalize_action_function_signature(dummy, f, "desc")
    # Provide kwargs only; wrapper should create param_model from kwargs and call async function
    result = await wrapped(x=7, y=8)
    assert result == (7, 8)

    # Also verify params.model_dump() path by explicitly constructing params and passing it
    params_instance = param_model(x=3, y=4)
    result2 = await wrapped(params=params_instance)
    assert result2 == (3, 4)


@pytest.mark.asyncio
@pytest.mark.parametrize("name, expected_msg", [
    ("browser_session", "requires browser_session"),
    ("page_extraction_llm", "requires page_extraction_llm"),
    ("file_system", "requires file_system"),
    ("page", "requires page"),
    ("available_file_paths", "requires available_file_paths"),
])
async def test_special_param_none_raises_specific_messages(name, expected_msg):
    # For special parameters with no default: when provided as None should raise the specific message (lines 210-224)
    dummy = DummySelf({name: object})

    async def f(**kwargs):
        # define explicit parameter to appear in signature, using the given special name
        # create a dummy function matching signature dynamically
        return "ok"

    # Build a function dynamically with the special parameter name to ensure correct signature
    src = f"async def func({name}):\n    return {name}"
    local = {}
    exec(src, {}, local)
    func = local["func"]

    wrapped, _ = Registry._normalize_action_function_signature(dummy, func, "desc")

    # Case A: parameter provided explicitly as None -> triggers first block raising specific error
    with pytest.raises(ValueError) as excinfo:
        await wrapped(**{name: None})
    assert expected_msg in str(excinfo.value)

    # Case B: parameter omitted entirely -> should raise same specific error when required (lines 226-243)
    with pytest.raises(ValueError) as excinfo2:
        await wrapped()  # not providing the special param
    assert expected_msg in str(excinfo2.value)


@pytest.mark.asyncio
async def test_special_param_with_default_is_used_when_not_provided(monkeypatch):
    # When special param has a default it should be used (lines 226-227)
    dummy = DummySelf({'page': object})

    # create function with default for special param
    async def func(page='default_value'):
        return page

    wrapped, _ = Registry._normalize_action_function_signature(dummy, func, "desc")

    # Not providing 'page' should result in default being passed to original function
    res = await wrapped()
    assert res == 'default_value'


@pytest.mark.asyncio
async def test_missing_required_action_parameter_raises():
    # Ensure missing required action parameter raises (lines 248-251)
    dummy = DummySelf({})  # no special params

    async def action(req):
        return req

    wrapped, _ = Registry._normalize_action_function_signature(dummy, action, "desc")
    # Call without params/kwargs -> missing required action parameter should raise
    with pytest.raises(ValueError) as exc:
        await wrapped()
    assert "missing required parameter 'req'" in str(exc.value)
