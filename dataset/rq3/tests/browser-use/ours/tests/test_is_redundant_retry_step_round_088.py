import types
import pytest
from browser_use.agent.service import Agent

# Minimal local test doubles that match the shapes expected by _is_redundant_retry_step
class DummyLogger:
    def __init__(self):
        self.messages = []

    def debug(self, msg):
        # store debug calls for assertions
        self.messages.append(msg)


class DummyElement:
    def __init__(self, element_hash=None, stable_hash=None, x_path=None, node_name="button"):
        self.element_hash = element_hash
        self.stable_hash = stable_hash
        self.x_path = x_path
        self.node_name = node_name


class DummyState:
    def __init__(self, interacted_element):
        self.interacted_element = interacted_element


class DummyAction:
    def __init__(self, action_key):
        self._action_key = action_key

    def model_dump(self, exclude_unset=True):
        # Return a dict shaped like the real action model_dump: key is the action type
        return {self._action_key: {}}


class DummyModelOutput:
    def __init__(self, actions):
        # actions is a list of DummyAction
        self.action = actions


class DummyHistory:
    def __init__(self, elements, action_keys=None):
        # elements: list of DummyElement (or empty list)
        self.state = DummyState(elements)
        if action_keys is None:
            self.model_output = None
        else:
            self.model_output = DummyModelOutput([DummyAction(k) for k in action_keys])


class DummySelf:
    def __init__(self):
        self.logger = DummyLogger()


# retrieve the unbound function so we can call it with a lightweight self
_is_redundant = getattr(Agent, "_is_redundant_retry_step")


def test_previous_none_returns_false_round_088():
    self = DummySelf()
    current = DummyHistory([DummyElement(element_hash="h")], ["click"])
    result = _is_redundant(self, current, None, True)
    assert result is False


def test_previous_not_succeeded_returns_false_round_088():
    self = DummySelf()
    current = DummyHistory([DummyElement(element_hash="h")], ["click"])
    previous = DummyHistory([DummyElement(element_hash="h")], ["click"])
    result = _is_redundant(self, current, previous, False)
    assert result is False


def test_missing_elements_returns_false_round_088():
    self = DummySelf()
    # empty current elements
    current_empty = DummyHistory([], ["click"])
    previous = DummyHistory([DummyElement(element_hash="h")], ["click"])
    assert _is_redundant(self, current_empty, previous, True) is False

    # empty previous elements
    current = DummyHistory([DummyElement(element_hash="h")], ["click"])
    previous_empty = DummyHistory([], ["click"])
    assert _is_redundant(self, current, previous_empty, True) is False


def test_missing_elem_objects_returns_false_round_088():
    self = DummySelf()
    # lists present but first elements are None
    current = DummyHistory([None], ["click"])
    previous = DummyHistory([DummyElement(element_hash="h")], ["click"])
    assert _is_redundant(self, current, previous, True) is False

    current = DummyHistory([DummyElement(element_hash="h")], ["click"])
    previous = DummyHistory([None], ["click"])
    assert _is_redundant(self, current, previous, True) is False


def test_elements_different_returns_false_round_088():
    self = DummySelf()
    # Different element_hash, stable_hash None, x_path different => not same
    current = DummyHistory([DummyElement(element_hash="h1", stable_hash=None, x_path="/a")], ["click"])
    previous = DummyHistory([DummyElement(element_hash="h2", stable_hash=None, x_path="/b")], ["click"])
    assert _is_redundant(self, current, previous, True) is False


def test_no_actions_returns_false_round_088():
    self = DummySelf()
    # elements match by hash but model_output missing for previous
    current = DummyHistory([DummyElement(element_hash="h")], ["click"])
    previous = DummyHistory([DummyElement(element_hash="h")], None)
    assert _is_redundant(self, current, previous, True) is False

    # model_output present but action lists empty
    class EmptyModelOutput:
        def __init__(self):
            self.action = []

    current2 = DummyHistory([DummyElement(element_hash="h")], ["click"])
    prev2 = DummyHistory([DummyElement(element_hash="h")], [])
    # prev2.model_output is a DummyModelOutput only when action_keys provided; emulate empty list
    prev2.model_output = EmptyModelOutput()
    assert _is_redundant(self, current2, prev2, True) is False


def test_different_action_types_returns_false_round_088():
    self = DummySelf()
    # same element, but different action keys (click vs type)
    current = DummyHistory([DummyElement(element_hash="h")], ["click"])
    previous = DummyHistory([DummyElement(element_hash="h")], ["type"])
    assert _is_redundant(self, current, previous, True) is False


def test_redundant_retry_by_hash_returns_true_round_088():
    self = DummySelf()
    # same element_hash and same action type -> should be redundant
    elem = DummyElement(element_hash="same-hash", stable_hash=None, x_path="/x", node_name="a")
    current = DummyHistory([elem], ["click"])
    previous = DummyHistory([DummyElement(element_hash="same-hash", stable_hash=None, x_path="/x", node_name="a")], ["click"])
    result = _is_redundant(self, current, previous, True)
    assert result is True
    # logger debug should have been called with the message mentioning node name and action
    assert any("Detected redundant retry" in m or "\ud83d\udd04" in m for m in self.logger.messages)


def test_redundant_retry_by_stable_hash_returns_true_round_088():
    self = DummySelf()
    # different element_hash but same non-None stable_hash -> should be redundant
    current_elem = DummyElement(element_hash="h1", stable_hash="stable-1", x_path="/x", node_name="div")
    prev_elem = DummyElement(element_hash="h2", stable_hash="stable-1", x_path="/y", node_name="div")
    current = DummyHistory([current_elem], ["click"])
    previous = DummyHistory([prev_elem], ["click"])
    assert _is_redundant(self, current, previous, True) is True
    assert any("Detected redundant retry" in m or "\ud83d\udd04" in m for m in self.logger.messages)
