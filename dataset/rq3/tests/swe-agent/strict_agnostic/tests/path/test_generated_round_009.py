import pytest
from sweagent.agent.history_processors import ClosedWindowHistoryProcessor


def test_closed_window_processor_various_round_009():
    proc = ClosedWindowHistoryProcessor()

    # e1 is an older user window for fileA that should be marked as outdated
    e1 = {
        "role": "user",
        "content": "1: line\n2: line\n[File: fileA.py (10 lines total)]",
    }

    # e2 is a newer user window for fileA (seen later in time) and should be kept
    e2 = {
        "role": "user",
        "content": "1: line\n[File: fileA.py (5 lines total)]",
    }

    # e3 is a demo user entry and should be preserved unchanged
    e3 = {"role": "user", "is_demo": True, "content": "demo content"}

    # e4 is not a user role and should be preserved unchanged
    e4 = {"role": "assistant", "content": "assistant content"}

    # e5 has numeric-line matches but lacks a file tag -> it should be skipped
    e5 = {"role": "user", "content": "1: x\n2: y\n"}

    history = [e1, e2, e3, e4, e5]

    out = proc(history)

    # Verify deterministic structure and behavior
    assert isinstance(out, list)

    # e5 should be removed, so we expect 4 items remaining
    assert len(out) == 4

    # The first original entry (e1) should have been replaced with an "Outdated window" message
    first = out[0]
    assert "Outdated window with 2 lines omitted...\n" in first["content"]
    # The trailing file tag from the original content should remain after omission
    assert "[File: fileA.py (10 lines total)]" in first["content"]

    # The newer window e2 should be preserved (content unchanged)
    assert out[1]["content"] == e2["content"]

    # The demo entry should be preserved with the is_demo flag
    assert out[2].get("is_demo") is True
    assert out[2]["content"] == e3["content"]

    # The assistant entry should be preserved exactly
    assert out[3] == e4
