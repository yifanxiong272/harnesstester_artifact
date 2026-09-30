import types
import pytest

from importlib import import_module

vb = import_module("openhands.agenthub.visualbrowsing_agent.visualbrowsing_agent")

# Lightweight test doubles to patch into the module under test.
class _EventSource:
    AGENT = "agent"

class _Observation:
    pass

class _BrowserOutputObservation(_Observation):
    def __init__(self, *, error=False, focused_element_bid=None, axtree_object=None, extra_element_properties=None, set_of_marks=None):
        self.error = error
        self.focused_element_bid = focused_element_bid
        self.axtree_object = axtree_object
        self.extra_element_properties = extra_element_properties
        self.set_of_marks = set_of_marks

class _BrowseInteractiveAction:
    def __init__(self, browser_actions=None, return_axtree=None, browsergym_send_msg_to_user=None):
        self.browser_actions = browser_actions
        self.return_axtree = return_axtree
        self.browsergym_send_msg_to_user = browsergym_send_msg_to_user

class _MessageAction:
    # Used both as an incoming event (with .source and .content) and as an outgoing action (constructed with a string)
    def __init__(self, *args, **kwargs):
        # If called like MessageAction('some string'), expose .message
        if len(args) == 1 and isinstance(args[0], str) and 'source' not in kwargs and 'content' not in kwargs:
            self.message = args[0]
            self.content = args[0]
            self.source = None
        else:
            self.source = kwargs.get('source', getattr(kwargs.get('content', None), 'source', None))
            # content may be passed positionally
            if args:
                self.content = args[0]
            else:
                self.content = kwargs.get('content')

class _AgentFinishAction:
    def __init__(self, outputs=None):
        self.outputs = outputs

class _Message:
    def __init__(self, *, role, content):
        self.role = role
        self.content = content

class _TextContent:
    def __init__(self, *, text=None, type='text'):
        self.type = type
        self.text = text

class _ImageContent:
    def __init__(self, *, image_urls):
        self.image_urls = image_urls

# Helper small state stub used by tests
class StateStub:
    def __init__(self, view, inputs=None, intent=None):
        self.view = list(view)
        self.inputs = inputs or {}
        # intent: tuple(goal, image_urls)
        self._intent = intent

    def get_current_user_intent(self):
        return self._intent if self._intent is not None else (None, [])


# Patch the module-level symbols used in step to our lightweight test doubles
@pytest.fixture(autouse=True)
def patch_module_symbols(monkeypatch):
    monkeypatch.setattr(vb, "BrowseInteractiveAction", _BrowseInteractiveAction)
    monkeypatch.setattr(vb, "MessageAction", _MessageAction)
    monkeypatch.setattr(vb, "AgentFinishAction", _AgentFinishAction)
    monkeypatch.setattr(vb, "BrowserOutputObservation", _BrowserOutputObservation)
    monkeypatch.setattr(vb, "Observation", _Observation)
    monkeypatch.setattr(vb, "EventSource", _EventSource)
    monkeypatch.setattr(vb, "Message", _Message)
    monkeypatch.setattr(vb, "TextContent", _TextContent)
    monkeypatch.setattr(vb, "ImageContent", _ImageContent)

    # Default simple helper implementations; individual tests may override further
    monkeypatch.setattr(vb, "get_error_prefix", lambda obs: "")
    monkeypatch.setattr(vb, "get_tabs", lambda obs: "[tabs]")
    monkeypatch.setattr(vb, "flatten_axtree_to_str", lambda *a, **k: "<axtree>" )
    monkeypatch.setattr(vb, "get_axtree", lambda axtree_txt=None: axtree_txt)
    monkeypatch.setattr(vb, "get_history_prompt", lambda prev_actions: "history_prompt")
    monkeypatch.setattr(vb, "create_goal_prompt", lambda goal, image_urls: ("goal_txt", list(image_urls)))
    monkeypatch.setattr(vb, "create_observation_prompt", lambda axtree_txt, tabs, focused_element, error_prefix, set_of_marks: ("obs_txt", None))

    yield


def _make_agent():
    # Create a VisualBrowsingAgent without calling its real __init__ to keep deterministic test doubles
    agent = object.__new__(vb.VisualBrowsingAgent)
    # minimal attributes used in step
    agent.error_accumulator = 0
    agent.action_prompt = "ACT_PROMPT"
    agent.hints = "HINTS"
    agent.abstract_example = "ABEX"
    agent.concrete_example = "CONEX"
    # llm and response_parser will be set by specific tests
    agent.llm = types.SimpleNamespace(completion=lambda **kw: {"response": True})
    agent.response_parser = types.SimpleNamespace(parse=lambda r: "PARSED_RESPONSE")
    return agent


def test_len_view_one_round_004():
    # When state.view has length 1 the agent should return a noop BrowseInteractiveAction
    agent = _make_agent()
    state = StateStub(view=[_BrowseInteractiveAction()])

    result = vb.VisualBrowsingAgent.step(agent, state)

    assert isinstance(result, _BrowseInteractiveAction)
    assert result.browser_actions == "noop(1000)"
    assert result.return_axtree is True


def test_agent_finish_on_message_agent_round_004():
    # When encountering a MessageAction with source==AGENT the agent should finish with AgentFinishAction
    agent = _make_agent()

    # first event is a noop BrowseInteractiveAction to emulate prev_actions behavior
    first = _BrowseInteractiveAction()
    # second event is a MessageAction event originating from the agent
    second = _MessageAction(source=_EventSource.AGENT, content="final content")

    state = StateStub(view=[first, second])

    result = vb.VisualBrowsingAgent.step(agent, state)

    assert isinstance(result, _AgentFinishAction)
    assert result.outputs == {"content": "final content"}


def test_error_accumulator_too_many_errors_round_004():
    # If many consecutive errors occur, the agent must return a user-facing failure MessageAction
    agent = _make_agent()
    agent.error_accumulator = 5  # set to threshold so that one more error triggers the branch

    # Make get_error_prefix return non-empty string to simulate recoverable error prompt
    vb.get_error_prefix = lambda obs: "RECOVER"

    # Create a BrowseOutputObservation with error True
    obs = _BrowserOutputObservation(error=True)

    # Prepend a noop BrowseInteractiveAction so prev_actions has at least one entry
    state = StateStub(view=[_BrowseInteractiveAction(), obs])

    result = vb.VisualBrowsingAgent.step(agent, state)

    assert isinstance(result, _MessageAction)
    # The code constructs MessageAction with a single string when failing due to too many errors
    assert getattr(result, "message", None) == "Too many errors encountered. Task failed."


def test_flatten_exception_returns_error_message_round_004():
    # If flatten_axtree_to_str raises, the agent should catch and return the appropriate MessageAction
    agent = _make_agent()
    agent.error_accumulator = 0

    # Ensure no early error path
    vb.get_error_prefix = lambda obs: ""

    # Cause flatten to raise
    def _raise_flatten(*args, **kwargs):
        raise RuntimeError("bad axtree")

    vb.flatten_axtree_to_str = _raise_flatten

    obs = _BrowserOutputObservation(error=False, axtree_object={})
    state = StateStub(view=[_BrowseInteractiveAction(), obs])

    result = vb.VisualBrowsingAgent.step(agent, state)

    assert isinstance(result, _MessageAction)
    assert getattr(result, "message", None) == "Error encountered when browsing."


def test_final_llm_and_response_parser_round_004():
    # Exercise the normal path where the llm is called and response_parser.parse result is returned
    agent = _make_agent()

    # Prepare get_current_user_intent giving None so fallback to state.inputs['task'] is used
    goal_text = "Please find the price"
    state = StateStub(view=[_BrowseInteractiveAction(), _BrowserOutputObservation(error=False, axtree_object={})], inputs={"task": goal_text}, intent=None)

    # Make create_goal_prompt return one image to exercise ImageContent branch
    vb.create_goal_prompt = lambda goal, image_urls: ("GOAL_TXT", ["http://img" ])
    # Let create_observation_prompt return a som screenshot to exercise screenshot branch
    vb.create_observation_prompt = lambda axtree_txt, tabs, focused_element, error_prefix, set_of_marks: ("OBS_TXT", "http://som")

    # Replace llm and parser to validate they are invoked and their values propagated
    called = {}

    def fake_completion(**kwargs):
        # ensure deterministic message structure passed
        called['messages_len'] = len(kwargs['messages'])
        return {"fake": True}

    def fake_parse(response):
        called['parsed'] = True
        return _BrowseInteractiveAction(browser_actions='do_something')

    agent.llm = types.SimpleNamespace(completion=fake_completion)
    agent.response_parser = types.SimpleNamespace(parse=fake_parse)

    result = vb.VisualBrowsingAgent.step(agent, state)

    # Expect the final result returned by response_parser.parse
    assert isinstance(result, _BrowseInteractiveAction)
    assert result.browser_actions == 'do_something'
    # Ensure llm was called and parser used
    assert called.get('messages_len', 0) >= 2
    assert called.get('parsed', False) is True
