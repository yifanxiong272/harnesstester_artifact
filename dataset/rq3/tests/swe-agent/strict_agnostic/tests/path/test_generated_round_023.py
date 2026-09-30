import pytest

from sweagent.agent.reviewer import ReviewSubmission


def test_to_format_dict_missing_submission_round_023():
    """When info lacks 'submission', the method should inject an empty
    submission string and include string and nested-dict keys with the
    provided suffix. Also ensure the original self.info is not mutated.
    """
    info = {"a": "alpha", "nested": {"x": "ex"}}
    # Use pydantic BaseModel.construct via ReviewSubmission to avoid validation
    # and keep the test deterministic and isolated.
    rs = ReviewSubmission.construct(trajectory=[], info=info, model_stats=None)

    out = rs.to_format_dict(suffix="_suf")

    # string value becomes key with suffix
    assert out["a_suf"] == "alpha"
    # nested dict expands into underscore-joined keys with suffix
    assert out["nested_x_suf"] == "ex"
    # missing submission was added as empty string and processed as a string
    assert out["submission_suf"] == ""
    # the original stored info on the instance must remain without the injected key
    assert "submission" not in rs.info


def test_to_format_dict_with_submission_round_023():
    """When info already has 'submission', it should be preserved and not
    replaced by the empty string. Also ensure dict values are expanded
    and non-empty submission value is kept.
    """
    info = {"submission": "yes", "b": "bee", "data": {"k": 123}}
    rs = ReviewSubmission.construct(trajectory=[], info=info, model_stats=None)

    out = rs.to_format_dict()

    # submission preserved
    assert out["submission"] == "yes"
    # simple string key copied without suffix (default suffix="")
    assert out["b"] == "bee"
    # nested dict expands, numeric inner values are preserved as-is
    assert out["data_k"] == 123


def test_to_format_dict_nonstring_non_dict_round_023():
    """Values that are neither str nor dict should be ignored by the
    formatting loop (no key should be produced for such items).
    """
    info = {"n": 42, "ok": "yes"}
    rs = ReviewSubmission.construct(trajectory=[], info=info, model_stats=None)

    out = rs.to_format_dict(suffix="_X")

    # string value included with suffix
    assert out["ok_X"] == "yes"
    # numeric value should not create a key in the output
    assert all(not k.startswith("n") for k in out.keys())
