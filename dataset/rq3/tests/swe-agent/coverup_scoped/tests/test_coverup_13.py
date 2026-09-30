# file: sweagent/agent/reviewer.py:30-56
# asked: {"lines": [44, 45, 46, 49, 50, 51, 52, 53, 54, 55, 56], "branches": [[46, 49], [46, 50], [50, 51], [50, 56], [51, 52], [51, 53], [53, 50], [53, 54], [54, 50], [54, 55]]}
# gained: {"lines": [44, 45, 46, 49, 50, 51, 52, 53, 54, 55, 56], "branches": [[46, 49], [46, 50], [50, 51], [50, 56], [51, 52], [51, 53], [53, 50], [53, 54], [54, 50], [54, 55]]}

import copy
from sweagent.agent.reviewer import ReviewSubmission


def test_to_format_dict_adds_missing_submission_and_handles_str_and_dict():
    # Prepare an info dict without 'submission', with a string, a nested dict and a non-str/non-dict
    original_info = {"foo": "bar", "meta": {"a": 1, "b": "two"}, "num": 123}
    # Use .construct to avoid pydantic validation requirements
    rs = ReviewSubmission.construct(trajectory=[], info=original_info, model_stats=None)

    # Call the method under test
    out = rs.to_format_dict()

    # Expected keys:
    # - 'submission' should be added as empty string because it was missing
    # - 'foo' (string) should be present
    # - nested dict entries should be flattened with underscore
    # - 'num' (non-str, non-dict) should be ignored
    assert out["submission"] == ""
    assert out["foo"] == "bar"
    assert out["meta_a"] == 1
    assert out["meta_b"] == "two"
    assert "num" not in out

    # Ensure the original info dict passed in was NOT modified (method uses deepcopy)
    assert "submission" not in original_info


def test_to_format_dict_preserves_existing_submission_and_applies_suffix():
    # Info already contains 'submission' and includes a nested dict and simple str
    info = {"submission": "auto", "x": "y", "meta": {"k": "v"}}
    info_copy = copy.deepcopy(info)  # keep a copy to assert original not modified
    rs = ReviewSubmission.construct(trajectory=[], info=info, model_stats=None)

    # Use a non-empty suffix to exercise that branch
    out = rs.to_format_dict(suffix="_suf")

    # Keys should include the suffix
    assert out["submission_suf"] == "auto"
    assert out["x_suf"] == "y"
    assert out["meta_k_suf"] == "v"

    # The original info dict should remain unchanged
    assert info == info_copy
