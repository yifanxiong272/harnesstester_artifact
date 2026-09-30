import pytest
import types
import asyncio
from types import SimpleNamespace

import browser_use.agent.service as service

# Helper test fixtures / classes used across tests
class DummyLogger:
    def __init__(self):
        self.infos = []
        self.debugs = []

    def info(self, *args, **kwargs):
        self.infos.append((args, kwargs))

    def debug(self, *args, **kwargs):
        self.debugs.append((args, kwargs))


class DummyAction:
    def __init__(self, index=0):
        self._index = index
        self.set_calls = []

    def get_index(self):
        return self._index

    def set_index(self, new_index):
        self.set_calls.append(new_index)
        self._index = new_index


class DummyElement:
    def __init__(
        self,
        node_name="div",
        element_hash=None,
        stable_hash=None,
        xpath=None,
        ax_node=None,
        attributes=None,
    ):
        self.node_name = node_name
        self.element_hash = element_hash
        self._stable_hash = stable_hash
        self.xpath = xpath
        self.ax_node = ax_node
        self.attributes = attributes or {}

    def compute_stable_hash(self):
        # deterministic stable hash based on provided _stable_hash
        return self._stable_hash


class DummyAXNode:
    def __init__(self, name):
        self.name = name


class DummyDomState:
    def __init__(self, selector_map):
        self.selector_map = selector_map


class DummyBrowserStateSummary:
    def __init__(self, selector_map):
        self.dom_state = DummyDomState(selector_map)


class DummySelf:
    def __init__(self):
        self.logger = DummyLogger()


@pytest.fixture(autouse=True)
def patch_match_level(monkeypatch):
    # Provide a lightweight MatchLevel with .name on each member to avoid importing the real enum.
    class M:
        class _L:
            def __init__(self, name):
                self.name = name

        EXACT = _L("EXACT")
        STABLE = _L("STABLE")
        XPATH = _L("XPATH")
        AX_NAME = _L("AX_NAME")
        ATTRIBUTE = _L("ATTRIBUTE")

    monkeypatch.setattr(service, "MatchLevel", M)
    yield


@pytest.mark.asyncio
async def test_exact_match_round_007():
    """Ensure EXACT hash match updates the action index and returns the action."""
    dummy = DummySelf()

    # historical element with a particular element_hash
    historical = SimpleNamespace(
        node_name="button",
        element_hash="hash-123",
        stable_hash=None,
        x_path=None,
        ax_name=None,
        attributes=None,
    )

    # selector map contains an element with a matching element_hash at index 5
    elem = DummyElement(node_name="button", element_hash="hash-123")
    selector_map = {5: elem, 6: DummyElement(node_name="button", element_hash="other")}

    bs = DummyBrowserStateSummary(selector_map)

    action = DummyAction(index=0)

    # Call the async method as an unbound coroutine on Agent class
    result = await service.Agent._update_action_indices(dummy, historical, action, bs)

    assert result is action
    # Because old index 0 != 5, set_index should have been called exactly once with 5
    assert action.set_calls == [5]
    # Logger should have an info entry about searching recorded
    assert any("Searching for element" in args[0][0] or "Searching for element" in str(args[0][0]) for args in dummy.logger.infos if args[0])


@pytest.mark.asyncio
async def test_xpath_and_ax_name_and_stable_match_round_007():
    """Cover XPATH, AX_NAME, and STABLE matching branches.

    We run three sub-scenarios by swapping the selector_map so each level matches when previous levels don't.
    """
    dummy = DummySelf()

    # Historical has stable_hash, xpath and ax_name set to prefer earlier matches if available
    historical = SimpleNamespace(
        node_name="li",
        element_hash="nonexistent",
        stable_hash="stable-42",
        x_path="/html/body/ul/li[2]",
        ax_name="Choice B",
        attributes=None,
    )

    # STABLE match scenario: one element compute_stable_hash returns "stable-42"
    stable_elem = DummyElement(node_name="li", element_hash="x", stable_hash="stable-42")
    xpath_elem = DummyElement(node_name="li", element_hash="y", xpath="/html/body/ul/li[2]")
    ax_elem = DummyElement(node_name="li", element_hash="z", ax_node=DummyAXNode("Choice B"))

    # 1) STABLE match should be found before XPATH and AX_NAME
    selector_map = {1: stable_elem, 2: xpath_elem, 3: ax_elem}
    bs = DummyBrowserStateSummary(selector_map)
    action = DummyAction(index=10)

    res = await service.Agent._update_action_indices(dummy, historical, action, bs)
    assert res is action
    assert action.set_calls == [1]
    action.set_calls.clear()

    # 2) If compute_stable_hash doesn't match, XPATH match should trigger
    stable_elem2 = DummyElement(node_name="li", element_hash="x", stable_hash="other")
    selector_map = {1: stable_elem2, 2: xpath_elem, 3: ax_elem}
    bs = DummyBrowserStateSummary(selector_map)
    action2 = DummyAction(index=2)

    res2 = await service.Agent._update_action_indices(dummy, historical, action2, bs)
    assert res2 is action2
    assert action2.set_calls == [2]
    action2.set_calls.clear()

    # 3) If no stable or xpath match, AX_NAME match should trigger
    selector_map = {1: DummyElement(node_name="li", element_hash="a", stable_hash="no"), 3: ax_elem}
    bs = DummyBrowserStateSummary(selector_map)
    action3 = DummyAction(index=99)

    res3 = await service.Agent._update_action_indices(dummy, historical, action3, bs)
    assert res3 is action3
    assert action3.set_calls == [3]


@pytest.mark.asyncio
async def test_attribute_match_and_failed_match_round_007():
    """Cover ATTRIBUTE matching branch and the final no-match -> None return path."""
    dummy = DummySelf()

    # Historical element that only has an id attribute
    historical_attr = SimpleNamespace(
        node_name="input",
        element_hash=None,
        stable_hash=None,
        x_path=None,
        ax_name=None,
        attributes={"id": "email-field"},
    )

    # Selector map with a matching attribute
    attr_elem = DummyElement(node_name="input", attributes={"id": "email-field"})
    selector_map = {7: attr_elem}
    bs = DummyBrowserStateSummary(selector_map)
    action = DummyAction(index=0)

    res = await service.Agent._update_action_indices(dummy, historical_attr, action, bs)
    assert res is action
    assert action.set_calls == [7]

    # Now a historical element with attributes but no matching element on page -> should return None
    historical_missing = SimpleNamespace(
        node_name="input",
        element_hash=None,
        stable_hash=None,
        x_path=None,
        ax_name=None,
        attributes={"id": "does-not-exist"},
    )

    selector_map2 = {1: DummyElement(node_name="input", attributes={"id": "other"})}
    bs2 = DummyBrowserStateSummary(selector_map2)
    action_missing = DummyAction(index=0)

    res_none = await service.Agent._update_action_indices(dummy, historical_missing, action_missing, bs2)
    assert res_none is None


@pytest.mark.asyncio
async def test_short_circuit_when_no_history_or_empty_selector_round_007():
    """The function should return the original action when historical_element is falsy or selector_map empty."""
    dummy = DummySelf()

    # Case 1: historical_element is None -> returns action unchanged
    action = DummyAction(index=1)
    bs_dummy = DummyBrowserStateSummary(selector_map={1: DummyElement(node_name="div")})

    res = await service.Agent._update_action_indices(dummy, None, action, bs_dummy)
    assert res is action
    assert action.set_calls == []

    # Case 2: selector_map is empty -> returns action unchanged
    historical = SimpleNamespace(node_name="div", element_hash="x", stable_hash=None, x_path=None, ax_name=None, attributes=None)
    bs_empty = DummyBrowserStateSummary(selector_map={})
    action2 = DummyAction(index=2)

    res2 = await service.Agent._update_action_indices(dummy, historical, action2, bs_empty)
    assert res2 is action2
    assert action2.set_calls == []
