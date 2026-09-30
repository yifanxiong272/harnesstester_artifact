# file: sweagent/agent/reviewer.py:200-234
# asked: {"lines": [228, 231, 234], "branches": []}
# gained: {"lines": [228, 231, 234], "branches": []}

import importlib
import types

import pytest


def _make_model_instance(cls):
    # Support both pydantic v2 (model_construct) and v1 (construct)
    constructor = getattr(cls, "model_construct", None) or getattr(cls, "construct", None)
    if constructor is None:
        # Fallback: create instance without calling __init__
        inst = object.__new__(cls)
    else:
        try:
            inst = constructor()
        except TypeError:
            # Some pydantic versions expect different signatures; fallback to __new__
            inst = object.__new__(cls)
    return inst


def test_score_retry_loop_config_validate_postinit_and_get_retry_loop(monkeypatch):
    # Import the module and the class under test
    mod = importlib.import_module("sweagent.agent.reviewer")
    ScoreRetryLoopConfig = getattr(mod, "ScoreRetryLoopConfig")

    # Create a bare instance bypassing validation/initialization
    cfg = _make_model_instance(ScoreRetryLoopConfig)

    # Populate required attributes used by the methods we will call.
    # We avoid creating full nested pydantic objects by using plain python objects,
    # since we won't execute code that depends on their internals.
    cfg.reviewer_config = object()
    cfg.accept_score = 0.5
    cfg.max_attempts = 1
    cfg.max_accepts = 1
    cfg.min_budget_for_new_attempt = 0.0
    cfg.cost_limit = 0.0
    cfg.model = {"type": "dummy-model"}

    # 1) Execute validate() (line 228)
    # Save original to call directly so we exercise the original implementation.
    orig_validate = cfg.validate
    # Should not raise and should return None (function body is "..." in source)
    assert orig_validate() is None

    # 2) Execute __post_init__ (line 231) and ensure it calls validate().
    called = {"flag": False}

    def fake_validate(self):
        called["flag"] = True
        return None

    # Replace class validate with our fake to observe the call from __post_init__
    monkeypatch.setattr(ScoreRetryLoopConfig, "validate", fake_validate)

    # Call __post_init__ which should call our fake_validate -> sets flag
    assert cfg.__post_init__() is None
    assert called["flag"] is True

    # 3) Execute get_retry_loop (line 234) and ensure it returns the ScoreRetryLoop result.
    # Monkeypatch the ScoreRetryLoop symbol in the module to a dummy callable so
    # we don't instantiate the real heavy object.
    captured = {}

    class DummyScoreRetryLoop:
        def __init__(self, config_arg, problem_statement_arg):
            # record that constructor was called with expected args
            captured["config"] = config_arg
            captured["problem_statement"] = problem_statement_arg

        def __repr__(self):
            return "<DummyScoreRetryLoop>"

    # Patch the module-level name
    monkeypatch.setattr(mod, "ScoreRetryLoop", DummyScoreRetryLoop)

    # Use a simple problem statement object (could be anything)
    problem_statement = object()

    result = cfg.get_retry_loop(problem_statement)
    # get_retry_loop returns an instance of DummyScoreRetryLoop
    assert isinstance(result, DummyScoreRetryLoop)
    # Validate the constructor received the same objects
    assert captured["config"] is cfg
    assert captured["problem_statement"] is problem_statement
