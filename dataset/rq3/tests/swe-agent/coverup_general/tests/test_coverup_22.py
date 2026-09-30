# file: sweagent/agent/reviewer.py:30-56
# asked: {"lines": [44, 45, 46, 49, 50, 51, 52, 53, 54, 55, 56], "branches": [[46, 49], [46, 50], [50, 51], [50, 56], [51, 52], [51, 53], [53, 50], [53, 54], [54, 50], [54, 55]]}
# gained: {"lines": [44, 45, 46, 49, 50, 51, 52, 53, 54, 55, 56], "branches": [[46, 49], [46, 50], [50, 51], [50, 56], [51, 52], [51, 53], [53, 50], [53, 54], [54, 50], [54, 55]]}

import pytest
from sweagent.agent.reviewer import ReviewSubmission


def test_to_format_dict_missing_submission_and_nested():
    # info missing 'submission' key -> should be added as empty string
    info = {"agent": "bot", "metrics": {"a": 1, "b": "two"}}
    rs = ReviewSubmission.construct(trajectory=[], info=info, model_stats={})
    out = rs.to_format_dict(suffix="_X")

    # submission added and uses suffix
    assert out["submission_X"] == ""
    # string value copied with suffix
    assert out["agent_X"] == "bot"
    # nested dict expanded with combined keys and suffix
    assert out["metrics_a_X"] == 1
    assert out["metrics_b_X"] == "two"
    # no extra keys
    assert set(out.keys()) == {"submission_X", "agent_X", "metrics_a_X", "metrics_b_X"}


def test_to_format_dict_existing_submission_and_skips_non_str_non_dict():
    # submission present and non-empty -> preserved
    # include a non-str, non-dict value which should be skipped
    info = {"submission": "submitted_ok", "count": 123, "meta": {"k": "v"}}
    rs = ReviewSubmission.construct(trajectory=None, info=info, model_stats=None)
    out = rs.to_format_dict()

    # submission preserved
    assert out["submission"] == "submitted_ok"
    # nested dict expanded
    assert out["meta_k"] == "v"
    # non-str, non-dict entry should not appear in output
    assert "count" not in out
