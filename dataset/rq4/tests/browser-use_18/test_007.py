import pytest
from types import SimpleNamespace
from pydantic import BaseModel

from browser_use.controller.registry.service import Registry

@pytest.mark.asyncio
async def test_probe_001():
    """Probe: tuple-typed BaseModel fields should preserve tuple type and substitute secret placeholders.

    This test registers an async action 'test_tuples' whose first parameter is a Pydantic model
    with a tuple[str, ...] field. It calls Registry.execute_action with a params dict that
    contains the placeholder '<secret>KEY</secret>' inside the tuple and sensitive_data that
    maps KEY -> 'REPLACED'. After execute_action returns, the action-captured validated model
    is inspected to assert that the tuple type is preserved and the element has been replaced.
    """

    # Deterministic param model with a tuple field
    class ParamModel(BaseModel):
        items: tuple[str, ...]

    # Capture the validated/possibly-mutated model instance passed into the action
    captured = []

    async def action_fn(model: ParamModel):
        # Store the exact object instance we receive for later assertions
        captured.append(model)
        return None

    # Prepare Registry and its internal action mapping deterministically
    registry = Registry()
    # The Registry instance exposes an attribute 'registry' that holds .actions
    registry.registry = SimpleNamespace(actions={})

    # Register the action with the required attributes used by execute_action
    registry.registry.actions['test_tuples'] = SimpleNamespace(
        function=action_fn,
        param_model=ParamModel,
        description='test tuple substitution'
    )

    # Call execute_action with params containing a tuple with the secret placeholder
    await registry.execute_action(
        action_name='test_tuples',
        params={'items': ('<secret>KEY</secret>',)},
        sensitive_data={'KEY': 'REPLACED'}
    )

    # Ensure the action was invoked and the model was captured
    assert captured, "action was not invoked or model not captured"
    model = captured[0]

    # Primary oracle: the field must remain a tuple and its element must be substituted
    assert isinstance(model.items, tuple), f"expected tuple type for 'items', got {type(model.items)}"
    assert model.items[0] == 'REPLACED', f"expected substituted element 'REPLACED', got {model.items[0]}"
