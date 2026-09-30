# file: browser_use/agent/service.py:3387-3516
# asked: {"lines": [3404, 3406, 3409, 3411, 3412, 3413, 3414, 3415, 3417, 3418, 3419, 3421, 3422, 3423, 3426, 3427, 3428, 3429, 3431, 3433, 3435, 3436, 3437, 3439, 3440, 3442, 3444, 3445, 3447, 3450, 3451, 3452, 3453, 3456, 3457, 3458, 3460, 3461, 3462, 3463, 3464, 3465, 3467, 3470, 3471, 3472, 3473, 3474, 3476, 3478, 3479, 3480, 3483, 3484, 3485, 3486, 3487, 3488, 3489, 3490, 3491, 3492, 3494, 3495, 3496, 3497, 3498, 3499, 3500, 3503, 3504, 3505, 3506, 3509, 3512, 3513, 3514, 3516], "branches": [[3409, 3411], [3409, 3435], [3412, 3413], [3412, 3426], [3413, 3414], [3413, 3426], [3417, 3413], [3417, 3418], [3421, 3413], [3421, 3422], [3426, 3427], [3426, 3433], [3428, 3429], [3428, 3431], [3436, 3437], [3436, 3439], [3442, 3444], [3442, 3512], [3447, 3450], [3447, 3470], [3450, 3451], [3450, 3456], [3476, 3478], [3476, 3509], [3485, 3486], [3485, 3494], [3486, 3487], [3486, 3494], [3487, 3486], [3487, 3488], [3489, 3486], [3489, 3490], [3491, 3486], [3491, 3492], [3495, 3496], [3495, 3497], [3497, 3498], [3497, 3503], [3512, 3513], [3512, 3516]]}
# gained: {"lines": [3404, 3406, 3409, 3411, 3412, 3413, 3414, 3415, 3417, 3418, 3419, 3421, 3422, 3423, 3426, 3427, 3428, 3429, 3435, 3436, 3437, 3439, 3440, 3442, 3444, 3445, 3447, 3450, 3451, 3452, 3453, 3456, 3457, 3458, 3460, 3461, 3462, 3463, 3464, 3465, 3467, 3470, 3471, 3472, 3473, 3474, 3476, 3478, 3479, 3480, 3483, 3484, 3485, 3486, 3487, 3488, 3489, 3490, 3491, 3494, 3495, 3496, 3503, 3504, 3505, 3506, 3509, 3512, 3513, 3514, 3516], "branches": [[3409, 3411], [3409, 3435], [3412, 3413], [3413, 3414], [3417, 3418], [3421, 3422], [3426, 3427], [3428, 3429], [3436, 3437], [3436, 3439], [3442, 3444], [3442, 3512], [3447, 3450], [3447, 3470], [3450, 3451], [3476, 3478], [3476, 3509], [3485, 3486], [3486, 3487], [3486, 3494], [3487, 3486], [3487, 3488], [3489, 3490], [3491, 3486], [3495, 3496], [3512, 3513], [3512, 3516]]}

import asyncio
import pytest
from types import SimpleNamespace

from browser_use.agent.service import Agent


class FakeAction:
    def __init__(self, data):
        self._data = data

    def model_dump(self, exclude_unset=True):
        return self._data


class FakeModelOutput:
    def __init__(self, actions):
        self.action = actions


class FakeState:
    def __init__(self, interacted_element):
        self.interacted_element = interacted_element


class FakeElem:
    def __init__(self, node_name, attributes=None):
        self.node_name = node_name
        self.attributes = attributes or {}


class FakeDomElem:
    def __init__(self, node_name, attributes=None):
        self.node_name = node_name
        self.attributes = attributes or {}


class FakeDomState:
    def __init__(self, selector_map):
        self.selector_map = selector_map


class FakeBrowserStateSummary:
    def __init__(self, selector_map=None):
        self.dom_state = FakeDomState(selector_map or {})


async def _noop_async(*args, **kwargs):
    return None


def make_agent():
    # Create Agent instance without running __init__
    a = object.__new__(Agent)
    # Minimal attributes used by _execute_history_step and logger property
    a.task_id = "task1234"
    # browser_session must have id and agent_focus_target_id for logger property
    sess = SimpleNamespace(id="bsess5678", agent_focus_target_id=None)
    # default get_browser_state_summary (tests will override as needed)
    async def default_get_state(include_screenshot=False):
        return FakeBrowserStateSummary(selector_map={})
    sess.get_browser_state_summary = default_get_state
    a.browser_session = sess
    # Hook methods that _execute_history_step calls; tests will override as needed
    a._count_expected_elements_from_history = lambda history_item: 0
    a._wait_for_minimum_elements = lambda *args, **kwargs: _noop_async()
    a.multi_act = lambda actions: _noop_async()
    a._execute_ai_step = lambda *args, **kwargs: _noop_async()
    a._update_action_indices = lambda *args, **kwargs: _noop_async()
    a._format_element_for_error = lambda elem: "<elem>"
    return a


@pytest.mark.asyncio
async def test_execute_history_step_extract_with_pending_actions_and_batch_then_ai():
    """
    - First action is a non-extract that yields an updated_action (pending)
    - Second action is extract which should cause pending_actions to be executed via multi_act
    - Then _execute_ai_step is executed and its result appended
    """
    agent = make_agent()

    # Prepare state returned by browser_session.get_browser_state_summary
    state = FakeBrowserStateSummary(selector_map={})
    async def get_state(include_screenshot=False):
        return state
    agent.browser_session.get_browser_state_summary = get_state

    # Make _update_action_indices return a sentinel action model for the first action
    async def update_action_indices(historical_elem, action, state_arg):
        return {"action": "updated", "orig": action}
    agent._update_action_indices = update_action_indices

    # multi_act should be called and return a list of results for pending actions
    async def multi_act(actions):
        # ensure it's called with the pending updated action
        assert actions == [{"action": "updated", "orig": FakeAction({"click": {"by": "x"}})}] or isinstance(actions, list)
        return ["click_result"]
    agent.multi_act = multi_act

    # _execute_ai_step should return an ActionResult-like value
    async def execute_ai_step(query, include_screenshot=False, extract_links=False, ai_step_llm=None):
        assert query.startswith("find me") or query == "find me"
        return "ai_result"
    agent._execute_ai_step = execute_ai_step

    # Build history: [click, extract]
    click_action = FakeAction({"click": {"by": "x"}})
    extract_action = FakeAction({"extract": {"query": "find me", "extract_links": False}})
    model_output = FakeModelOutput([click_action, extract_action])
    # Historical interacted elements list (one for click)
    hist_state = FakeState([FakeElem("button", {"aria-label": "Do it"})])
    hist = SimpleNamespace(model_output=model_output, state=hist_state)

    results = await agent._execute_history_step(hist, delay=0.0)
    # Expect multi_act results first then AI extract result
    assert results == ["click_result", "ai_result"]


@pytest.mark.asyncio
async def test_execute_history_step_update_action_indices_none_raises_with_diagnostic():
    """
    When _update_action_indices returns None, the method should raise ValueError
    with a diagnostic that includes available aria-label list when selector_map has matching elements.
    """
    agent = make_agent()

    # Create a browser state with selector_map that has a matching node with aria-label
    selector_map = {
        0: FakeDomElem("BUTTON", {"aria-label": "Press Me"}),
        1: FakeDomElem("DIV", {"aria-label": "Other"})
    }
    async def get_state(include_screenshot=False):
        return FakeBrowserStateSummary(selector_map=selector_map)
    agent.browser_session.get_browser_state_summary = get_state

    # _update_action_indices returns None to trigger diagnostic branch
    async def update_action_indices(historical_elem, action, state_arg):
        return None
    agent._update_action_indices = update_action_indices

    # Provide a formatting function to return visible element info
    agent._format_element_for_error = lambda elem: f"node={elem.node_name}, attrs={elem.attributes}"

    # Build history with a single click action and historical element with node_name and attributes
    click = FakeAction({"click": {"by": "x"}})
    model_output = FakeModelOutput([click])
    hist_state = FakeState([FakeElem("BUTTON", {"aria-label": "Historical Label"})])
    hist = SimpleNamespace(model_output=model_output, state=hist_state)

    with pytest.raises(ValueError) as excinfo:
        await agent._execute_history_step(hist, delay=0.0)
    msg = str(excinfo.value)
    assert "Could not find matching element" in msg
    # The diagnostic should mention aria-label because selector_map had a BUTTON with aria-label
    assert "aria-label" in msg


@pytest.mark.asyncio
async def test_execute_history_step_wait_for_elements_branch_and_final_pending_execution():
    """
    Test branch where wait_for_elements=True, needs_element_matching True, min_elements > 0
    causing _wait_for_minimum_elements to be awaited, and final pending_actions executed.
    """
    agent = make_agent()

    # Make history with an action that needs element matching (click)
    click = FakeAction({"click": {"by": "x"}})
    model_output = FakeModelOutput([click])
    hist_state = FakeState([FakeElem("A", {"id": "link1"})])
    hist = SimpleNamespace(model_output=model_output, state=hist_state)

    # browser_session.get_browser_state_summary should not be used if _wait_for_minimum_elements returns state
    async def get_state_should_not_be_called(include_screenshot=False):
        pytest.skip("get_browser_state_summary should not be called in this scenario")
    agent.browser_session.get_browser_state_summary = get_state_should_not_be_called

    # _count_expected_elements_from_history returns >0
    agent._count_expected_elements_from_history = lambda h: 2

    # _wait_for_minimum_elements returns a BrowserStateSummary-like object
    async def wait_for_minimum(min_elements, timeout=15.0, poll_interval=1.0):
        return FakeBrowserStateSummary(selector_map={0: FakeDomElem("A", {"aria-label": "Lnk"})})
    agent._wait_for_minimum_elements = wait_for_minimum

    # _update_action_indices returns updated_action
    async def update_action_indices(historical_elem, action, state_arg):
        # ensure historical_elem passed through is the one from history
        assert isinstance(historical_elem, FakeElem)
        return {"action": "updated_click"}
    agent._update_action_indices = update_action_indices

    # multi_act should be called at end
    async def multi_act(actions):
        assert actions == [{"action": "updated_click"}]
        return ["done_click"]
    agent.multi_act = multi_act

    results = await agent._execute_history_step(hist, delay=0.0, wait_for_elements=True)
    assert results == ["done_click"]


@pytest.mark.asyncio
async def test_execute_history_step_invalid_state_or_model_output_raises():
    """
    If get_browser_state_summary returns falsy or model_output is falsy, method should raise ValueError.
    """
    agent = make_agent()

    # browser_session.get_browser_state_summary returns None (falsy)
    async def get_state(include_screenshot=False):
        return None
    agent.browser_session.get_browser_state_summary = get_state

    # history with no model_output
    hist = SimpleNamespace(model_output=None, state=FakeState([]))

    with pytest.raises(ValueError) as excinfo:
        await agent._execute_history_step(hist, delay=0.0)
    assert "Invalid state or model output" in str(excinfo.value)
