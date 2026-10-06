import pytest
from pydantic import BaseModel
from typing import Tuple, Optional, Dict
from types import SimpleNamespace

from browser_use.controller.registry.service import Registry


@pytest.mark.asyncio
async def test_probe_001():
    """Probe: placeholders inside tuple elements should be replaced and tuple type preserved.

    This test registers an action whose param_model has a Tuple[str, str] field and an async
    action function that records the received model. It then calls Registry.execute_action with
    sensitive_data mapping 'KEY' -> 'SECRET_VALUE' and params containing ('<secret>KEY</secret>', 'UNCHANGED').

    Oracle: the action receives a model where .items is a tuple and equals ('SECRET_VALUE', 'UNCHANGED').
    """

    # Prepare Registry and ensure the underlying registry.actions mapping exists
    registry = Registry()
    if not hasattr(registry, 'registry') or not hasattr(registry.registry, 'actions'):
        registry.registry = SimpleNamespace(actions={})

    # Deterministic Pydantic model with a tuple field (two fixed elements)
    class TupleParam(BaseModel):
        items: Tuple[str, str]

    # Capture container for the invoked parameter
    received: Dict[str, Optional[TupleParam]] = {'param': None}

    # Action function must be an async function annotated to accept the Pydantic model
    async def capture_action(param: TupleParam):
        # Record the received model instance (do not mutate)
        received['param'] = param
        return 'ok'

    # Register the action in the registry mapping the execute_action path will consult
    registry.registry.actions['probe_action'] = SimpleNamespace(
        function=capture_action,
        param_model=TupleParam,
        description='probe tuple secret replacement'
    )

    # Call execute_action with a tuple containing a secret placeholder
    result = await registry.execute_action(
        'probe_action',
        params={'items': ('<secret>KEY</secret>', 'UNCHANGED')},
        sensitive_data={'KEY': 'SECRET_VALUE'}
    )

    # Primary observable: the action was invoked and the model received is available
    assert received['param'] is not None, 'The registered action was not invoked'
    received_param = received['param']

    # Assert: tuple type preserved and placeholder substituted
    assert isinstance(received_param.items, tuple), (
        f"Invariant violated: expected tuple type preserved for .items, got {type(received_param.items)!r}"
    )
    assert received_param.items == ('SECRET_VALUE', 'UNCHANGED'), (
        f"Placeholder substitution incorrect or ordering changed: got {received_param.items!r}"
    )
