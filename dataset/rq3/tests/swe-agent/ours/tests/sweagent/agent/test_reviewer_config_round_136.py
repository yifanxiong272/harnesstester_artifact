import builtins
import types

import pytest

from sweagent.agent import reviewer as reviewer_mod
from sweagent.agent.reviewer import ReviewerConfig


def test_get_reviewer_forwards_config_and_model_round_136(monkeypatch):
    """Ensure ReviewerConfig.get_reviewer constructs Reviewer with the same
    config instance and the provided model object.
    """
    recorded = {}

    class StubReviewer:
        def __init__(self, cfg, model):
            # record what was passed in so we can assert identity
            recorded["cfg"] = cfg
            recorded["model"] = model

        def identify(self):
            return "stub"

    # Patch the Reviewer symbol in the module under test so the call in
    # get_reviewer will instantiate our stub instead of the real Reviewer.
    monkeypatch.setattr(reviewer_mod, "Reviewer", StubReviewer)

    # Construct a ReviewerConfig without invoking full pydantic validation
    # (this avoids needing to fully satisfy nested model constructors).
    cfg = ReviewerConfig.construct(
        system_template="sys-template",
        instance_template="instance-template",
        traj_formatter={"dummy": True},
    )

    dummy_model = object()

    result = cfg.get_reviewer(dummy_model)

    # The returned object should be an instance of our stub and the
    # stub should have recorded the exact config and model objects passed.
    assert isinstance(result, StubReviewer)
    assert recorded["cfg"] is cfg
    assert recorded["model"] is dummy_model
    assert result.identify() == "stub"


def test_get_reviewer_allows_none_model_round_136(monkeypatch):
    """Verify that get_reviewer forwards None (or other model-like objects)
    unchanged to the Reviewer constructor.
    """

    class StubReviewer2:
        def __init__(self, cfg, model):
            self.cfg = cfg
            self.model = model

    monkeypatch.setattr(reviewer_mod, "Reviewer", StubReviewer2)

    cfg = ReviewerConfig.construct(
        system_template="s2",
        instance_template="i2",
        traj_formatter={"x": 1},
    )

    result = cfg.get_reviewer(None)

    assert isinstance(result, StubReviewer2)
    # ensure the exact config object is forwarded
    assert result.cfg is cfg
    # ensure None is forwarded as-is
    assert result.model is None
