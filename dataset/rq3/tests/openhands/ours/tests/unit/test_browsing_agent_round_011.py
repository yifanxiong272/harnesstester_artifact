import importlib

import types

import pytest

# Module under test
mod = importlib.import_module("openhands.agenthub.browsing_agent.browsing_agent")

# Helper: create a bare-bones dummy State object matching what step() expects
class DummyState:
    def __init__(self, view, inputs=None, intent=None):
        self.view = view
        self._intent = intent
        self.inputs = inputs or {}

    def get_current_user_intent(self):
        # returns a (goal, metadata) pair
        return (self._intent, {})


# Replace several collaborator types in the module with lightweight test doubles.
# We patch symbols on the module so isinstance checks inside step() behave with our dummies.
class DummyBrowseInteractiveAction:
    def __init__(self, browser_actions=None, browsergym_send_msg_to_user=None):
        self.browser_actions = browser_actions
        self.browsergym_send_msg_to_user = browsergym_send_msg_to_user


class DummyMessageAction:
    def __init__(self, content):
        # In production MessageAction may have more shape; tests only assert on .content
        self.content = content


class DummyObservation:
    pass


class DummyBrowserOutputObservation(DummyObservation):
    def __init__(self, *, error=False, last_browser_action=None, url="", axtree_object=None, extra_element_properties=None):
        self.error = error
        self.last_browser_action = last_browser_action
        self.url = url
        self.axtree_object = axtree_object
        self.extra_element_properties = extra_element_properties


class DummyTextContent:
    def __init__(self, text):
        self.text = text


class DummyMessage:
    def __init__(self, role, content):
        self.role = role
        self.content = content


# Apply patches to the module so BrowsingAgent.step resolves our test doubles
@pytest.fixture(autouse=True)
def patch_module_symbols(monkeypatch):
    monkeypatch.setattr(mod, "BrowseInteractiveAction", DummyBrowseInteractiveAction)
    monkeypatch.setattr(mod, "MessageAction", DummyMessageAction)
    monkeypatch.setattr(mod, "Observation", DummyObservation)
    monkeypatch.setattr(mod, "BrowserOutputObservation", DummyBrowserOutputObservation)
    monkeypatch.setattr(mod, "TextContent", DummyTextContent)
    monkeypatch.setattr(mod, "Message", DummyMessage)
    yield


# Utility to create a BrowsingAgent-like instance without invoking its real __init__
# We construct an object of the real class but manually set the attributes used by step().
def make_agent(
    *,
    error_accumulator=0,
    action_space_desc="ACTION_DESC",
    llm_result=None,
    response_parse_result=None,
):
    agent = object.__new__(mod.BrowsingAgent)

    # minimal action_space with describe() used by step
    class AS:
        def describe(self, with_long_description=False, with_examples=True):
            return action_space_desc

    agent.action_space = AS()
    agent.error_accumulator = error_accumulator

    # simple llm with a completion method that records what was passed and returns llm_result
    class DummyLLM:
        def __init__(self):
            self.last_call = None

        def completion(self, *, messages, stop):
            # record the messages list shape for assertions
            self.last_call = {"messages": messages, "stop": stop}
            return llm_result

    agent.llm = DummyLLM()

    # simple response parser
    class RP:
        def parse(self, response):
            return response_parse_result

    agent.response_parser = RP()

    return agent


def test_eval_mode_noop_round_011(monkeypatch):
    # EVAL_MODE True and single-element view should return a noop BrowseInteractiveAction
    monkeypatch.setattr(mod, "EVAL_MODE", True)

    # create state with single event in view (the specific event content is irrelevant)
    state = DummyState(view=["irrelevant"])

    agent = make_agent()

    result = mod.BrowsingAgent.step(agent, state)

    # Should return a BrowseInteractiveAction instance with browser_actions set to noop()
    assert isinstance(result, DummyBrowseInteractiveAction)
    assert result.browser_actions == "noop()"


def test_last_action_send_msg_round_011(monkeypatch):
    # When last_action has browsergym_send_msg_to_user, step should return a MessageAction with that content
    monkeypatch.setattr(mod, "EVAL_MODE", False)

    # create a BrowseInteractiveAction event that will become last_action
    send_msg = "hello-user"
    event = DummyBrowseInteractiveAction(browser_actions="act", browsergym_send_msg_to_user=send_msg)

    state = DummyState(view=[event])

    agent = make_agent()

    result = mod.BrowsingAgent.step(agent, state)

    assert isinstance(result, DummyMessageAction)
    assert result.content == send_msg


def test_error_accumulator_too_many_errors_round_011(monkeypatch):
    # Simulate a BrowserOutputObservation with an error and agent.error_accumulator incrementing past 5
    monkeypatch.setattr(mod, "EVAL_MODE", False)

    last_obs = DummyBrowserOutputObservation(error=True, last_browser_action="last_act")
    state = DummyState(view=[last_obs])

    # start with 5 so that incrementing leads to >5
    agent = make_agent(error_accumulator=5)

    result = mod.BrowsingAgent.step(agent, state)

    assert isinstance(result, DummyMessageAction)
    assert result.content == "Too many errors encountered. Task failed."


def test_flatten_exception_returns_error_message_round_011(monkeypatch):
    # If flatten_axtree_to_str raises, we should get a MessageAction with the error string
    monkeypatch.setattr(mod, "EVAL_MODE", False)

    # last_obs with no error so the code attempts to flatten axtree
    last_obs = DummyBrowserOutputObservation(error=False, url="http://x", axtree_object={})
    state = DummyState(view=[last_obs])

    # Make flatten_axtree_to_str raise
    def raise_on_flatten(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(mod, "flatten_axtree_to_str", raise_on_flatten)

    agent = make_agent()

    result = mod.BrowsingAgent.step(agent, state)

    assert isinstance(result, DummyMessageAction)
    assert result.content == "Error encountered when browsing."


def test_llm_and_response_parser_called_round_011(monkeypatch):
    # Happy-path: flatten returns text and llm.completion + response_parser.parse are invoked; return value is propagated
    monkeypatch.setattr(mod, "EVAL_MODE", False)

    # last_obs with no error
    last_obs = DummyBrowserOutputObservation(
        error=False,
        url="http://ok",
        axtree_object={"some": "tree"},
        extra_element_properties={"p": "v"},
    )

    # State has no current user intent so goal should be taken from inputs['task']
    state = DummyState(view=[last_obs], inputs={"task": "my task"}, intent=None)

    # Make flatten return a string
    monkeypatch.setattr(mod, "flatten_axtree_to_str", lambda *args, **kwargs: "AXTREE_TEXT")

    # Simple deterministic system/prompt functions
    monkeypatch.setattr(mod, "get_error_prefix", lambda last: "ERRP")
    monkeypatch.setattr(mod, "get_system_message", lambda goal, action_space: "SYSMSG")
    monkeypatch.setattr(mod, "get_prompt", lambda error_prefix, cur_url, cur_axtree_txt, prev_action_str: "PROMPTMSG")

    # Prepare agent with llm returning a known structure and response_parser returning a sentinel
    llm_result = {"llm": "result"}
    parse_result = "PARSED_ACTION"
    agent = make_agent(llm_result=llm_result, response_parse_result=parse_result)

    result = mod.BrowsingAgent.step(agent, state)

    # The response_parser.parse return should be propagated directly
    assert result == parse_result

    # Validate the LLM was called with messages including our system and user content
    # agent.llm.last_call recorded messages
    last_call = agent.llm.last_call
    assert last_call is not None
    messages_passed = last_call["messages"]

    # Expect two messages: system and user
    assert len(messages_passed) == 2
    assert isinstance(messages_passed[0], DummyMessage)
    # system message content stored as list with DummyTextContent; verify the inner text
    system_content = messages_passed[0].content
    assert isinstance(system_content, list)
    assert isinstance(system_content[0], DummyTextContent)
    assert system_content[0].text == "SYSMSG"

    # user prompt message verification
    user_content = messages_passed[1].content
    assert isinstance(user_content, list)
    assert isinstance(user_content[0], DummyTextContent)
    assert user_content[0].text == "PROMPTMSG"
