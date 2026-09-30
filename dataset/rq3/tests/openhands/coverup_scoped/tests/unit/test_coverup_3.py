# file: openhands/agenthub/visualbrowsing_agent/visualbrowsing_agent.py:187-317
# asked: {"lines": [200, 201, 202, 203, 204, 205, 206, 207, 208, 210, 214, 215, 218, 219, 220, 221, 222, 224, 225, 227, 228, 229, 231, 232, 237, 238, 240, 242, 243, 244, 246, 247, 248, 249, 250, 251, 253, 254, 255, 256, 258, 259, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 272, 273, 274, 275, 277, 278, 279, 281, 282, 283, 284, 285, 287, 288, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 302, 304, 306, 308, 309, 311, 312, 313, 314, 317], "branches": [[210, 214], [210, 218], [218, 219], [218, 231], [219, 220], [219, 222], [222, 224], [222, 225], [225, 218], [225, 227], [227, 228], [227, 229], [231, 232], [231, 236], [236, 240], [236, 242], [243, 244], [243, 279], [244, 246], [244, 253], [247, 248], [247, 253], [249, 250], [249, 253], [254, 255], [254, 258], [281, 282], [281, 283], [290, 291], [290, 292], [293, 294], [293, 295]]}
# gained: {"lines": [200, 201, 202, 203, 204, 205, 206, 207, 208, 210, 214, 215, 218, 219, 220, 221, 222, 224, 225, 227, 229, 231, 232, 237, 238, 240, 242, 243, 244, 246, 247, 248, 249, 250, 251, 253, 254, 255, 256, 258, 259, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 272, 273, 274, 275, 277, 278, 279, 281, 283, 284, 285, 287, 288, 290, 292, 293, 295, 296, 297, 298, 299, 300, 302, 304, 306, 308, 309, 311, 312, 313, 314, 317], "branches": [[210, 214], [210, 218], [218, 219], [218, 231], [219, 220], [219, 222], [222, 224], [222, 225], [225, 218], [225, 227], [227, 229], [231, 232], [231, 236], [236, 240], [236, 242], [243, 244], [244, 246], [244, 253], [247, 248], [249, 250], [254, 255], [281, 283], [290, 292], [293, 295]]}

import pytest
from types import SimpleNamespace

from openhands.events.event import EventSource
from openhands.events.action import BrowseInteractiveAction, MessageAction, AgentFinishAction
from openhands.events.observation import BrowserOutputObservation

import openhands.agenthub.visualbrowsing_agent.visualbrowsing_agent as vba


class FakeState:
    def __init__(self, view, task='do something', intent=(None, [])):
        self.view = view
        self.inputs = {'task': task}
        self._intent = intent

    def get_current_user_intent(self):
        return self._intent


def make_agent():
    # Create agent instance without invoking __init__, and set required attributes
    agent = object.__new__(vba.VisualBrowsingAgent)
    agent.error_accumulator = 0
    agent.action_prompt = "ACTION_PROMPT"
    agent.hints = "HINTS"
    agent.abstract_example = "ABSTRACT"
    agent.concrete_example = "CONCRETE"
    # default llm completion and response parser; tests will override as needed
    agent.llm = SimpleNamespace(completion=lambda **kwargs: "LLM_RESPONSE")
    agent.response_parser = SimpleNamespace(parse=lambda resp: MessageAction(content="PARSED"))
    return agent


def make_browse_obs(**kwargs):
    # Create an uninitialized instance and set attributes used by the agent.step logic
    obs = BrowserOutputObservation.__new__(BrowserOutputObservation)
    # Set some defaults then override with kwargs
    defaults = {
        "url": "http://x",
        "trigger_by_action": "t",
        "screenshot": "",
        "screenshot_path": None,
        "set_of_marks": "",
        "error": False,
        "goal_image_urls": [],
        "open_pages_urls": [],
        "active_page_index": -1,
        "dom_object": {},
        "axtree_object": {},
        "extra_element_properties": {},
        "last_browser_action": "",
        "last_browser_action_error": "",
        "focused_element_bid": "",
        "filter_visible_only": False,
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(obs, k, v)
    return obs


def test_returns_noop_when_single_view():
    agent = make_agent()
    state = FakeState(view=[object()])  # length 1 triggers noop
    action = agent.step(state)
    assert isinstance(action, BrowseInteractiveAction)
    assert action.browser_actions == "noop(1000)"
    assert action.return_axtree is True


def test_finishes_when_agent_message_in_view():
    agent = make_agent()
    # subclass MessageAction to provide a read-only source property returning EventSource.AGENT
    class MsgWithSource(MessageAction):
        @property
        def source(self):
            return EventSource.AGENT

    msg = MsgWithSource(content="done")
    # ensure view length > 1 to skip noop branch
    state = FakeState(view=[object(), msg])
    action = agent.step(state)
    assert isinstance(action, AgentFinishAction)
    assert getattr(action, "outputs", {}) == {"content": msg.content}


def test_send_msg_to_user_branch_returns_message_action():
    agent = make_agent()
    # Create two BrowseInteractiveAction events so prev_actions logic removes first and keeps last_action
    first = BrowseInteractiveAction(browser_actions="noop(1000)")
    second = BrowseInteractiveAction(browser_actions="doit", browsergym_send_msg_to_user="Hello user")
    state = FakeState(view=[first, second])
    action = agent.step(state)
    assert isinstance(action, MessageAction)
    assert action.content == "Hello user"


def test_error_prefix_too_many_errors(monkeypatch):
    agent = make_agent()
    # set error_accumulator close to threshold
    agent.error_accumulator = 5

    # Prepare a BrowserOutputObservation with error True using helper
    obs = make_browse_obs(error=True)
    # Ensure view contains more than 1 element so noop branch not taken
    state = FakeState(view=[object(), obs])

    # Monkeypatch get_error_prefix to return non-empty prefix
    monkeypatch.setattr(vba, "get_error_prefix", lambda o: "ERR")
    # Patch get_history_prompt because step calls it before handling observation
    monkeypatch.setattr(vba, "get_history_prompt", lambda prev_actions: "HISTORY")
    action = agent.step(state)
    assert isinstance(action, MessageAction)
    assert "Too many errors encountered. Task failed." in action.content


def test_flatten_axtree_success_and_parse(monkeypatch):
    agent = make_agent()

    # Create a BrowserOutputObservation with focused_element_bid set to test focused_element branch
    obs = make_browse_obs(
        set_of_marks="marks",
        error=False,
        focused_element_bid="42",
        axtree_object={"node": "n"},
        extra_element_properties={},
    )

    # Prepare state: include an initial noop BrowseInteractiveAction so prev_actions logic removes it
    noop = BrowseInteractiveAction(browser_actions="noop(1000)")
    state = FakeState(view=[noop, obs], intent=("find something", []))

    # Monkeypatch flatten_axtree_to_str and get_axtree to return predictable axtree content
    monkeypatch.setattr(vba, "flatten_axtree_to_str", lambda a, extra_properties, **kwargs: "FLATTENED_AXTREE")
    monkeypatch.setattr(vba, "get_axtree", lambda axtree_txt=None: f"AXTREE:{axtree_txt}")

    # Monkeypatch create_goal_prompt and create_observation_prompt used to build prompts
    monkeypatch.setattr(vba, "create_goal_prompt", lambda goal, imgs: (f"GOAL:{goal}", []))
    monkeypatch.setattr(vba, "create_observation_prompt", lambda axt, tabs, focused, error_prefix, som: ("OBS_PROMPT", None))
    monkeypatch.setattr(vba, "get_tabs", lambda o: "TABS")
    monkeypatch.setattr(vba, "get_history_prompt", lambda prev_actions: "HISTORY")

    # Make llm.completion return a fake response and response_parser.parse return a MessageAction
    called = {}
    def fake_completion(**kwargs):
        called['messages'] = kwargs.get('messages')
        return "LLM_OK"
    monkeypatch.setattr(agent, "llm", SimpleNamespace(completion=fake_completion))
    monkeypatch.setattr(agent, "response_parser", SimpleNamespace(parse=lambda resp: MessageAction(content="PARSED_OK")))

    action = agent.step(state)
    assert isinstance(action, MessageAction)
    assert action.content == "PARSED_OK"
    # ensure the messages were built and system + user messages are present
    assert isinstance(called.get('messages'), list)
    assert called['messages'][0].role == "system"
    assert called['messages'][1].role == "user"


def test_flatten_axtree_exception_returns_error_message(monkeypatch):
    agent = make_agent()
    # Create observation that will trigger flatten exception
    obs = make_browse_obs(axtree_object={}, extra_element_properties={})
    noop = BrowseInteractiveAction(browser_actions="noop(1000)")
    state = FakeState(view=[noop, obs])

    # Patch flatten_axtree_to_str to raise
    def raiser(*args, **kwargs):
        raise RuntimeError("boom")
    monkeypatch.setattr(vba, "flatten_axtree_to_str", raiser)
    # minimal stubs for other functions to avoid further errors
    monkeypatch.setattr(vba, "get_tabs", lambda o: "")
    monkeypatch.setattr(vba, "get_error_prefix", lambda o: "")
    monkeypatch.setattr(vba, "get_history_prompt", lambda prev_actions: "HISTORY")

    action = agent.step(state)
    assert isinstance(action, MessageAction)
    assert action.content == "Error encountered when browsing."
