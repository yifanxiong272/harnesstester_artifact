import asyncio
import types

import pytest

import browser_use.agent.service as service

# Helper mocks that match the minimal shapes expected by _execute_history_step
class MockAction:
    def __init__(self, dump_dict):
        self._dump = dump_dict

    def model_dump(self, exclude_unset=True):
        return self._dump


class MockHistoricalElement:
    def __init__(self, node_name, attributes=None):
        self.node_name = node_name
        self.attributes = attributes or {}


class MockState:
    def __init__(self, interacted_element):
        self.interacted_element = interacted_element


class MockDOMState:
    def __init__(self, selector_map):
        self.selector_map = selector_map


class MockBrowserStateSummary:
    def __init__(self, dom_state):
        self.dom_state = dom_state


class MockBrowserSession:
    def __init__(self, state_return=None):
        # state_return may be an awaitable or value; we implement as async def
        self._state_return = state_return

    async def get_browser_state_summary(self, include_screenshot=False):
        # Simulate an async browser call
        return self._state_return


class MockHistoryOutput:
    def __init__(self, actions):
        # actions is a list of MockAction
        self.action = actions


class MockHistoryItem:
    def __init__(self, model_output, state):
        self.model_output = model_output
        self.state = state


# Utility to bind the unbound async function to a fake self
def bound_execute(fake_self):
    return types.MethodType(service.Agent._execute_history_step, fake_self)


def run_coro(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_invalid_state_raises_value_error_round_013():
    # Setup: browser_session returns None -> should raise ValueError('Invalid state or model output')
    fake_self = types.SimpleNamespace()
    fake_self.browser_session = MockBrowserSession(state_return=None)

    # Provide a model_output that is truthy so the error is caused by state being falsy
    actions = []
    model_output = MockHistoryOutput(actions)
    history_item = MockHistoryItem(model_output=model_output, state=MockState([]))

    # Bind and run
    func = bound_execute(fake_self)

    with pytest.raises(ValueError) as exc:
        run_coro(func(history_item, 0, None, wait_for_elements=False))

    assert 'Invalid state or model output' in str(exc.value)


def test_extract_action_calls_ai_step_and_returns_result_round_013():
    # Setup: state is present; model_output contains a single extract action
    # Capture the parameters passed to _execute_ai_step
    captured = {}

    async def fake_execute_ai_step(query, include_screenshot, extract_links, ai_step_llm):
        captured['query'] = query
        captured['include_screenshot'] = include_screenshot
        captured['extract_links'] = extract_links
        captured['ai_step_llm'] = ai_step_llm
        return {'ai_result': 'ok', 'query': query, 'extract_links': extract_links}

    fake_self = types.SimpleNamespace()
    # Provide a truthy browser state summary so code continues
    dom = MockDOMState(selector_map={})
    fake_state_summary = MockBrowserStateSummary(dom_state=dom)
    fake_self.browser_session = MockBrowserSession(state_return=fake_state_summary)

    # Attach the fake async AI step
    fake_self._execute_ai_step = fake_execute_ai_step
    fake_self._update_action_indices = None
    fake_self.multi_act = None
    fake_self._count_expected_elements_from_history = lambda hi: 0
    fake_self._wait_for_minimum_elements = None

    # Build a history item containing an extract action
    extract_action = MockAction({'extract': {'query': 'find me', 'extract_links': True}})
    model_output = MockHistoryOutput([extract_action])
    history_item = MockHistoryItem(model_output=model_output, state=MockState([]))

    func = bound_execute(fake_self)
    result = run_coro(func(history_item, 0, None, wait_for_elements=False))

    # Should return a list with the ai_result dict we returned from fake_execute_ai_step
    assert isinstance(result, list)
    assert result == [{'ai_result': 'ok', 'query': 'find me', 'extract_links': True}]

    # Also validate the internal call used the intended flags
    assert captured['include_screenshot'] is False
    assert captured['query'] == 'find me'
    assert captured['extract_links'] is True


def test_non_extract_action_missing_element_builds_diagnostic_and_raises_round_013():
    # Setup: browser state has selector_map with elements that match node_name and include aria-label,
    # so diagnostic should contain 'Available <NODE>' and aria-label snippet
    hist_elem = MockHistoricalElement('button', attributes={'id': 'hist', 'aria-label': 'the-historical'})
    history_state = MockState([hist_elem])

    # Create selector_map with one element that will be detected as similar
    selector_elem = MockHistoricalElement('button', attributes={'aria-label': 'matching-aria-label-value'})
    dom = MockDOMState(selector_map={1: selector_elem, 2: MockHistoricalElement('div', attributes={})})
    fake_state_summary = MockBrowserStateSummary(dom_state=dom)

    fake_self = types.SimpleNamespace()
    fake_self.browser_session = MockBrowserSession(state_return=fake_state_summary)

    # Make _update_action_indices return None to trigger diagnostic and raise
    async def fake_update_action_indices(historical_elem, action, state):
        return None

    fake_self._update_action_indices = fake_update_action_indices
    fake_self._count_expected_elements_from_history = lambda hi: 0
    fake_self._wait_for_minimum_elements = None
    fake_self.multi_act = None

    # Single click action (non-extract)
    click_action = MockAction({'click': {'some': 'params'}})
    model_output = MockHistoryOutput([click_action])
    history_item = MockHistoryItem(model_output=model_output, state=history_state)

    func = bound_execute(fake_self)

    with pytest.raises(ValueError) as exc:
        run_coro(func(history_item, 0, None, wait_for_elements=False))

    msg = str(exc.value)
    # Ensure diagnostic contains the expected fragments
    assert 'Could not find matching element for action 0' in msg
    assert 'Page has' in msg
    # Our diagnostic should include the AVAILABLE node snippet and the aria-label
    assert 'Available <BUTTON>' in msg or 'Found' in msg
    assert 'matching-aria-label-value' in msg
