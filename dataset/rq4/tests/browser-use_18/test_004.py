import pytest
from types import SimpleNamespace
from pydantic import BaseModel

from browser_use.controller.registry.service import Registry

@pytest.mark.asyncio
async def test_probe_001_tuple_element_substitution_and_type_preservation():
    """Probe: placeholders inside tuple elements should be substituted and tuple type preserved when executed via Registry.execute_action.

    Activation:
    - Register an action whose first parameter is a Pydantic model with a tuple field.
    - Provide params where the tuple contains the string '<secret>MYKEY</secret>'.
    - Call execute_action with sensitive_data={'MYKEY': 'REPLACED'} and observe the actual argument received by the action.
    """

    captured = []

    class TestModel(BaseModel):
        my_tuple: tuple[str, ...]

    async def action_fn(model_arg: TestModel):
        # record the actual runtime argument received by execute_action
        captured.append(model_arg)
        return "done"

    registry = Registry()

    # Register the action in the registry in the same shape the code expects
    registry.registry.actions['probe_action'] = SimpleNamespace(
        function=action_fn,
        param_model=TestModel,
        description='probe tuple substitution',
    )

    # Call the public entrypoint which uses _replace_sensitive_data internally
    await registry.execute_action(
        'probe_action',
        params={'my_tuple': ('<secret>MYKEY</secret>',)},
        sensitive_data={'MYKEY': 'REPLACED'},
    )

    # Observable assertions (primary oracle): action invoked and received tuple value substituted and type preserved
    assert len(captured) == 1, f"expected action to be invoked once, got {len(captured)}"
    received = captured[0]

    # Conservative public invariant assertion per boundary plan
    assert isinstance(received.my_tuple, tuple), f"expected tuple type preserved, got {type(received.my_tuple)!r}"
    assert received.my_tuple == ('REPLACED',), f"expected tuple element substituted to 'REPLACED', got {received.my_tuple!r}"
