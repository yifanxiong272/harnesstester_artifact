# file: openhands/agenthub/visualbrowsing_agent/visualbrowsing_agent.py:187-317
# asked: {"lines": [200, 201, 202, 203, 204, 205, 206, 207, 208, 210, 214, 215, 218, 219, 220, 221, 222, 224, 225, 227, 228, 229, 231, 232, 237, 238, 240, 242, 243, 244, 246, 247, 248, 249, 250, 251, 253, 254, 255, 256, 258, 259, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 272, 273, 274, 275, 277, 278, 279, 281, 282, 283, 284, 285, 287, 288, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 302, 304, 306, 308, 309, 311, 312, 313, 314, 317], "branches": [[210, 214], [210, 218], [218, 219], [218, 231], [219, 220], [219, 222], [222, 224], [222, 225], [225, 218], [225, 227], [227, 228], [227, 229], [231, 232], [231, 236], [236, 240], [236, 242], [243, 244], [243, 279], [244, 246], [244, 253], [247, 248], [247, 253], [249, 250], [249, 253], [254, 255], [254, 258], [281, 282], [281, 283], [290, 291], [290, 292], [293, 294], [293, 295]]}
# gained: {"lines": [200, 201, 202, 203, 204, 205, 206, 207, 208, 210, 214, 215, 218, 219, 220, 221, 222, 224, 225, 227, 229, 231, 232, 237, 238, 240, 242, 243, 244, 246, 247, 248, 249, 250, 251, 253, 254, 255, 256, 258, 259, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 272, 273, 274, 275, 277, 278, 279, 281, 282, 283, 284, 285, 287, 288, 290, 292, 293, 295, 296, 297, 298, 299, 300, 302, 304, 306, 308, 309, 311, 312, 313, 314, 317], "branches": [[210, 214], [210, 218], [218, 219], [218, 231], [219, 220], [219, 222], [222, 224], [222, 225], [225, 227], [227, 229], [231, 232], [236, 240], [236, 242], [243, 244], [244, 246], [244, 253], [247, 248], [249, 250], [254, 255], [281, 282], [290, 292], [293, 295]]}

import types
import pytest

from openhands.events.action import BrowseInteractiveAction, MessageAction, AgentFinishAction
from openhands.events.observation.browse import BrowserOutputObservation
from openhands.events.event import EventSource

import openhands.agenthub.visualbrowsing_agent.visualbrowsing_agent as vbmod
from openhands.agenthub.visualbrowsing_agent.visualbrowsing_agent import VisualBrowsingAgent


class DummyState:
    def __init__(self, view, inputs=None, intent=None):
        self.view = view
        self.inputs = inputs or {}
        self._intent = intent

    def get_current_user_intent(self):
        if self._intent is not None:
            return self._intent
        return (None, [])


def make_agent_without_init():
    # Create instance without running __init__
    agent = VisualBrowsingAgent.__new__(VisualBrowsingAgent)
    # Provide minimal attributes used in step for controlled tests
    agent.action_prompt = "ACTION_PROMPT"
    agent.hints = "HINTS"
    agent.abstract_example = "ABSTRACT_EX"
    agent.concrete_example = "CONCRETE_EX"
    agent.error_accumulator = 0
    # Provide a dummy llm and response_parser which can be monkeypatched per-test
    agent.llm = types.SimpleNamespace(completion=lambda **kwargs: {"resp": "ok"})
    agent.response_parser = types.SimpleNamespace(parse=lambda resp: MessageAction(content="parsed"))
    return agent


def test_step_returns_noop_when_single_view_item():
    agent = make_agent_without_init()
    state = DummyState(view=[object()])  # length 1 triggers noop path

    action = agent.step(state)
    assert isinstance(action, BrowseInteractiveAction)
    assert action.browser_actions == 'noop(1000)'
    assert action.return_axtree is True


def test_step_returns_messageaction_when_last_action_sends_msg_to_user():
    agent = make_agent_without_init()
    # First noop then an action that requests sending a message to user
    noop = BrowseInteractiveAction(browser_actions='noop(1000)')
    send = BrowseInteractiveAction(browser_actions="click('1')", browsergym_send_msg_to_user='hello-user')
    state = DummyState(view=[noop, send])

    action = agent.step(state)
    assert isinstance(action, MessageAction)
    assert action.content == 'hello-user'


def test_step_returns_agent_finish_when_agent_sent_message_event(monkeypatch):
    agent = make_agent_without_init()
    noop = BrowseInteractiveAction(browser_actions='noop(1000)')
    msg_event = MessageAction(content='done')
    # Monkeypatch the MessageAction.source property to simulate AGENT source
    monkeypatch.setattr(MessageAction, 'source', property(lambda self: EventSource.AGENT))
    state = DummyState(view=[noop, msg_event])

    action = agent.step(state)
    assert isinstance(action, AgentFinishAction)
    assert action.outputs == {'content': 'done'}


def test_error_prefix_too_many_errors_bails_out_immediately(monkeypatch):
    agent = make_agent_without_init()
    # Set accumulator already high so the next error increments it beyond threshold
    agent.error_accumulator = 6

    # Create BrowserOutputObservation with error True (include required 'content' arg)
    noop = BrowseInteractiveAction(browser_actions='noop(1000)')
    last_obs = BrowserOutputObservation(content='c', url='u', trigger_by_action='t', error=True)
    state = DummyState(view=[noop, last_obs], inputs={'task': 'a task'})

    # Monkeypatch get_error_prefix to return a non-empty prefix so the accumulator increments
    monkeypatch.setattr(vbmod, 'get_error_prefix', lambda obs: 'ERR_PREFIX')
    # Other functions shouldn't be called because early return will occur; still safe to set them
    monkeypatch.setattr(vbmod, 'get_history_prompt', lambda prev: '')
    action = agent.step(state)
    assert isinstance(action, MessageAction)
    assert 'Too many errors encountered' in action.content


def test_flatten_axtree_exception_returns_error_message(monkeypatch):
    agent = make_agent_without_init()
    # normal accumulator
    agent.error_accumulator = 0

    noop = BrowseInteractiveAction(browser_actions='noop(1000)')
    # Provide a BrowserOutputObservation with no error to skip error_prefix path
    last_obs = BrowserOutputObservation(content='c', url='u', trigger_by_action='t', error=False)
    state = DummyState(view=[noop, last_obs], inputs={'task': 'a task'})

    # Ensure get_error_prefix returns empty so we proceed to flatten axtree
    monkeypatch.setattr(vbmod, 'get_error_prefix', lambda obs: '')
    monkeypatch.setattr(vbmod, 'get_history_prompt', lambda prev: 'HIST')
    monkeypatch.setattr(vbmod, 'get_tabs', lambda obs: 'TABS')
    # Make flatten_axtree_to_str raise to hit the exception handling branch
    def _raise(*args, **kwargs):
        raise RuntimeError("boom")
    monkeypatch.setattr(vbmod, 'flatten_axtree_to_str', _raise)

    action = agent.step(state)
    assert isinstance(action, MessageAction)
    assert action.content == 'Error encountered when browsing.'


def test_full_path_calls_llm_and_parses_response(monkeypatch):
    agent = make_agent_without_init()

    noop = BrowseInteractiveAction(browser_actions='noop(1000)')
    last_obs = BrowserOutputObservation(content='c', url='u', trigger_by_action='t', error=False, focused_element_bid='42', set_of_marks='marks')
    state = DummyState(view=[noop, last_obs], inputs={'task': 'my task'}, intent=(None, []))

    # Monkeypatch helpers used to build prompts and axtree processing
    monkeypatch.setattr(vbmod, 'get_history_prompt', lambda prev: 'HISTORY_PROMPT')
    monkeypatch.setattr(vbmod, 'get_error_prefix', lambda obs: '')
    monkeypatch.setattr(vbmod, 'get_tabs', lambda obs: 'TABTXT')
    monkeypatch.setattr(vbmod, 'flatten_axtree_to_str', lambda *args, **kwargs: 'AXTREE_TXT')
    monkeypatch.setattr(vbmod, 'get_axtree', lambda axtree_txt='': axtree_txt)
    monkeypatch.setattr(vbmod, 'create_goal_prompt', lambda goal, images: ('GOAL_TXT', []))
    monkeypatch.setattr(vbmod, 'create_observation_prompt', lambda a, b, c, d, e: ('OBS_TXT', None))

    # Spy on llm.completion being called and set response
    captured = {}
    def fake_completion(messages, temperature, stop):
        captured['messages'] = messages
        captured['temperature'] = temperature
        captured['stop'] = stop
        return {'fake': 'response'}
    agent.llm = types.SimpleNamespace(completion=fake_completion)
    # response parser should be called and its return should be forwarded
    agent.response_parser = types.SimpleNamespace(parse=lambda resp: MessageAction(content='final-action'))

    action = agent.step(state)
    assert isinstance(action, MessageAction)
    assert action.content == 'final-action'
    # verify that llm.completion was invoked with messages containing a system and a user message
    assert 'messages' in captured
    msgs = captured['messages']
    # there should be at least two messages appended: system and user
    assert any(getattr(m, "role", None) == 'system' for m in msgs)
    assert any(getattr(m, "role", None) == 'user' for m in msgs)
