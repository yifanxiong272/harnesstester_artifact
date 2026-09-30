import importlib
import types
import pytest

MODULE_PATH = 'openhands.agenthub.visualbrowsing_agent.visualbrowsing_agent'


class DummyBrowseInteractiveAction:
    def __init__(self, browser_actions=None, return_axtree=None, browsergym_send_msg_to_user=None):
        self.browser_actions = browser_actions
        self.return_axtree = return_axtree
        self.browsergym_send_msg_to_user = browsergym_send_msg_to_user


class DummyMessageAction:
    def __init__(self, content=None, source=None):
        self.content = content
        self.source = source


class DummyAgentFinishAction:
    def __init__(self, outputs=None):
        self.outputs = outputs


class DummyObservation:
    def __init__(self):
        pass


class DummyBrowserOutputObservation(DummyObservation):
    def __init__(self, *, error=False, axtree_object=None, extra_element_properties=None, focused_element_bid=None, set_of_marks=None):
        super().__init__()
        self.error = error
        self.axtree_object = axtree_object
        self.extra_element_properties = extra_element_properties
        self.focused_element_bid = focused_element_bid
        self.set_of_marks = set_of_marks


class DummyTextContent:
    def __init__(self, text=None, type=None):
        self.text = text
        self.type = type


class DummyImageContent:
    def __init__(self, image_urls=None):
        self.image_urls = image_urls


class DummyMessage:
    def __init__(self, role=None, content=None):
        self.role = role
        self.content = content


class DummyEventSource:
    AGENT = 'agent'


class DummyLLM:
    def __init__(self):
        self.last_call = None

    def completion(self, *, messages, temperature, stop):
        # Record what messages were passed for assertions in tests
        self.last_call = dict(messages=messages, temperature=temperature, stop=stop)
        # return a deterministic fake response object
        return {'fake': 'response'}


class DummyResponseParser:
    def __init__(self, to_return):
        self.to_return = to_return
        self.called_with = None

    def parse(self, response):
        self.called_with = response
        return self.to_return


class FakeState:
    def __init__(self, view, inputs=None, current_intent=(None, [])):
        self.view = view
        self.inputs = inputs or {'task': 'default task'}
        self._intent = current_intent

    def get_current_user_intent(self):
        return self._intent


@pytest.fixture(autouse=True)
def patch_module(monkeypatch):
    """Patch the names in the module under test with deterministic dummy types and functions.

    Each test can further monkeypatch to change behavior.
    """
    mod = importlib.import_module(MODULE_PATH)
    # Replace classes used in isinstance checks and return values
    monkeypatch.setattr(mod, 'BrowseInteractiveAction', DummyBrowseInteractiveAction)
    monkeypatch.setattr(mod, 'MessageAction', DummyMessageAction)
    monkeypatch.setattr(mod, 'AgentFinishAction', DummyAgentFinishAction)
    monkeypatch.setattr(mod, 'Observation', DummyObservation)
    monkeypatch.setattr(mod, 'BrowserOutputObservation', DummyBrowserOutputObservation)
    monkeypatch.setattr(mod, 'TextContent', DummyTextContent)
    monkeypatch.setattr(mod, 'ImageContent', DummyImageContent)
    monkeypatch.setattr(mod, 'Message', DummyMessage)
    monkeypatch.setattr(mod, 'EventSource', DummyEventSource)

    # Patch helper functions to deterministic defaults; individual tests override as needed
    monkeypatch.setattr(mod, 'get_history_prompt', lambda prev_actions: 'HISTORY')
    monkeypatch.setattr(mod, 'get_error_prefix', lambda obs: '')
    monkeypatch.setattr(mod, 'flatten_axtree_to_str', lambda a, extra_properties, with_visible, with_clickable, with_center_coords, with_bounding_box_coords, filter_visible_only, filter_with_bid_only, filter_som_only: 'AXTREE')
    monkeypatch.setattr(mod, 'get_axtree', lambda axtree_txt: axtree_txt + '_GOT')
    monkeypatch.setattr(mod, 'get_tabs', lambda obs: 'TABS')
    monkeypatch.setattr(mod, 'create_goal_prompt', lambda goal, image_urls: ('GOAL_TXT', image_urls or []))
    monkeypatch.setattr(mod, 'create_observation_prompt', lambda axtree_txt, tabs, focused_element, error_prefix, set_of_marks: ('OBS_TXT', None))

    yield


def test_noop_initial_view_round_004():
    """When state.view has length 1, a BrowseInteractiveAction noop is immediately returned."""
    mod = importlib.import_module(MODULE_PATH)
    # one event -> triggers initial noop return
    state = FakeState(view=[object()], inputs={'task': 't'})

    # instantiate agent and call step
    agent = mod.VisualBrowsingAgent.__new__(mod.VisualBrowsingAgent)
    # Minimal attributes expected by step: llm and response_parser exist but won't be used
    agent.llm = DummyLLM()
    agent.response_parser = DummyResponseParser(None)
    # Ensure reset or other init fields are present
    agent.error_accumulator = 0
    agent.action_prompt = 'A'
    agent.hints = 'H'
    agent.abstract_example = 'AE'
    agent.concrete_example = 'CE'

    result = mod.VisualBrowsingAgent.step(agent, state)
    assert isinstance(result, DummyBrowseInteractiveAction)
    assert result.browser_actions == 'noop(1000)'
    assert result.return_axtree is True


def test_agent_finish_on_agent_message_round_004():
    """If a MessageAction from the agent is in the view, AgentFinishAction is returned with its content."""
    mod = importlib.import_module(MODULE_PATH)
    # create a MessageAction event coming from agent
    msg = DummyMessageAction(content='done', source=DummyEventSource.AGENT)
    # include a preceding object so len(view) != 1
    state = FakeState(view=[object(), msg], inputs={'task': 't'})

    agent = mod.VisualBrowsingAgent.__new__(mod.VisualBrowsingAgent)
    agent.llm = DummyLLM()
    agent.response_parser = DummyResponseParser(None)
    agent.error_accumulator = 0
    agent.action_prompt = 'A'
    agent.hints = 'H'
    agent.abstract_example = 'AE'
    agent.concrete_example = 'CE'

    result = mod.VisualBrowsingAgent.step(agent, state)
    assert isinstance(result, DummyAgentFinishAction)
    # AgentFinishAction was constructed with outputs containing the message content
    assert result.outputs == {'content': 'done'}


def test_message_after_browser_send_msg_round_004():
    """If the last BrowseInteractiveAction has browsergym_send_msg_to_user, a MessageAction with that text is returned."""
    mod = importlib.import_module(MODULE_PATH)
    # first noop-like BrowseInteractiveAction, then one with browsergym_send_msg_to_user
    first = DummyBrowseInteractiveAction(browser_actions='noop(1000)', return_axtree=True)
    second = DummyBrowseInteractiveAction(browsergym_send_msg_to_user='user message')
    state = FakeState(view=[first, second], inputs={'task': 't'})

    agent = mod.VisualBrowsingAgent.__new__(mod.VisualBrowsingAgent)
    agent.llm = DummyLLM()
    agent.response_parser = DummyResponseParser(None)
    agent.error_accumulator = 0
    agent.action_prompt = 'A'
    agent.hints = 'H'
    agent.abstract_example = 'AE'
    agent.concrete_example = 'CE'

    result = mod.VisualBrowsingAgent.step(agent, state)
    # Because we patched MessageAction in module to DummyMessageAction, result should be that
    assert isinstance(result, DummyMessageAction)
    assert result.content == 'user message'


def test_too_many_errors_accumulator_round_004(monkeypatch):
    """When get_error_prefix returns a non-empty prefix and error_accumulator exceeds threshold, a failure MessageAction is returned."""
    mod = importlib.import_module(MODULE_PATH)
    # create a browser output observation with an error
    bo = DummyBrowserOutputObservation(error=True, axtree_object=None, extra_element_properties=None)

    # prefix non-empty triggers increment
    monkeypatch.setattr(mod, 'get_error_prefix', lambda obs: 'RECOVER')

    # add one noop-like browse action first to avoid len(view)==1 behavior
    first = DummyBrowseInteractiveAction(browser_actions='noop(1000)', return_axtree=True)
    state = FakeState(view=[first, bo], inputs={'task': 't'})

    agent = mod.VisualBrowsingAgent.__new__(mod.VisualBrowsingAgent)
    agent.llm = DummyLLM()
    agent.response_parser = DummyResponseParser(None)
    agent.error_accumulator = 5  # after increment becomes 6 -> triggers too-many-errors
    agent.action_prompt = 'A'
    agent.hints = 'H'
    agent.abstract_example = 'AE'
    agent.concrete_example = 'CE'

    result = mod.VisualBrowsingAgent.step(agent, state)
    assert isinstance(result, DummyMessageAction)
    assert result.content == 'Too many errors encountered. Task failed.'


def test_flatten_exception_returns_error_message_round_004(monkeypatch):
    """If flatten_axtree_to_str raises, the agent returns an error MessageAction before calling llm."""
    mod = importlib.import_module(MODULE_PATH)
    # create browser output observation with no error prefix so it reaches flatten call
    bo = DummyBrowserOutputObservation(error=False, axtree_object={'bad': 'tree'}, extra_element_properties={'p': 1})

    # cause flatten to raise
    def raise_flatten(*args, **kwargs):
        raise RuntimeError('boom')

    monkeypatch.setattr(mod, 'flatten_axtree_to_str', raise_flatten)

    first = DummyBrowseInteractiveAction(browser_actions='noop(1000)', return_axtree=True)
    state = FakeState(view=[first, bo], inputs={'task': 't'})

    agent = mod.VisualBrowsingAgent.__new__(mod.VisualBrowsingAgent)
    agent.llm = DummyLLM()
    agent.response_parser = DummyResponseParser(None)
    agent.error_accumulator = 0
    agent.action_prompt = 'A'
    agent.hints = 'H'
    agent.abstract_example = 'AE'
    agent.concrete_example = 'CE'

    result = mod.VisualBrowsingAgent.step(agent, state)
    assert isinstance(result, DummyMessageAction)
    assert result.content == 'Error encountered when browsing.'


def test_normal_flow_calls_llm_and_parse_round_004(monkeypatch):
    """Full non-error flow: verify the message assembly and that llm and response_parser are called and returned action is forwarded."""
    mod = importlib.import_module(MODULE_PATH)

    # BrowserOutputObservation that does not error
    bo = DummyBrowserOutputObservation(error=False, axtree_object={'tree': 1}, extra_element_properties=None, focused_element_bid=None, set_of_marks={'m'})

    # ensure helper functions return expected pieces
    monkeypatch.setattr(mod, 'get_error_prefix', lambda obs: '')
    monkeypatch.setattr(mod, 'flatten_axtree_to_str', lambda *args, **kwargs: 'AXTREE_RAW')
    monkeypatch.setattr(mod, 'get_axtree', lambda txt: 'AXTREE_PROCESSED')
    monkeypatch.setattr(mod, 'get_tabs', lambda obs: 'TABZ')
    monkeypatch.setattr(mod, 'create_goal_prompt', lambda goal, image_urls: ('GOAL_PROMPT', ['img1']))
    monkeypatch.setattr(mod, 'create_observation_prompt', lambda a, b, c, d, e: ('OBS_PROMPT', 'SOM_IMG'))

    first = DummyBrowseInteractiveAction(browser_actions='noop(1000)', return_axtree=True)
    state = FakeState(view=[first, bo], inputs={'task': 't'}, current_intent=(None, ['img1']))

    agent = mod.VisualBrowsingAgent.__new__(mod.VisualBrowsingAgent)
    # attach dummy llm and parser
    dummy_llm = DummyLLM()
    parsed_action = DummyBrowseInteractiveAction(browser_actions='do_something')
    dummy_parser = DummyResponseParser(parsed_action)
    agent.llm = dummy_llm
    agent.response_parser = dummy_parser
    agent.error_accumulator = 0
    agent.action_prompt = 'ACT_PROMPT'
    agent.hints = 'HINTS'
    agent.abstract_example = 'AE'
    agent.concrete_example = 'CE'

    result = mod.VisualBrowsingAgent.step(agent, state)

    # Ensure llm was called with messages that include system and user roles
    assert dummy_llm.last_call is not None
    messages = dummy_llm.last_call['messages']
    assert any(m.role == 'system' for m in messages)
    assert any(m.role == 'user' for m in messages)

    # Ensure parse was called with the llm response and returned value is forwarded
    assert dummy_parser.called_with == {'fake': 'response'}
    assert result is parsed_action
