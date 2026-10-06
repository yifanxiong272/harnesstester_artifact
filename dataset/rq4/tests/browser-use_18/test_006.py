import pytest
from types import SimpleNamespace
from pydantic import BaseModel
from browser_use.controller.registry.service import Registry

@ pytest.mark.asyncio
async def test_probe_001_replace_secret_inside_set_elements():
    """
    Probe: When execute_action is called with a params model that contains a set
    element holding a '<secret>KEY</secret>' placeholder and sensitive_data
    supplies KEY -> 'REPLACED', the placeholder should be replaced in the
    element reachable from params.model_dump(). The public observable is the
    action return value (the tags collection) which must contain 'REPLACED'
    and must not contain the placeholder.
    """

    # Local deterministic Param model with a set field
    class TagsModel(BaseModel):
        tags: set[str]

    # Async action that accepts a Pydantic model and returns the tags field
    async def capture_action(params: TagsModel):
        # Return the raw tags container so execute_action's result reveals what
        # the registry saw after _replace_sensitive_data ran.
        return params.tags

    # Prepare a Registry instance and register the action deterministically
    registry = Registry()
    # Ensure registry.registry.actions exists and is a simple mutable mapping
    registry.registry = SimpleNamespace(actions={})

    # Register the action shape expected by execute_action
    registry.registry.actions['test_action'] = SimpleNamespace(
        function=capture_action,
        param_model=TagsModel,
    )

    # Input params: a set containing the placeholder string
    params = {'tags': {'<secret>KEY</secret>'}}
    sensitive_data = {'KEY': 'REPLACED'}

    # Invoke the public entrypoint. This goes through execute_action -> _replace_sensitive_data
    result = await registry.execute_action('test_action', params, sensitive_data=sensitive_data)

    # Normalize result into a set for deterministic assertions (handles list/set returned differences)
    returned_items = set(result)

    # Primary oracle: placeholder must have been substituted with the sensitive value
    assert 'REPLACED' in returned_items and '<secret>KEY</secret>' not in returned_items, (
        f"Expected placeholder to be replaced inside set element, got: {returned_items}"
    )
