import asyncio
from types import SimpleNamespace

import pytest

from browser_use.agent.message_manager import service as svc

# Minimal test helpers to mimic history items and state

class DummyHistoryItem:
    def __init__(self, text: str):
        self._text = text

    def to_string(self):
        return self._text

class DummyState:
    def __init__(self):
        self.last_compaction_step = None
        self.agent_history_items = []
        self.compacted_memory = None
        self.read_state_description = None
        self.compaction_count = 0

class DummyLLM:
    def __init__(self, completion=None, raise_exc=False, record_messages=None):
        self._completion = completion
        self._raise = raise_exc
        # optional list to record passed messages for inspection
        self.record_messages = record_messages

    async def ainvoke(self, messages):
        if self.record_messages is not None:
            self.record_messages.append(messages)
        if self._raise:
            raise RuntimeError("simulated llm error")
        return SimpleNamespace(completion=self._completion)


def make_manager_with_state(state: DummyState, sensitive_data=False):
    # Construct a MessageManager instance without calling its __init__
    mgr = object.__new__(svc.MessageManager)
    mgr.state = state
    mgr.sensitive_data = sensitive_data

    # default filter: return object with .text attribute same as input content
    def default_filter(user_msg):
        return SimpleNamespace(text=getattr(user_msg, 'content', ''))

    mgr._filter_sensitive_data = default_filter
    return mgr


# Tests

def test_early_gates_settings_llm_stepinfo_none_round_027():
    mgr = make_manager_with_state(DummyState())

    # settings None -> immediate False
    result = asyncio.run(mgr.maybe_compact_messages(None, None, None))
    assert result is False

    # settings disabled -> False
    settings = SimpleNamespace(enabled=False)
    result = asyncio.run(mgr.maybe_compact_messages(None, settings, SimpleNamespace(step_number=1)))
    assert result is False

    # llm None -> False
    settings = SimpleNamespace(enabled=True)
    result = asyncio.run(mgr.maybe_compact_messages(None, settings, SimpleNamespace(step_number=1)))
    assert result is False

    # step_info None -> False
    llm = DummyLLM(completion='ok')
    result = asyncio.run(mgr.maybe_compact_messages(llm, settings, None))
    assert result is False


def test_step_cadence_and_char_floor_gates_round_027():
    state = DummyState()
    # last compaction at step 10
    state.last_compaction_step = 10
    # one short history item
    state.agent_history_items = [DummyHistoryItem('short')]
    mgr = make_manager_with_state(state)

    # compact_every_n_steps too large => steps_since < compact_every_n_steps -> False
    settings = SimpleNamespace(enabled=True, compact_every_n_steps=100, trigger_char_count=1, include_read_state=False, summary_max_chars=None, keep_last_items=0)
    llm = DummyLLM(completion='summary')
    # step_number 50 => steps_since = 40 < 100
    result = asyncio.run(mgr.maybe_compact_messages(llm, settings, SimpleNamespace(step_number=50)))
    assert result is False

    # steps ok but history too short for char floor -> False
    settings.compact_every_n_steps = 1
    settings.trigger_char_count = 1000  # large trigger; history remains small
    result = asyncio.run(mgr.maybe_compact_messages(llm, settings, SimpleNamespace(step_number=200)))
    assert result is False


def test_llm_exception_and_empty_response_round_027():
    state = DummyState()
    # make history large enough to pass char floor
    long_text = 'A' * 200
    state.agent_history_items = [DummyHistoryItem(long_text)]
    mgr = make_manager_with_state(state)

    settings = SimpleNamespace(enabled=True, compact_every_n_steps=1, trigger_char_count=10, include_read_state=False, summary_max_chars=None, keep_last_items=0)

    # llm raises -> returns False
    llm_err = DummyLLM(raise_exc=True)
    result = asyncio.run(mgr.maybe_compact_messages(llm_err, settings, SimpleNamespace(step_number=2)))
    assert result is False

    # llm returns empty completion -> returns False
    llm_empty = DummyLLM(completion='')
    result = asyncio.run(mgr.maybe_compact_messages(llm_empty, settings, SimpleNamespace(step_number=3)))
    assert result is False


def test_compaction_truncation_and_keep_last_zero_round_027():
    # This test exercises branches that set compacted_memory, include read state, sensitive data filter, summary truncation,
    # and keep_last_items == 0 path for history trimming.
    state = DummyState()
    # create multiple history items to ensure trimming will be exercised
    state.agent_history_items = [DummyHistoryItem(f'item{i}') for i in range(6)]
    state.compacted_memory = 'previous summary'
    state.read_state_description = 'read-state'
    mgr = make_manager_with_state(state, sensitive_data=False)

    # llm will return a long summary; force truncation by setting summary_max_chars small
    completion_text = 'S' * 50
    recorded_messages = []
    llm = DummyLLM(completion=completion_text, record_messages=recorded_messages)

    settings = SimpleNamespace(
        enabled=True,
        compact_every_n_steps=1,
        trigger_char_count=1,  # pass char floor
        include_read_state=True,
        summary_max_chars=10,
        keep_last_items=0,
    )

    step = SimpleNamespace(step_number=5)
    result = asyncio.run(mgr.maybe_compact_messages(llm, settings, step))
    assert result is True

    # Compacted memory should be truncated and end with an ellipsis character
    assert mgr.state.compacted_memory.endswith('\u2026')
    # compaction count incremented
    assert mgr.state.compaction_count == 1
    # last compaction step updated
    assert mgr.state.last_compaction_step == 5
    # When keep_last_items == 0, agent_history_items should retain only the first item
    assert len(mgr.state.agent_history_items) == 1
    assert mgr.state.agent_history_items[0].to_string() == 'item0'

    # Validate that the messages passed to the llm included the system prompt and a user message payload
    assert recorded_messages, "llm was not invoked or messages were not recorded"
    msgs = recorded_messages[0]
    # expecting a system message then a user message
    assert len(msgs) == 2
    # The second message content should include the previous_compacted_memory marker and agent_history
    user_msg = msgs[1]
    assert '<agent_history>' in getattr(user_msg, 'content', '')
    assert '<previous_compacted_memory>' in getattr(user_msg, 'content', '')


def test_compaction_keep_last_positive_round_027():
    # Test trimming when keep_last_items > 0
    state = DummyState()
    state.agent_history_items = [DummyHistoryItem(f'entry{i}') for i in range(1, 8)]
    mgr = make_manager_with_state(state)

    # llm returns a short summary that does not require truncation
    llm = DummyLLM(completion='short summary')

    settings = SimpleNamespace(
        enabled=True,
        compact_every_n_steps=1,
        trigger_char_count=1,
        include_read_state=False,
        summary_max_chars=None,
        keep_last_items=2,
    )

    step = SimpleNamespace(step_number=10)
    result = asyncio.run(mgr.maybe_compact_messages(llm, settings, step))
    assert result is True

    # After compaction, we should keep the first item and the last 2 items
    kept = [h.to_string() for h in mgr.state.agent_history_items]
    assert kept[0] == 'entry1'
    assert kept[-2:] == ['entry6', 'entry7']
    assert len(kept) == 3


def test_sensitive_data_filter_invoked_round_027():
    # Ensure that when sensitive_data is True the _filter_sensitive_data hook is used and its output applied
    state = DummyState()
    state.agent_history_items = [DummyHistoryItem('sensitive content')]
    mgr = make_manager_with_state(state, sensitive_data=True)

    # Replace the filter with one that records and returns a modified text
    recorded = {}

    def fake_filter(user_msg):
        recorded['seen'] = getattr(user_msg, 'content', '')
        # Return object with .text property altered
        return SimpleNamespace(text='FILTERED_TEXT')

    mgr._filter_sensitive_data = fake_filter

    # LLM that returns a non-empty completion so compaction proceeds
    llm = DummyLLM(completion='ok')

    settings = SimpleNamespace(enabled=True, compact_every_n_steps=1, trigger_char_count=1, include_read_state=False, summary_max_chars=None, keep_last_items=0)
    step = SimpleNamespace(step_number=42)

    result = asyncio.run(mgr.maybe_compact_messages(llm, settings, step))
    assert result is True

    # The filter should have been given a UserMessage-like object content
    assert 'sensitive content' in recorded.get('seen', '')
    # The state.compacted_memory should match the llm completion (no truncation here)
    assert mgr.state.compacted_memory == 'ok'
