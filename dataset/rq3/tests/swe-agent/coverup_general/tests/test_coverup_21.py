# file: sweagent/inspector/server.py:15-34
# asked: {"lines": [15, 16, 17, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 32, 33, 34], "branches": [[17, 18], [17, 20], [20, 21], [20, 34], [21, 22], [21, 32]]}
# gained: {"lines": [15, 16, 17, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 32, 33, 34], "branches": [[17, 18], [17, 20], [20, 21], [20, 34], [21, 22], [21, 32]]}

import pytest
from sweagent.inspector.server import append_exit


def test_append_exit_no_exit_status_returns_same_object():
    content = {}  # no 'info' key -> exit_status is None
    returned = append_exit(content)
    # Should return the same object unchanged
    assert returned is content
    assert returned == {}


def test_append_exit_non_submitted_exit_status_returns_unchanged():
    content = {"info": {"exit_status": "failed"}, "trajectory": []}
    returned = append_exit(content)
    # exit_status present but doesn't start with 'submitted' -> unchanged
    assert returned is content
    assert returned["trajectory"] == []


def test_append_exit_submitted_with_submission_appends_trajectory_entry():
    exit_status = "submitted-2026-07-18"
    submission_text = "ANSWER: 42"
    content = {
        "info": {"exit_status": exit_status, "submission": submission_text},
        "trajectory": [],
    }

    returned = append_exit(content)

    # Should return same object mutated in-place
    assert returned is content
    assert len(returned["trajectory"]) == 1

    entry = returned["trajectory"][0]
    # Check required keys and values
    assert entry["thought"] == "Submitting solution"
    assert entry["action"] == "Model Submission"
    assert entry["response"] == "Submitting solution"
    assert entry["observation"] == submission_text
    assert isinstance(entry["messages"], list) and len(entry["messages"]) == 1
    msg = entry["messages"][0]
    assert msg["role"] == "system"
    # Message content must include the exit_status
    assert f"Submission generated - {exit_status}" == msg["content"]


def test_append_exit_submitted_without_submission_raises_value_error():
    content = {"info": {"exit_status": "submitted-now"}, "trajectory": []}
    with pytest.raises(ValueError) as excinfo:
        append_exit(content)
    assert str(excinfo.value) == "No submission in history or info"
