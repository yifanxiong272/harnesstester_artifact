# file: browser_use/agent/service.py:3387-3516
# asked: {"lines": [3404, 3406, 3409, 3411, 3412, 3413, 3414, 3415, 3417, 3418, 3419, 3421, 3422, 3423, 3426, 3427, 3428, 3429, 3431, 3433, 3435, 3436, 3437, 3439, 3440, 3442, 3444, 3445, 3447, 3450, 3451, 3452, 3453, 3456, 3457, 3458, 3460, 3461, 3462, 3463, 3464, 3465, 3467, 3470, 3471, 3472, 3473, 3474, 3476, 3478, 3479, 3480, 3483, 3484, 3485, 3486, 3487, 3488, 3489, 3490, 3491, 3492, 3494, 3495, 3496, 3497, 3498, 3499, 3500, 3503, 3504, 3505, 3506, 3509, 3512, 3513, 3514, 3516], "branches": [[3409, 3411], [3409, 3435], [3412, 3413], [3412, 3426], [3413, 3414], [3413, 3426], [3417, 3413], [3417, 3418], [3421, 3413], [3421, 3422], [3426, 3427], [3426, 3433], [3428, 3429], [3428, 3431], [3436, 3437], [3436, 3439], [3442, 3444], [3442, 3512], [3447, 3450], [3447, 3470], [3450, 3451], [3450, 3456], [3476, 3478], [3476, 3509], [3485, 3486], [3485, 3494], [3486, 3487], [3486, 3494], [3487, 3486], [3487, 3488], [3489, 3486], [3489, 3490], [3491, 3486], [3491, 3492], [3495, 3496], [3495, 3497], [3497, 3498], [3497, 3503], [3512, 3513], [3512, 3516]]}
# gained: {"lines": [3404, 3406, 3409, 3411, 3412, 3413, 3414, 3415, 3417, 3418, 3419, 3421, 3422, 3423, 3426, 3427, 3428, 3429, 3435, 3436, 3439, 3440, 3442, 3444, 3445, 3447, 3450, 3451, 3452, 3453, 3456, 3457, 3458, 3460, 3461, 3462, 3463, 3464, 3465, 3467, 3470, 3471, 3472, 3473, 3474, 3476, 3478, 3479, 3480, 3483, 3484, 3485, 3486, 3487, 3488, 3489, 3490, 3491, 3494, 3495, 3496, 3503, 3504, 3505, 3506, 3509, 3512, 3516], "branches": [[3409, 3411], [3409, 3435], [3412, 3413], [3413, 3414], [3417, 3418], [3421, 3422], [3426, 3427], [3428, 3429], [3436, 3439], [3442, 3444], [3442, 3512], [3447, 3450], [3447, 3470], [3450, 3451], [3476, 3478], [3476, 3509], [3485, 3486], [3486, 3487], [3486, 3494], [3487, 3486], [3487, 3488], [3489, 3490], [3491, 3486], [3495, 3496], [3512, 3516]]}

import asyncio
import pytest
from types import SimpleNamespace

from browser_use.agent.service import Agent


class FakeAction:
    def __init__(self, data):
        self._data = data

    def model_dump(self, exclude_unset=True):
        return self._data


class FakeElem:
    def __init__(self, node_name, attributes=None):
        self.node_name = node_name
        self.attributes = attributes or {}


class FakeDomState:
    def __init__(self, selector_map=None):
        self.selector_map = selector_map or {}


class FakeState:
    def __init__(self, dom_state=None):
        self.dom_state = dom_state or FakeDomState()


@pytest.mark.asyncio
async def test_execute_history_step_with_pending_and_extract():
    """
    Test flow:
    - wait_for_elements=True
    - needs_element_matching=True and min_elements>0 path (_wait_for_minimum_elements used)
    - first action is non-extract and _update_action_indices returns a non-None updated action
    - pending_actions executed via multi_act before extract
    - extract action triggers _execute_ai_step and results are appended
    """
    # Prepare fake state and browser_session
    dom_state = FakeDomState(selector_map={1: FakeElem("BUTTON", {"aria-label": "Click me"})})
    state = FakeState(dom_state=dom_state)

    async def fake_get_browser_state_summary(include_screenshot=False):
        return state

    browser_session = SimpleNamespace(get_browser_state_summary=fake_get_browser_state_summary)

    # Build fake self object with required attributes/methods
    async def fake_wait_for_minimum_elements(min_elements, timeout=0, poll_interval=0):
        return state

    async def fake_update_action_indices(historical_elem, action, st):
        return {"updated": "action"}  # non-None means will be queued

    async def fake_multi_act(pending):
        return ["batch_result"]

    async def fake_execute_ai_step(query, include_screenshot, extract_links, ai_step_llm):
        return "ai_result"

    fake_self = SimpleNamespace()
    fake_self.browser_session = browser_session
    fake_self.logger = SimpleNamespace(info=lambda *a, **k: None)
    fake_self._count_expected_elements_from_history = lambda history_item: 1
    fake_self._wait_for_minimum_elements = fake_wait_for_minimum_elements
    fake_self._update_action_indices = fake_update_action_indices
    fake_self.multi_act = fake_multi_act
    fake_self._execute_ai_step = fake_execute_ai_step
    fake_self._format_element_for_error = lambda e: "ELEMENT-INFO"

    # Build history: first click, then extract
    click = FakeAction({"click": {}})
    extract = FakeAction({"extract": {"query": "find this", "extract_links": True}})
    model_output = SimpleNamespace(action=[click, extract])
    hist_state = SimpleNamespace(interacted_element=[FakeElem("BUTTON", {"id": "btn1"})])
    history_item = SimpleNamespace(model_output=model_output, state=hist_state)

    results = await Agent._execute_history_step(fake_self, history_item, delay=0.0, ai_step_llm=None, wait_for_elements=True)

    assert results == ["batch_result", "ai_result"]


@pytest.mark.asyncio
async def test_execute_history_step_update_none_raises_with_similar_elements():
    """
    Test flow:
    - wait_for_elements=False (direct get_browser_state_summary path)
    - non-extract action where _update_action_indices returns None
    - state.dom_state.selector_map contains matching node_name with aria-labels so similar_elements branch is used
    - ValueError is raised and message contains diagnostics
    """
    selector_map = {
        1: FakeElem("INPUT", {"aria-label": "First input"}),
        2: FakeElem("INPUT", {"aria-label": "Second input"}),
        3: FakeElem("DIV", {"aria-label": "Other"}),
    }
    dom_state = FakeDomState(selector_map=selector_map)
    state = FakeState(dom_state=dom_state)

    async def fake_get_browser_state_summary(include_screenshot=False):
        return state

    browser_session = SimpleNamespace(get_browser_state_summary=fake_get_browser_state_summary)

    async def fake_update_action_indices(historical_elem, action, st):
        return None

    fake_self = SimpleNamespace()
    fake_self.browser_session = browser_session
    fake_self.logger = SimpleNamespace(info=lambda *a, **k: None)
    fake_self._update_action_indices = fake_update_action_indices
    fake_self._format_element_for_error = lambda e: "ELEMENT-LOOKUP-INFO"

    # Build history with a single 'click' action and a historical element with node_name 'INPUT'
    click = FakeAction({"click": {}})
    model_output = SimpleNamespace(action=[click])
    hist_state = SimpleNamespace(interacted_element=[FakeElem("INPUT", {"id": "x"})])
    history_item = SimpleNamespace(model_output=model_output, state=hist_state)

    with pytest.raises(ValueError) as exc:
        await Agent._execute_history_step(fake_self, history_item, delay=0.0, ai_step_llm=None, wait_for_elements=False)

    msg = str(exc.value)
    assert "Could not find matching element for action 0" in msg
    assert "ELEMENT-LOOKUP-INFO" in msg
    # Diagnostic should include either similar elements info or found count
    assert ("Available <INPUT> with aria-label" in msg) or ("Found" in msg)
