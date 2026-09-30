import pytest
import types
from types import SimpleNamespace
import asyncio

from browser_use.agent.message_manager.service import MessageManager


class DummyHistoryItem:
    def __init__(self, text):
        self._text = text

    def to_string(self):
        return self._text


class DummyLLM:
    def __init__(self, completion=None, raise_exc=False):
        self._completion = completion
        self._raise = raise_exc

    async def ainvoke(self, messages):
        # messages is accepted but not inspected to keep tests deterministic
        if self._raise:
            raise RuntimeError("llm failed")
        return SimpleNamespace(completion=self._completion)


def make_manager(history_texts=None, prev_compacted=None, read_state=None, sensitive=False):
    # Create a bare MessageManager instance without running its __init__
    mgr = object.__new__(MessageManager)
    history_items = [DummyHistoryItem(t) for t in (history_texts or [])]
    mgr.state = SimpleNamespace(
        last_compaction_step=None,
        agent_history_items=history_items,
        compacted_memory=prev_compacted,
        read_state_description=read_state,
        compaction_count=0,
    )
    mgr.sensitive_data = sensitive

    # Provide a simple filter function used when sensitive_data is True
    def fake_filter(msg):
        # return object with .text attribute as expected by code
        return SimpleNamespace(text="[FILTERED]")

    mgr._filter_sensitive_data = fake_filter
    return mgr


@pytest.mark.asyncio
async def test_settings_none_round_028():
    mgr = make_manager()
    llm = DummyLLM(completion="ok")
    step_info = SimpleNamespace(step_number=1)

    # settings is None -> immediate False (lines ~223-224)
    res = await MessageManager.maybe_compact_messages(mgr, None, None, step_info)
    assert res is False


@pytest.mark.asyncio
async def test_llm_none_round_028():
    mgr = make_manager()
    settings = SimpleNamespace(enabled=True)
    step_info = SimpleNamespace(step_number=1)

    # llm is None -> immediate False (lines ~225-226)
    res = await MessageManager.maybe_compact_messages(mgr, None, settings, step_info)
    assert res is False


@pytest.mark.asyncio
async def test_step_info_none_round_028():
    mgr = make_manager()
    settings = SimpleNamespace(enabled=True)
    llm = DummyLLM(completion="ok")

    # step_info is None -> immediate False (lines ~227-228)
    res = await MessageManager.maybe_compact_messages(mgr, llm, settings, None)
    assert res is False


@pytest.mark.asyncio
async def test_steps_since_gate_round_028():
    # steps_since < compact_every_n_steps triggers early return (lines ~231-233)
    mgr = make_manager(history_texts=["a"])
    settings = SimpleNamespace(enabled=True, compact_every_n_steps=5, trigger_char_count=1)
    llm = DummyLLM(completion="ok")
    step_info = SimpleNamespace(step_number=1)  # steps_since = 1

    res = await MessageManager.maybe_compact_messages(mgr, llm, settings, step_info)
    assert res is False


@pytest.mark.asyncio
async def test_char_floor_gate_round_028():
    # Enough steps but history text smaller than trigger_char_count -> False (lines ~236-240)
    mgr = make_manager(history_texts=["short"])
    settings = SimpleNamespace(enabled=True, compact_every_n_steps=1, trigger_char_count=100)
    llm = DummyLLM(completion="ok")
    step_info = SimpleNamespace(step_number=10)

    res = await MessageManager.maybe_compact_messages(mgr, llm, settings, step_info)
    assert res is False


@pytest.mark.asyncio
async def test_llm_exception_round_028():
    # LLM raises exception -> caught and returns False (lines ~272-277)
    long_text = "x" * 200
    mgr = make_manager(history_texts=[long_text], prev_compacted=None, read_state=None)
    settings = SimpleNamespace(
        enabled=True,
        compact_every_n_steps=1,
        trigger_char_count=10,
        include_read_state=False,
        summary_max_chars=None,
        keep_last_items=1,
    )
    llm = DummyLLM(raise_exc=True)
    step_info = SimpleNamespace(step_number=2)

    res = await MessageManager.maybe_compact_messages(mgr, llm, settings, step_info)
    assert res is False


@pytest.mark.asyncio
async def test_empty_summary_round_028():
    # LLM returns empty completion -> False (lines ~279-280)
    long_text = "x" * 200
    mgr = make_manager(history_texts=[long_text])
    settings = SimpleNamespace(
        enabled=True,
        compact_every_n_steps=1,
        trigger_char_count=10,
        include_read_state=False,
        summary_max_chars=None,
        keep_last_items=1,
    )
    llm = DummyLLM(completion="")
    step_info = SimpleNamespace(step_number=3)

    res = await MessageManager.maybe_compact_messages(mgr, llm, settings, step_info)
    assert res is False


@pytest.mark.asyncio
async def test_success_truncate_and_keep_last_round_028():
    # Full path: include previous compacted memory, include read state, sensitive data filtering,
    # truncation of summary, compaction state updates, and keeping last N items (lines ~242-296)
    history = [f"item{i}" for i in range(6)]
    mgr = make_manager(history_texts=history, prev_compacted="OLD_SUMMARY", read_state="READ_STATE", sensitive=True)

    # small trigger to allow compaction; summary_max_chars triggers truncation
    settings = SimpleNamespace(
        enabled=True,
        compact_every_n_steps=1,
        trigger_char_count=1,
        include_read_state=True,
        summary_max_chars=10,
        keep_last_items=2,
    )

    # llm returns a longer summary than summary_max_chars to force truncation
    long_summary = "This is a long summary that should be truncated."
    llm = DummyLLM(completion=long_summary)
    step_info = SimpleNamespace(step_number=42)

    res = await MessageManager.maybe_compact_messages(mgr, llm, settings, step_info)
    assert res is True

    # truncated summary ends with ellipsis character U+2026
    assert mgr.state.compacted_memory.endswith("\u2026")
    # compaction count incremented and last step recorded
    assert mgr.state.compaction_count == 1
    assert mgr.state.last_compaction_step == step_info.step_number
    # agent_history_items should contain first item + last keep_last_items entries (1 + 2 = 3)
    assert len(mgr.state.agent_history_items) == 3
    assert mgr.state.agent_history_items[0].to_string() == history[0]
    assert mgr.state.agent_history_items[-1].to_string() == history[-1]


@pytest.mark.asyncio
async def test_success_keep_last_zero_round_028():
    # Keep-last == 0 path: only the very first history item should be kept (lines ~290-295)
    history = [f"h{i}" for i in range(4)]
    mgr = make_manager(history_texts=history)

    settings = SimpleNamespace(
        enabled=True,
        compact_every_n_steps=1,
        trigger_char_count=1,
        include_read_state=False,
        summary_max_chars=None,
        keep_last_items=0,
    )
    llm = DummyLLM(completion="final summary")
    step_info = SimpleNamespace(step_number=7)

    res = await MessageManager.maybe_compact_messages(mgr, llm, settings, step_info)
    assert res is True
    # Only the first history item remains
    assert len(mgr.state.agent_history_items) == 1
    assert mgr.state.agent_history_items[0].to_string() == history[0]
