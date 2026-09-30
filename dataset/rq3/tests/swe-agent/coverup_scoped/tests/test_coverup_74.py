# file: sweagent/agent/history_processors.py:123-140
# asked: {"lines": [135], "branches": []}
# gained: {"lines": [135], "branches": []}

import pytest

from sweagent.agent import history_processors as hp


def make_history_item(message_type="observation", content="orig", tags=None):
    if tags is None:
        tags = []
    return {"message_type": message_type, "content": content, "tags": tags}


def test_drop_observation_rewrites_content(monkeypatch):
    proc = hp.LastNObservations(n=1)

    # Force the processor to drop the only entry (index 0)
    monkeypatch.setattr(proc, "_get_omit_indices", lambda history: [0])

    history = [make_history_item(message_type="observation", content="line1\nline2", tags=[])]
    new_history = proc(history)

    assert len(new_history) == 1
    entry = new_history[0]
    # The processor should have rewritten the content to the "Old environment output" message
    assert isinstance(entry["content"], str)
    assert entry["content"].startswith("Old environment output:")
    # It should report the correct number of omitted lines (2 lines)
    assert "(2 lines omitted)" in entry["content"]


def test_drop_non_observation_raises_assert(monkeypatch):
    proc = hp.LastNObservations(n=1)
    monkeypatch.setattr(proc, "_get_omit_indices", lambda history: [0])

    history = [make_history_item(message_type="not_observation", content="something", tags=[])]
    with pytest.raises(AssertionError) as excinfo:
        proc(history)

    assert "Expected observation for dropped entry" in str(excinfo.value)
    # It should include the actual message_type in the assertion message
    assert "not_observation" in str(excinfo.value)


def test_keep_tag_preserves_output_when_omitted_index(monkeypatch):
    proc = hp.LastNObservations(n=1)
    # Force omission list to include index 0, but the tag should force keeping the output
    monkeypatch.setattr(proc, "_get_omit_indices", lambda history: [0])

    history = [make_history_item(message_type="observation", content="keep me", tags=["keep_output"])]
    new_history = proc(history)

    assert len(new_history) == 1
    entry = new_history[0]
    # Because it had the keep_output tag, content should be unchanged
    assert entry["content"] == "keep me"
    # Ensure the same dict object was preserved (not rewritten)
    assert entry is history[0]
