import asyncio
from types import SimpleNamespace
import pytest

from browser_use.agent.service import Agent

# Two tests target different branches of Agent._execute_history_step
# - test_execute_history_step_extract_round_014: exercises non-extract then extract flow
#   verifying pending actions are flushed via multi_act and AI extract result appended.
# - test_execute_history_step_missing_element_round_014: simulates _update_action_indices
#   returning None to trigger the diagnostic ValueError about missing matching element.

@pytest.mark.asyncio
async def test_execute_history_step_extract_round_014():
    """Verify that when a non-extract action is followed by an extract action,
    pending actions are executed via multi_act and the AI extract result is appended.
    """
    method = Agent._execute_history_step

    async def get_browser_state_summary(include_screenshot=False):
        # Provide a truthy state with an empty selector_map to keep flow simple
        return SimpleNamespace(dom_state=SimpleNamespace(selector_map={}))

    async def fake_execute_ai_step(query, include_screenshot, extract_links, ai_step_llm):
        return {'ai': 'result', 'query': query, 'extract_links': extract_links}

    async def fake_update_action_indices(historical_elem, action, state):
        # Simulate a successful update producing an actionable item
        return {'updated': True, 'orig': action}

    async def fake_multi_act(actions):
        # Return a synthetic batch result for pending actions
        return [{'batch': 'ok', 'count': len(actions)}]

    # Build a fake self with required attributes and async methods
    fake_self = SimpleNamespace()
    fake_self.browser_session = SimpleNamespace(get_browser_state_summary=get_browser_state_summary)
    fake_self._execute_ai_step = fake_execute_ai_step
    fake_self._update_action_indices = fake_update_action_indices
    fake_self.multi_act = fake_multi_act
    fake_self._count_expected_elements_from_history = lambda history_item: 0
    fake_self._wait_for_minimum_elements = lambda *a, **k: asyncio.sleep(0)
    fake_self._format_element_for_error = lambda e: 'ELEMENT'
    fake_self.logger = SimpleNamespace(info=lambda *a, **k: None)

    # Two actions: first is a non-extract (e.g., click), second is extract
    action_click = SimpleNamespace(model_dump=lambda exclude_unset=True: {'click': {'selector': 'x'}})
    action_extract = SimpleNamespace(model_dump=lambda exclude_unset=True: {'extract': {'query': 'find me', 'extract_links': False}})

    history_item = SimpleNamespace(
        model_output=SimpleNamespace(action=[action_click, action_extract]),
        state=SimpleNamespace(interacted_element=[SimpleNamespace(node_name='DIV', attributes={'aria-label': 'lbl'})])
    )

    # Call the method under test
    results = await method(fake_self, history_item, delay=0, ai_step_llm=None, wait_for_elements=False)

    # Oracle: first batch result from multi_act then AI extract result
    assert isinstance(results, list)
    assert len(results) == 2
    assert results[0] == {'batch': 'ok', 'count': 1}
    assert results[1]['ai'] == 'result'
    assert results[1]['query'] == 'find me'


@pytest.mark.asyncio
async def test_execute_history_step_missing_element_round_014():
    """When _update_action_indices returns None, a ValueError is raised with
    a diagnostic message indicating the element could not be found.
    """
    method = Agent._execute_history_step

    async def get_browser_state_summary(include_screenshot=False):
        # Provide dom_state with selector_map that does not match the historical element
        # to force the diagnostic path.
        # Map has one element with node_name 'span' so it won't match a historical 'button'
        selector_map = {
            1: SimpleNamespace(node_name='SPAN', attributes={}),
            2: SimpleNamespace(node_name='DIV', attributes={}),
        }
        return SimpleNamespace(dom_state=SimpleNamespace(selector_map=selector_map))

    async def fake_update_action_indices(historical_elem, action, state):
        # Simulate inability to map historical indexes to current page -> return None
        return None

    # Minimal fake self
    fake_self = SimpleNamespace()
    fake_self.browser_session = SimpleNamespace(get_browser_state_summary=get_browser_state_summary)
    fake_self._update_action_indices = fake_update_action_indices
    fake_self._format_element_for_error = lambda e: 'HIST_ELEM_INFO'
    fake_self.logger = SimpleNamespace(info=lambda *a, **k: None)
    fake_self._count_expected_elements_from_history = lambda history_item: 0
    fake_self._wait_for_minimum_elements = lambda *a, **k: asyncio.sleep(0)

    # One click action expecting an interacted element
    action_click = SimpleNamespace(model_dump=lambda exclude_unset=True: {'click': {'selector': 'x'}})
    historical_elem = SimpleNamespace(node_name='BUTTON', attributes={'aria-label': 'btn'})

    history_item = SimpleNamespace(
        model_output=SimpleNamespace(action=[action_click]),
        state=SimpleNamespace(interacted_element=[historical_elem])
    )

    with pytest.raises(ValueError) as exc:
        await method(fake_self, history_item, delay=0, ai_step_llm=None, wait_for_elements=False)

    msg = str(exc.value)
    # Oracle assertions: error mentions inability to find matching element and the action index
    assert 'Could not find matching element for action 0' in msg
    assert 'Page has' in msg
