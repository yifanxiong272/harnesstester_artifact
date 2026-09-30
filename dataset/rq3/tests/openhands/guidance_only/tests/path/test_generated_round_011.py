import pytest

from types import SimpleNamespace

from openhands.agenthub.browsing_agent import browsing_agent as mod

# Test doubles and helpers
class DummyBrowseInteractiveAction:
    def __init__(self, browser_actions=None, browsergym_send_msg_to_user=None):
        self.browser_actions = browser_actions
        self.browsergym_send_msg_to_user = browsergym_send_msg_to_user

class DummyMessageAction:
    def __init__(self, content=None, source=None):
        # used both as an event type and as a returned action
        self.content = content
        self.source = source

class DummyAgentFinishAction:
    def __init__(self, outputs=None):
        self.outputs = outputs

class DummyBrowserOutputObservation:
    def __init__(self, *, error=False, last_browser_action=None, url='', axtree_object=None, extra_element_properties=None):
        self.error = error
        self.last_browser_action = last_browser_action
        self.url = url
        self.axtree_object = axtree_object
        self.extra_element_properties = extra_element_properties

class DummyEventSource:
    AGENT = 'agent'

class DummyState:
    def __init__(self, view, inputs=None, intent=None):
        self.view = view
        self.inputs = inputs or {'task': 'default task'}
        # intent is a tuple (goal, other)
        self._intent = intent if intent is not None else (None, None)

    def get_current_user_intent(self):
        return self._intent

class DummyLLM:
    def __init__(self):
        self.last_call = None

    def completion(self, *, messages, stop=None):
        # record call for assertions and return a deterministic sentinel
        self.last_call = {'messages': messages, 'stop': stop}
        return {'text': 'model-response'}

class DummyResponseParser:
    def __init__(self):
        self.last_parsed = None

    def parse(self, response):
        self.last_parsed = response
        return 'PARSED:' + str(response)

class DummyActionSpace:
    def describe(self, with_long_description=False, with_examples=True):
        return 'ACTION_SPACE_DESCRIPTION'

# Monkeypatch common module-level symbols for deterministic behavior
@pytest.fixture(autouse=True)
def patch_module_symbols(monkeypatch):
    # Replace classes and helpers used inside step with test doubles
    monkeypatch.setattr(mod, 'BrowseInteractiveAction', DummyBrowseInteractiveAction, raising=False)
    monkeypatch.setattr(mod, 'MessageAction', DummyMessageAction, raising=False)
    monkeypatch.setattr(mod, 'AgentFinishAction', DummyAgentFinishAction, raising=False)
    monkeypatch.setattr(mod, 'BrowserOutputObservation', DummyBrowserOutputObservation, raising=False)
    # CRITICAL: also patch Observation so isinstance checks succeed for our dummy observation
    monkeypatch.setattr(mod, 'Observation', DummyBrowserOutputObservation, raising=False)
    monkeypatch.setattr(mod, 'EventSource', DummyEventSource, raising=False)

    # Patch functions that might touch external logic
    monkeypatch.setattr(mod, 'get_error_prefix', lambda lb: 'ERR_PREFIX:', raising=False)
    monkeypatch.setattr(mod, 'get_system_message', lambda goal, action_space: f'SYS MSG: {goal} | {action_space}', raising=False)
    monkeypatch.setattr(mod, 'get_prompt', lambda ep, url, axt, prev: f'PROMPT|{ep}|{url}|{axt}|{prev}', raising=False)

    # By default have flatten_axtree_to_str behave deterministically
    monkeypatch.setattr(mod, 'flatten_axtree_to_str', lambda *args, **kwargs: 'AXTREE_TXT', raising=False)

    yield

# Helper to construct a BrowsingAgent instance bypassing real init
def make_agent():
    agent = mod.BrowsingAgent.__new__(mod.BrowsingAgent)
    agent.error_accumulator = 0
    agent.action_space = DummyActionSpace()
    agent.llm = DummyLLM()
    agent.response_parser = DummyResponseParser()
    return agent


def test_eval_mode_noop_round_011(monkeypatch):
    # EVAL_MODE True and state.view length == 1 should return noop BrowseInteractiveAction
    monkeypatch.setattr(mod, 'EVAL_MODE', True, raising=False)
    agent = make_agent()

    state = DummyState(view=[object()])

    result = agent.step(state)

    # Expect the BrowseInteractiveAction double with browser_actions set to noop()
    assert isinstance(result, DummyBrowseInteractiveAction)
    assert result.browser_actions == 'noop()'


def test_agent_finish_on_agent_message_round_011(monkeypatch):
    # If the state view contains a MessageAction whose source == EventSource.AGENT,
    # BrowsingAgent.step should return AgentFinishAction with the content
    monkeypatch.setattr(mod, 'EVAL_MODE', False, raising=False)
    agent = make_agent()

    msg = DummyMessageAction(content='final reply', source=DummyEventSource.AGENT)
    state = DummyState(view=[msg])

    res = agent.step(state)

    assert isinstance(res, DummyAgentFinishAction)
    assert res.outputs == {'content': 'final reply'}


def test_last_action_send_msg_round_011(monkeypatch):
    # If the last BrowseInteractiveAction has browsergym_send_msg_to_user, step returns a MessageAction containing it
    monkeypatch.setattr(mod, 'EVAL_MODE', False, raising=False)
    agent = make_agent()

    last_action = DummyBrowseInteractiveAction(browser_actions='x', browsergym_send_msg_to_user='hello-user')
    state = DummyState(view=[last_action])

    res = agent.step(state)

    # The function returns a MessageAction constructed with the send_msg_to_user string
    assert isinstance(res, DummyMessageAction)
    assert res.content == 'hello-user'


def test_browser_output_too_many_errors_round_011(monkeypatch):
    # When a BrowserOutputObservation reports error and error_accumulator increases beyond 5,
    # the agent returns a MessageAction with a failure message
    monkeypatch.setattr(mod, 'EVAL_MODE', False, raising=False)
    agent = make_agent()
    agent.error_accumulator = 5  # will be incremented to 6 inside step

    obs = DummyBrowserOutputObservation(error=True, last_browser_action='click()')
    state = DummyState(view=[obs])

    res = agent.step(state)

    assert isinstance(res, DummyMessageAction)
    assert res.content == 'Too many errors encountered. Task failed.'


def test_flatten_axtree_exception_round_011(monkeypatch):
    # If flatten_axtree_to_str raises, the agent should catch and return an error MessageAction
    monkeypatch.setattr(mod, 'EVAL_MODE', False, raising=False)
    # patch flatten to raise
    def _raise(*args, **kwargs):
        raise RuntimeError('boom')
    monkeypatch.setattr(mod, 'flatten_axtree_to_str', _raise, raising=False)

    agent = make_agent()

    obs = DummyBrowserOutputObservation(error=False, last_browser_action=None, url='http://x')
    state = DummyState(view=[obs])

    res = agent.step(state)

    assert isinstance(res, DummyMessageAction)
    assert res.content == 'Error encountered when browsing.'


def test_normal_flow_calls_llm_and_parse_round_011(monkeypatch):
    # Full flow where there's a BrowserOutputObservation without error and flatten works,
    # ensures that the LLM completion is called with the constructed messages and response_parser.parse is used
    monkeypatch.setattr(mod, 'EVAL_MODE', False, raising=False)
    agent = make_agent()

    # Observation without error so we go through prompt/system-msg construction and LLM call
    obs = DummyBrowserOutputObservation(error=False, last_browser_action=None, url='http://ok', axtree_object={'a': 1}, extra_element_properties=None)
    state = DummyState(view=[obs], inputs={'task': 'my task'})

    result = agent.step(state)

    # result should be whatever the parser returned; we expect our DummyResponseParser prefix
    assert result == 'PARSED:{"text": "model-response"}' or result == "PARSED:{'text': 'model-response'}"

    # Also ensure LLM was invoked and the messages assembled include system and user messages
    assert agent.llm.last_call is not None
    messages = agent.llm.last_call['messages']
    # messages should be a list and contain Message-like objects created by the module
    assert isinstance(messages, list)
    # There should be a system message and a user message appended in that order
    assert messages[0].role == 'system'
    assert messages[1].role == 'user'
