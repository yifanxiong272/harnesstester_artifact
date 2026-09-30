import types
import pytest

import openhands.agenthub.browsing_agent.browsing_agent as browsing_agent


class DummyState:
    def __init__(self, view, goal=None, inputs=None):
        self.view = view
        self._goal = goal
        self.inputs = inputs or {}

    def get_current_user_intent(self):
        return (self._goal, None)


# Minimal dummy classes to stand in for framework classes. We will monkeypatch
# these into the browsing_agent module so isinstance checks pass and the
# attributes the step() method expects are present.
class DummyBrowseInteractiveAction:
    def __init__(self, browser_actions=None, browsergym_send_msg_to_user=None):
        self.browser_actions = browser_actions
        self.browsergym_send_msg_to_user = browsergym_send_msg_to_user


class DummyMessageAction:
    def __init__(self, content=None, source=None):
        # browsing_agent.step may call MessageAction(...) with either a str or other
        # values; store in a consistent attribute for assertions
        self.content = content
        self.source = source


class DummyObservation:
    pass


# FIX: ensure DummyBrowserOutputObservation is recognized as an Observation by
# inheriting from DummyObservation so isinstance checks in step() succeed.
class DummyBrowserOutputObservation(DummyObservation):
    def __init__(self, *, error=False, last_browser_action=None, url='', axtree_object=None, extra_element_properties=None):
        self.error = error
        self.last_browser_action = last_browser_action
        self.url = url
        self.axtree_object = axtree_object
        self.extra_element_properties = extra_element_properties


class DummyMessage:
    def __init__(self, role=None, content=None):
        self.role = role
        self.content = content


class DummyTextContent:
    def __init__(self, text):
        self.text = text


class DummyLLM:
    def __init__(self, response):
        self._response = response
        self.received_messages = None

    def completion(self, *, messages, stop=None):
        # capture messages for assertions and return a deterministic raw response
        self.received_messages = messages
        return self._response


class DummyParser:
    def __init__(self, parsed_response):
        self._parsed = parsed_response
        self.received = None

    def parse(self, response):
        self.received = response
        return self._parsed


@pytest.fixture(autouse=True)
def patch_module_classes(monkeypatch):
    # Replace classes and helper functions the step() relies on so tests are
    # deterministic and do not require the full project environment.
    monkeypatch.setattr(browsing_agent, 'BrowseInteractiveAction', DummyBrowseInteractiveAction)
    monkeypatch.setattr(browsing_agent, 'MessageAction', DummyMessageAction)
    monkeypatch.setattr(browsing_agent, 'Observation', DummyObservation)
    monkeypatch.setattr(browsing_agent, 'BrowserOutputObservation', DummyBrowserOutputObservation)

    # Replace message/TextContent builders used to compose prompts
    monkeypatch.setattr(browsing_agent, 'Message', DummyMessage)
    monkeypatch.setattr(browsing_agent, 'TextContent', DummyTextContent)

    # Replace helpers used later in the flow; tests will individually override as needed
    monkeypatch.setattr(browsing_agent, 'get_system_message', lambda goal, action_space: 'SYSTEM_MSG')
    monkeypatch.setattr(browsing_agent, 'get_prompt', lambda error_prefix, cur_url, cur_axtree_txt, prev_action_str: 'PROMPT')
    monkeypatch.setattr(browsing_agent, 'flatten_axtree_to_str', lambda *args, **kwargs: 'AXTREE')

    # Ensure we start each test with a deterministic eval mode flag value (False)
    monkeypatch.setattr(browsing_agent, 'EVAL_MODE', False)

    yield


def make_agent_without_init(parsed_response='PARSED', llm_response='RAW'):
    # Create BrowsingAgent instance without calling its real __init__ to avoid
    # depending on project-wide registries. Populate the attributes used by step().
    agent = object.__new__(browsing_agent.BrowsingAgent)
    agent.error_accumulator = 0

    # action_space.describe might be called by get_system_message; we replaced
    # get_system_message with a stub that ignores it, but set a minimal action_space
    agent.action_space = types.SimpleNamespace(describe=lambda **kwargs: 'DESC')

    # LLM and response parser are deterministic test doubles
    llm = DummyLLM(llm_response)
    parser = DummyParser(parsed_response)
    agent.llm = llm
    agent.response_parser = parser
    return agent, llm, parser


def test_eval_mode_noop_returns_noop_round_011(monkeypatch):
    # Cover branch: if EVAL_MODE and len(state.view) == 1 -> return noop BrowseInteractiveAction
    monkeypatch.setattr(browsing_agent, 'EVAL_MODE', True)

    state = DummyState(view=[object()])
    agent, _, _ = make_agent_without_init()

    result = agent.step(state)

    # The browsing_agent.step should return an instance of BrowseInteractiveAction with noop()
    assert isinstance(result, DummyBrowseInteractiveAction)
    assert result.browser_actions == 'noop()'


def test_last_action_send_msg_returns_message_action_round_011(monkeypatch):
    # Cover branch where the last BrowserInteractiveAction has browsergym_send_msg_to_user set
    monkeypatch.setattr(browsing_agent, 'EVAL_MODE', False)

    send_text = 'Hello user'
    last_action = DummyBrowseInteractiveAction(browser_actions='do()', browsergym_send_msg_to_user=send_text)
    # put an earlier no-op action plus the last action to ensure loop logic processes it
    state = DummyState(view=[DummyBrowseInteractiveAction(browser_actions='noop()'), last_action])

    agent, _, _ = make_agent_without_init()

    result = agent.step(state)

    # Should be a MessageAction containing the send_text
    assert isinstance(result, DummyMessageAction)
    assert result.content == send_text


def test_too_many_errors_returns_failure_message_round_011(monkeypatch):
    # Cover branch where BrowserOutputObservation.error is True and error_accumulator > 5
    monkeypatch.setattr(browsing_agent, 'EVAL_MODE', False)

    # Create a BrowserOutputObservation with error True
    last_obs = DummyBrowserOutputObservation(error=True, last_browser_action='act1')
    state = DummyState(view=[last_obs], goal=None, inputs={'task': 'do the thing'})

    agent, _, _ = make_agent_without_init()
    # set accumulator to 5 so that after increment it will be > 5 and trigger the early return
    agent.error_accumulator = 5

    result = agent.step(state)

    assert isinstance(result, DummyMessageAction)
    assert result.content == 'Too many errors encountered. Task failed.'


def test_flatten_exception_returns_error_message_round_011(monkeypatch):
    # Cover the try/except around flatten_axtree_to_str -> when it raises, we return an error MessageAction
    monkeypatch.setattr(browsing_agent, 'EVAL_MODE', False)

    # Make flatten_axtree_to_str raise
    def raise_on_flatten(*args, **kwargs):
        raise RuntimeError('boom')

    monkeypatch.setattr(browsing_agent, 'flatten_axtree_to_str', raise_on_flatten)

    last_obs = DummyBrowserOutputObservation(error=False, url='http://x', axtree_object={'x': 1})
    state = DummyState(view=[last_obs], goal=None, inputs={'task': 'do it'})

    agent, _, _ = make_agent_without_init()

    result = agent.step(state)

    assert isinstance(result, DummyMessageAction)
    assert result.content == 'Error encountered when browsing.'


def test_llm_response_parsed_round_011(monkeypatch):
    # Cover the full prompt path where goal is None so inputs['task'] is used, and the agent calls llm.completion
    monkeypatch.setattr(browsing_agent, 'EVAL_MODE', False)

    # Prepare a browser output observation with no error, so the code reaches the prompt/llm flow
    last_obs = DummyBrowserOutputObservation(error=False, url='http://example', axtree_object={'a': 1}, extra_element_properties={'p': 1})
    state = DummyState(view=[last_obs], goal=None, inputs={'task': 'some task'})

    # Make get_system_message and get_prompt deterministic and recordable
    recorded = {}

    def fake_system_msg(goal, action_space):
        recorded['system_goal'] = goal
        return 'SYS_MSG'

    def fake_prompt(error_prefix, cur_url, cur_axtree_txt, prev_action_str):
        recorded['prompt_args'] = (error_prefix, cur_url, cur_axtree_txt, prev_action_str)
        return 'USER_PROMPT'

    monkeypatch.setattr(browsing_agent, 'get_system_message', fake_system_msg)
    monkeypatch.setattr(browsing_agent, 'get_prompt', fake_prompt)

    # Create agent with an LLM that returns a raw response and a parser that returns a sentinel action
    agent, llm, parser = make_agent_without_init(parsed_response='PARSED_ACTION', llm_response={'resp': 'ok'})

    result = agent.step(state)

    # Ensure the parser received the raw response from the LLM and that the final parsed action was returned
    assert parser.received == {'resp': 'ok'}
    assert result == 'PARSED_ACTION'

    # Confirm that our get_system_message and get_prompt were called with expected values
    assert recorded['system_goal'] == 'some task'
    # prompt_args should include the cur_url derived from last_obs
    assert recorded['prompt_args'][1] == 'http://example'
