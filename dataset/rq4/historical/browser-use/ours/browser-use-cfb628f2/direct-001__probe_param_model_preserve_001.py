import pytest
from types import SimpleNamespace
from pydantic import BaseModel
from browser_use.controller.registry.service import Registry

class Nested(BaseModel):
    token: str

class Parent(BaseModel):
    child: Nested
    other: str

@pytest.mark.asyncio
async def test_probe_001():
    """Probe that execute_action constructs/validates param_model and preserves nested BaseModel types while replacing <secret>...</secret> placeholders."""
    # Capture the single argument passed to the action
    captured = {}

    # IMPORTANT: annotate the first parameter with Parent so execute_action
    # recognizes the action function as accepting a Pydantic model instance.
    async def action_fn(arg: Parent):
        captured['arg'] = arg

    # Prepare registry and register the action deterministically
    reg = Registry()
    # Replace internal registry container with a minimal stand-in having an actions mapping
    reg.registry = SimpleNamespace(actions={})
    # Register action: function + declared param_model
    reg.registry.actions['test_action'] = SimpleNamespace(function=action_fn, param_model=Parent)

    # Params contain a nested placeholder that should be replaced
    params = {
        'child': {'token': '<secret>token_name</secret>'},
        'other': 'value'
    }
    sensitive = {'token_name': 'REAL_TOKEN'}

    # Invoke the public entrypoint under test
    await reg.execute_action('test_action', params, sensitive_data=sensitive)

    # Primary behavioral oracle: action called with an instance of Parent, preserving Nested
    assert 'arg' in captured, 'registered action was not called'
    arg = captured['arg']
    assert isinstance(arg, Parent), f'expected Parent instance, got {type(arg)!r}'
    assert isinstance(arg.child, Nested), f'expected Nested instance for child, got {type(arg.child)!r}'
    assert arg.child.token == 'REAL_TOKEN', f"expected secret replaced with 'REAL_TOKEN', got {arg.child.token!r}"
