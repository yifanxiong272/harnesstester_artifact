import pytest

import openhands.agenthub.visualbrowsing_agent.visualbrowsing_agent as vba


class DummyState:
    def __init__(self, view, intent=(None, []), inputs=None):
        self.view = view
        self._intent = intent
        self.inputs = inputs or {"task": "default task"}

    def get_current_user_intent(self):
        return self._intent


# Local fake classes to monkeypatch into the module for deterministic behavior
class FakeBrowseInteractiveAction:
    def __init__(self, browser_actions=None, return_axtree=False, browsergym_send_msg_to_user=None):
        self.browser_actions = browser_actions
        self.return_axtree = return_axtree
        # attribute used in branch that sends a message to user
        self.browsergym_send_msg_to_user = browsergym_send_msg_to_user


class FakeAgentFinishAction:
    def __init__(self, outputs=None):
        self.outputs = outputs


class FakeMessageAction:
    def __init__(self, content=None, source=None):
        self.content = content
        self.source = source


class FakeObservation:
    pass


class FakeBrowserOutputObservation(FakeObservation):
    def __init__(self, error=False, focused_element_bid=None, axtree_object=None, extra_element_properties=None, set_of_marks=None):
        self.error = error
        self.focused_element_bid = focused_element_bid
        self.axtree_object = axtree_object
        self.extra_element_properties = extra_element_properties
        self.set_of_marks = set_of_marks


class FakeTextContent:
    def __init__(self, type=None, text=None):
        self.type = type
        self.text = text


class FakeImageContent:
    def __init__(self, image_urls=None):
        self.image_urls = image_urls


class FakeMessage:
    def __init__(self, role=None, content=None):
        self.role = role
        self.content = content


@pytest.fixture(autouse=True)
def patch_module_classes(monkeypatch):
    """Monkeypatch classes and helper functions from the module to deterministic fakes."""
    monkeypatch.setattr(vba, "BrowseInteractiveAction", FakeBrowseInteractiveAction)
    monkeypatch.setattr(vba, "AgentFinishAction", FakeAgentFinishAction)
    monkeypatch.setattr(vba, "MessageAction", FakeMessageAction)
    monkeypatch.setattr(vba, "Observation", FakeObservation)
    monkeypatch.setattr(vba, "BrowserOutputObservation", FakeBrowserOutputObservation)
    monkeypatch.setattr(vba, "TextContent", FakeTextContent)
    monkeypatch.setattr(vba, "ImageContent", FakeImageContent)
    monkeypatch.setattr(vba, "Message", FakeMessage)

    # Default deterministic implementations for helper functions
    monkeypatch.setattr(vba, "get_history_prompt", lambda prev_actions: "HISTORY_PROMPT")
    monkeypatch.setattr(vba, "get_error_prefix", lambda obs: "ERR" if getattr(obs, "error", False) else "")
    monkeypatch.setattr(vba, "get_tabs", lambda obs: "TABS")
    monkeypatch.setattr(vba, "flatten_axtree_to_str", lambda a, **kw: "AX_STR")
    monkeypatch.setattr(vba, "get_axtree", lambda axtree_txt: axtree_txt)
    monkeypatch.setattr(vba, "create_goal_prompt", lambda goal, image_urls: ("GOAL_TXT", image_urls or []))
    monkeypatch.setattr(vba, "create_observation_prompt", lambda a, b, c, d, e: ("OBS_TXT", None))
    yield


def call_step_with_self_and_state(monkeypatch, state, self_attrs=None):
    """Helper that constructs a minimal self object and calls the unbound step function.

    We avoid running VisualBrowsingAgent.__init__ to keep the test lightweight.
    """
    # get unbound function
    step_func = vba.VisualBrowsingAgent.step
    # craft a minimal self
    class S:
        pass

    s = S()
    # Default attributes required by step
    s.error_accumulator = 0
    s.action_prompt = "ACTION_PROMPT"
    s.hints = "HINTS"
    s.abstract_example = "ABSTRACT"
    s.concrete_example = "CONCRETE"
    # fake llm and response_parser
    s.llm = type("LLM", (), {"completion": lambda *_, **__: "LLM_RESPONSE"})()
    s.response_parser = type("RP", (), {"parse": lambda _, resp: ("PARSED", resp)})()

    # override with any provided attributes
    if self_attrs:
        for k, v in self_attrs.items():
            setattr(s, k, v)

    return step_func(s, state)


def test_len_view_one_returns_noop_round_004():
    """When state.view has length 1, the agent should immediately return a noop BrowseInteractiveAction."""
    state = DummyState(view=[object()])

    # Call step
    result = call_step_with_self_and_state(None, state)

    # Ensure it's our patched BrowseInteractiveAction with the expected noop values
    assert isinstance(result, FakeBrowseInteractiveAction)
    assert result.browser_actions == "noop(1000)"
    assert result.return_axtree is True


def test_agent_finish_on_message_from_agent_round_004():
    """If a MessageAction from EventSource.AGENT is in view, the agent should finish with that content."""
    # create a FakeMessageAction that mimics a message from the agent
    msg = FakeMessageAction(content="done", source=vba.EventSource.AGENT)
    state = DummyState(view=[object(), msg])

    result = call_step_with_self_and_state(None, state)

    # Should return an AgentFinishAction-like object (patched)
    assert isinstance(result, FakeAgentFinishAction)
    assert result.outputs == {"content": "done"}


def test_returns_message_on_browser_send_msg_round_004():
    """If the last BrowseInteractiveAction contains browsergym_send_msg_to_user, it should be returned as MessageAction."""
    # first noop, then an action that requests sending message to user
    noop = FakeBrowseInteractiveAction(browser_actions="noop(1000)")
    send_action = FakeBrowseInteractiveAction(browsergym_send_msg_to_user="hello_user")
    state = DummyState(view=[noop, send_action])

    result = call_step_with_self_and_state(None, state)

    # Should return a MessageAction with the text from browsergym_send_msg_to_user
    assert isinstance(result, FakeMessageAction)
    assert result.content == "hello_user"


def test_error_prefix_and_too_many_errors_round_004():
    """When BrowserOutputObservation.error is True and error accumulator crosses limit, return failure message."""
    # create a browser observation showing an error
    obs = FakeBrowserOutputObservation(error=True)
    # Put an initial noop BrowseInteractiveAction so prev_actions logic runs but returns to obs handling
    noop = FakeBrowseInteractiveAction(browser_actions="noop(1000)")
    state = DummyState(view=[noop, obs])

    # set self.error_accumulator to 5 so after increment it becomes 6 (>5)
    result = call_step_with_self_and_state(None, state, self_attrs={"error_accumulator": 5})

    # Expect a MessageAction indicating too many errors
    assert isinstance(result, FakeMessageAction)
    assert "Too many errors" in result.content


def test_flatten_axtree_exception_returns_error_message_round_004(monkeypatch):
    """If flatten_axtree_to_str raises, the agent should catch and return a browsing error message."""
    # arrange obs with no error, but cause flatten_axtree_to_str to raise
    obs = FakeBrowserOutputObservation(error=False, axtree_object={})
    noop = FakeBrowseInteractiveAction(browser_actions="noop(1000)")
    state = DummyState(view=[noop, obs])

    # monkeypatch the flatten function to raise
    monkeypatch.setattr(vba, "flatten_axtree_to_str", lambda *a, **kw: (_ for _ in ()).throw(Exception("boom")))

    result = call_step_with_self_and_state(monkeypatch, state)

    assert isinstance(result, FakeMessageAction)
    assert result.content == "Error encountered when browsing."


def test_full_prompt_assembly_and_response_parse_round_004(monkeypatch):
    """Test the normal path: build prompts including goal images and som screenshot and parse llm response."""
    # make observation with focused_element_bid and set_of_marks to cover branches
    obs = FakeBrowserOutputObservation(error=False, focused_element_bid="BID123", axtree_object={}, extra_element_properties={}, set_of_marks={"m": 1})
    noop = FakeBrowseInteractiveAction(browser_actions="noop(1000)")
    state = DummyState(view=[noop, obs], intent=(None, ["http://img.example/1.png"]), inputs={"task": "task_from_inputs"})

    # patch create_goal_prompt to produce a non-empty list of images
    monkeypatch.setattr(vba, "create_goal_prompt", lambda goal, image_urls: ("GOAL_FROM_PROMPT", ["http://img.example/1.png"]))
    # patch create_observation_prompt to return an observation text and a som screenshot
    monkeypatch.setattr(vba, "create_observation_prompt", lambda *a, **kw: ("OBS_TEXT", "http://som.example/s.png"))

    # Make llm.completion return a deterministic value and parser return a sentinel
    parse_result = {"action": "do_something"}
    def fake_completion(*_, **__):
        return "LLM_OK"

    def fake_parse(self, response):
        # assert that the response is the llm completion output
        assert response == "LLM_OK"
        return parse_result

    result = call_step_with_self_and_state(None, state, self_attrs={
        "llm": type("LLM", (), {"completion": staticmethod(fake_completion)})(),
        "response_parser": type("RP", (), {"parse": fake_parse})(),
    })

    assert result is parse_result
