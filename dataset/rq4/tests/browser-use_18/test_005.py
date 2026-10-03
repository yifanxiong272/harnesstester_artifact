import pytest
from types import SimpleNamespace
from typing import Tuple
from pydantic import BaseModel

from browser_use.controller.registry.service import Registry

@pytest.mark.asyncio
async def test_probe_001_tuple_placeholder_replaced_and_type_preserved():
    """Probe: when a param model has a tuple[str, ...] containing a '<secret>KEY</secret>' placeholder,
    Registry.execute_action with sensitive_data={'KEY': 'VAL'} should substitute the placeholder inside the
    tuple element and preserve the tuple container type.

    This test exercises the public entrypoint Registry.execute_action and does not import or call
    the private _replace_sensitive_data directly.
    """

    class TupleModel(BaseModel):
        field: Tuple[str, ...]

    # Action function annotated to accept the pydantic model as first parameter so
    # execute_action's is_pydantic path is taken and the validated model (possibly modified)
    # is passed directly to this function.
    async def action_fn(params: TupleModel):
        # Return the field so the test can observe both value and type
        return params.field

    registry = Registry()

    # Register the action deterministically using a simple namespace object with the
    # attributes the Registry expects: function and param_model
    registry.registry.actions["tuplify"] = SimpleNamespace(
        function=action_fn,
        param_model=TupleModel,
        description="test tuple substitution",
    )

    # Input: tuple containing a placeholder that should be replaced
    input_params = {"field": ("<secret>KEY</secret>",)}

    # Invoke the public entrypoint with no browser and with the sensitive mapping
    result = await registry.execute_action(
        "tuplify",
        input_params,
        browser=None,
        sensitive_data={"KEY": "VAL"},
    )

    # Primary behavioral oracle (conservative): the returned field must be a tuple
    # and its element must have been substituted from the sensitive_data mapping.
    assert isinstance(result, tuple), f"expected tuple container preserved, got {type(result)!r}"
    assert result == ("VAL",), f"expected tuple element substituted to ('VAL',), got {result!r}"
