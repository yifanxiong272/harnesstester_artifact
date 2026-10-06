import pytest
from types import SimpleNamespace
from pydantic import BaseModel

from browser_use.controller.registry.service import Registry

@pytest.mark.asyncio
async def test_probe_001():
    # Setup: real Registry and a deterministic ParamModel with a tuple field
    registry = Registry()

    class ParamModel(BaseModel):
        my_tuple: tuple[str, ...]

    # Capture the params object actually passed into the registered action
    received = {}

    async def action_fn(params: ParamModel):
        # record the received pydantic model instance for external observation
        received['params'] = params
        return 'ok'

    # Register the action with the Registry internals as the public API expects
    registry.registry.actions['test_action'] = SimpleNamespace(
        function=action_fn,
        param_model=ParamModel,
        description='test',
    )

    # Deterministic params: tuple containing a secret placeholder
    params = {'my_tuple': ('<secret>KEY</secret>',)}

    # Act: invoke the public entrypoint with sensitive_data mapping
    result = await registry.execute_action(
        'test_action',
        params=params,
        sensitive_data={'KEY': 'REPLACED'},
    )

    # Basic sanity: action returned and was called
    assert result == 'ok'
    assert 'params' in received, 'registered action was not invoked with params'

    observed = received['params']

    # Primary behavioral oracle (conservative public assertion):
    # The tuple container type must be preserved and its string element substituted.
    assert isinstance(observed.my_tuple, tuple), (
        f'Expected tuple type preserved for field my_tuple, got {type(observed.my_tuple)}'
    )
    assert observed.my_tuple[0] == 'REPLACED', (
        f'Expected secret placeholder substituted to "REPLACED", got {observed.my_tuple[0]!r}'
    )
