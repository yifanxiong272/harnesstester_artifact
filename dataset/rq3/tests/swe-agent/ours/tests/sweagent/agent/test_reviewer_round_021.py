import copy
import importlib

import pytest

# Import the class under test
reviewer_mod = importlib.import_module("sweagent.agent.reviewer")
ReviewSubmission = reviewer_mod.ReviewSubmission


def _make_submission_with_info(info):
    """
    Create a ReviewSubmission instance without full validation but with Pydantic
    internals initialized. Prefer model_construct (pydantic v2), fall back to
    construct (pydantic v1). As a final fallback, create a minimal object and
    populate __dict__ directly.
    """
    if hasattr(ReviewSubmission, "model_construct"):
        # pydantic v2: model_construct accepts kwargs for fields
        return ReviewSubmission.model_construct(info=info, trajectory=None, model_stats=None)
    if hasattr(ReviewSubmission, "construct"):
        # pydantic v1: construct
        return ReviewSubmission.construct(info=info, trajectory=None, model_stats=None)
    # Last-resort: ensure internals exist and set attributes directly
    inst = object.__new__(ReviewSubmission)
    # Provide typical pydantic internals expected by __setattr__ / __getattr__
    try:
        inst.__pydantic_fields_set__ = set()
    except Exception:
        pass
    inst.__dict__["info"] = info
    inst.__dict__["trajectory"] = None
    inst.__dict__["model_stats"] = None
    return inst


def test_to_format_dict_missing_submission_adds_and_preserves_original_round_021():
    # Original info missing 'submission' key and contains both a string and a dict.
    original_info = {"user": "alice", "meta": {"a": "1"}}
    submission = _make_submission_with_info(copy.deepcopy(original_info))

    # Call method with a non-empty suffix
    out = submission.to_format_dict(suffix="_s")

    # The returned dict should include the submission key added as an empty string
    # and should include both the string and nested dict entries with the suffix applied.
    expected = {"submission_s": "", "user_s": "alice", "meta_a_s": "1"}
    assert out == expected

    # Ensure the original info dict passed into the constructor was not mutated by to_format_dict
    # (the code uses deepcopy internally, but ensure our original dict remains without 'submission')
    assert "submission" not in original_info


def test_to_format_dict_keeps_existing_submission_and_handles_non_string_values_round_021():
    # Info contains an existing, truthy submission and a nested dict with an int value
    original_info = {"submission": "done", "status": "ok", "counts": {"n": 2}}
    submission = _make_submission_with_info(copy.deepcopy(original_info))

    out = submission.to_format_dict()

    # Expect the existing submission to be preserved and nested int to be carried through
    expected = {"submission": "done", "status": "ok", "counts_n": 2}
    assert out == expected

    # Ensure the instance preserves the info value we provided
    assert submission.info.get("submission") == "done"
