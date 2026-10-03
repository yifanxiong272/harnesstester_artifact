from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from browser_use.controller.registry.service import Registry


class TupleParamModel(BaseModel):
    items: tuple[str, ...]


@pytest.mark.asyncio
async def test_probe_001():
    """Detect whether placeholders inside tuple elements are substituted before action invocation.

    Activation steps (deterministic):
    - Create Registry
    - Register an action whose param_model has a tuple[str, ...] field
    - Call execute_action with params containing a tuple element '<secret>KEY</secret>' and sensitive_data {'KEY': 'REPLACED'}
    - Observe the arguments with which the action function was awaited
    """
    registry = Registry()

    # Prepare the AsyncMock action that will record how it was called
    action_mock = AsyncMock()

    # Register action in the registry in the same pattern used by existing tests
    registry.registry.actions['probe_action'] = MagicMock(
        function=action_mock,
        param_model=TupleParamModel,
        description='probe action for tuple substitution',
    )

    # Deterministic params: tuple containing the secret placeholder string
    params = {'items': ('<secret>KEY</secret>',)}

    # Invoke via public entrypoint; exercise the substitution path with sensitive_data
    await registry.execute_action('probe_action', params=params, sensitive_data={'KEY': 'REPLACED'})

    # Observable: the action must have been awaited once
    action_mock.assert_awaited_once()

    # Inspect the arguments with which the action was called
    call_args = action_mock.call_args
    # call_args is a (args, kwargs) pair; expect invocation via kwargs (common in this codebase)
    _, kwargs = call_args
    assert 'items' in kwargs, "expected 'items' kwarg passed to action"
    received_items = kwargs['items']
    assert isinstance(received_items, tuple), 'expected items to be a tuple'

    # PRIMARY ORACLE: tuple element should have been replaced by sensitive_data
    assert received_items[0] == 'REPLACED', (
        "Expected placeholder inside tuple element to be substituted with 'REPLACED', "
        f"but got: {received_items[0]!r}"
    )
