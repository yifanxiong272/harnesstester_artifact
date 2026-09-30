import types
import pytest

from openhands.agenthub.browsing_agent import browsing_agent as ba

# --- Fake/test helper classes to monkeypatch module-level names ---
class FakeBrowseInteractiveAction:
    def __init__(self, browser_actions='', browsergym_send_msg_to_user=None):
        self.browser_actions = browser_actions
        self.browsergym_send_msg_to_user = browsergym_send_msg_to_user

class FakeMessageAction:
    def __init__(self, content=None, source=None):
        # In real code MessageAction may be used both as an event with .source and as a return value with content
        self.content = content
        self.source = source

class FakeObservation:
    pass

class FakeBrowserOutputObservation(FakeObservation):
    def __init__(self, error=False, url='', last_browser_action=None, axtree_object=None, extra_element_properties=None):
        self.error = error
        self.url = url
        self.last_browser_action = last_browser_action
        self.axtree_object = axtree_object
        self.extra_element_properties = extra_element_properties

class DummyEventSource:
    AGENT = 'agent'

class DummyState:
    def __init__(self, view, inputs=None, current_intent=(None, None)):
        self.view = view
        self.inputs = inputs or {'task': 'default task'}
        self._current_intent = current_intent

    def get_current_user_intent(self):
        return self._current_intent

# Helper to build a minimal agent object without running __init__
def make_agent():
    agent = object.__new__(ba.BrowsingAgent)
    # simple action_space with describe method
    class AS:
        def describe(self, with_long_description=False, with_examples=True):
            return 'ACTIONSPEC'
    agent.action_space = AS()

    # simple llm and response_parser default behavior
    class LLM:
        def completion(self, messages=None, stop=None):
            return {'mocked': True}
    class RP:
        def parse(self, resp):
            return resp

    agent.llm = LLM()
    agent.response_parser = RP()
    agent.error_accumulator = 0
    return agent

# --- Tests ---

def test_eval_mode_noop_round_011():
    """When EVAL_MODE is True and the state.view contains a single entry,
    the agent should return a noop BrowseInteractiveAction (browser_actions == 'noop()').
    """
    # Monkeypatch module-level classes and flags
    ba.BrowseInteractiveAction = FakeBrowseInteractiveAction
    ba.MessageAction = FakeMessageAction
    ba.BrowserOutputObservation = FakeBrowserOutputObservation
    ba.Observation = FakeObservation
    ba.EventSource = DummyEventSource

    # set EVAL_MODE True to hit the early return branch at lines ~160-164
    ba.EVAL_MODE = True

    state = DummyState(view=[object()])
    agent = make_agent()

    res = ba.BrowsingAgent.step(agent, state)

    assert isinstance(res, FakeBrowseInteractiveAction)
    assert getattr(res, 'browser_actions') == 'noop()'


def test_browser_send_msg_to_user_round_011():
    """If the last BrowseInteractiveAction has browsergym_send_msg_to_user set,
    the agent should immediately return a MessageAction with that content.
    This covers the branch around lines ~182-186.
    """
    ba.BrowseInteractiveAction = FakeBrowseInteractiveAction
    ba.MessageAction = FakeMessageAction
    ba.BrowserOutputObservation = FakeBrowserOutputObservation
    ba.Observation = FakeObservation
    ba.EventSource = DummyEventSource

    ba.EVAL_MODE = False

    # Build a BrowseInteractiveAction with a user message to send
    last_action = FakeBrowseInteractiveAction(browser_actions='x', browsergym_send_msg_to_user='hello user')

    state = DummyState(view=[last_action])
    agent = make_agent()

    res = ba.BrowsingAgent.step(agent, state)

    assert isinstance(res, FakeMessageAction)
    assert res.content == 'hello user'


def test_flatten_exception_round_011():
    """If flatten_axtree_to_str raises, the agent should catch it and
    return a MessageAction with the error message. This covers the try/except
    at lines ~199-209.
    """
    # Monkeypatch classes and functions
    ba.BrowseInteractiveAction = FakeBrowseInteractiveAction
    ba.MessageAction = FakeMessageAction
    ba.BrowserOutputObservation = FakeBrowserOutputObservation
    ba.Observation = FakeObservation
    ba.EventSource = DummyEventSource

    ba.EVAL_MODE = False

    # Make flatten_axtree_to_str raise to trigger the exception handling branch
    def fake_flatten_raise(axtree_object, extra_properties=None, with_clickable=True, filter_visible_only=True):
        raise RuntimeError('flatten failed')

    ba.flatten_axtree_to_str = fake_flatten_raise

    # Create an observation that will be recognized as Observation (and also BrowserOutputObservation type)
    last_obs = FakeBrowserOutputObservation(
        error=False,
        url='http://example',
        axtree_object={'dummy': True},
        extra_element_properties=None,
    )

    state = DummyState(view=[last_obs])
    agent = make_agent()

    res = ba.BrowsingAgent.step(agent, state)

    assert isinstance(res, FakeMessageAction)
    assert res.content == 'Error encountered when browsing.'


def test_full_llm_parse_round_011():
    """Full path: successfully flatten axtree, build messages, call llm.completion,
    and return response_parser.parse(response). This covers the tail of the
    function around lines ~213-230.
    """
    ba.BrowseInteractiveAction = FakeBrowseInteractiveAction
    ba.MessageAction = FakeMessageAction
    ba.BrowserOutputObservation = FakeBrowserOutputObservation
    ba.Observation = FakeObservation
    ba.EventSource = DummyEventSource

    ba.EVAL_MODE = False

    # Flatten returns a deterministic string
    def fake_flatten_ok(axtree_object, extra_properties=None, with_clickable=True, filter_visible_only=True):
        return 'AXTREE_TEXT'

    ba.flatten_axtree_to_str = fake_flatten_ok

    # Prepare observation
    last_obs = FakeBrowserOutputObservation(error=False, url='http://ok', axtree_object={'ok': True}, extra_element_properties=None)

    # Build state so get_current_user_intent returns (None, None) to force using state.inputs['task']
    state = DummyState(view=[last_obs], inputs={'task': 'search for X'}, current_intent=(None, None))

    # Build agent and stub llm and response_parser to verify pass-through
    agent = make_agent()

    class LLMStub:
        def completion(self, messages=None, stop=None):
            # Return an object that response_parser.parse can interpret
            return {'resp_text': 'MODEL_OUTPUT'}
    final_action = FakeBrowseInteractiveAction(browser_actions='do_final')

    class RPStub:
        def parse(self, resp):
            # verify we get the model output dict we expected
            assert resp == {'resp_text': 'MODEL_OUTPUT'}
            return final_action

    agent.llm = LLMStub()
    agent.response_parser = RPStub()

    res = ba.BrowsingAgent.step(agent, state)

    # The parse result should pass through exactly
    assert res is final_action
