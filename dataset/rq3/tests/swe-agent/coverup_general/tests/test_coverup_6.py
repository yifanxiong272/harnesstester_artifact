# file: sweagent/agent/reviewer.py:329-372
# asked: {"lines": [330, 331, 332, 333, 334, 335, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 354, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 369, 370, 371], "branches": [[333, 334], [333, 337], [338, 339], [338, 357], [345, 346], [345, 356], [351, 352], [351, 354], [365, 366], [365, 369]]}
# gained: {"lines": [330, 331, 332, 333, 334, 335, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 354, 356, 357, 358, 359, 360, 361, 365, 366, 367, 369, 370, 371], "branches": [[333, 334], [333, 337], [338, 339], [345, 346], [345, 356], [351, 352], [351, 354], [365, 366], [365, 369]]}

import types
import pytest

import sweagent.agent.reviewer as reviewer_module
from types import SimpleNamespace


class DummyLogger:
    def __init__(self):
        self.records = {"debug": [], "error": [], "critical": []}

    def debug(self, *args, **kwargs):
        self.records["debug"].append((args, kwargs))

    def error(self, *args, **kwargs):
        self.records["error"].append((args, kwargs))

    def critical(self, *args, **kwargs):
        self.records["critical"].append((args, kwargs))


class DummyModel:
    def __init__(self, return_message):
        self.return_message = return_message
        self.queries = []

    def query(self, messages):
        # record the messages for assertions
        self.queries.append(messages)
        return {"message": self.return_message}


class ReviewSubmission:
    def __init__(self, info=None):
        self.info = info or {}


def make_config(preselector, model_name="dummy"):
    return SimpleNamespace(preselector=preselector, model=model_name)


def setup_common(monkeypatch, model_return_message="resp"):
    """
    Prepare common monkeypatches: get_logger and get_model replacement.
    Returns (logger, model_instance).
    """
    logger = DummyLogger()
    model = DummyModel(model_return_message)

    # get_model(original_model_name, config) -> return our DummyModel
    def fake_get_model(model_name, cfg):
        return model

    monkeypatch.setattr(reviewer_module, "get_model", fake_get_model)
    monkeypatch.setattr(reviewer_module, "get_logger", lambda *args, **kwargs: logger)
    return logger, model


def test_preselector_valid_choice_maps_index(monkeypatch):
    # Setup common monkeypatches
    logger, model = setup_common(monkeypatch, model_return_message="ok1")

    # Make 4 submissions, three of which are 'submitted'
    subs = [
        ReviewSubmission({"exit_status": "submitted"}),
        ReviewSubmission({"exit_status": "submitted"}),
        ReviewSubmission({"exit_status": "submitted"}),
        ReviewSubmission({"exit_status": "failed"}),
    ]

    # Preselector stub that returns chosen_idx [1] (chooses second selected item)
    class PreselectorStub:
        def __init__(self, cfg):
            self.cfg = cfg

        def choose(self, problem_statement, inputs):
            # Return a proper PreselectorOutput model so attribute access works and pydantic accepts it
            return reviewer_module.PreselectorOutput(chosen_idx=[1], response="pre", messages=[])

    monkeypatch.setattr(reviewer_module, "Preselector", PreselectorStub)

    # Create chooser with preselector configured
    cfg = make_config(preselector={"any": True}, model_name="m")
    chooser = reviewer_module.Chooser(cfg)

    # Replace instance methods to predictable behavior
    messages_out = [{"role": "system", "content": "msg"}]
    chooser.build_messages = lambda problem_statement, inputs: messages_out
    # interpret returns 0 (index into the _preselected list, which after preselection will have length 1)
    chooser.interpret = lambda response: 0

    result = chooser.choose("problem", subs)

    # After preselection, selected_indices should become [1] (the original index 1)
    assert result.chosen_idx == 1
    assert result.preselector_output is not None
    assert getattr(result.preselector_output, "chosen_idx") == [1]
    assert result.messages == messages_out
    # model.query should have been called with messages that match build_messages output
    assert model.queries and model.queries[-1] == messages_out
    # logger should have recorded a debug about having submitted submissions
    assert any("submitted submissions" in rec[0][0] for rec in logger.records["debug"])


def test_preselector_exception_and_interpret_none_chooses_first(monkeypatch):
    logger, model = setup_common(monkeypatch, model_return_message="ok2")

    # 4 submissions, only one is 'submitted'
    subs = [
        ReviewSubmission({"exit_status": "failed"}),
        ReviewSubmission({"exit_status": "failed"}),
        ReviewSubmission({"exit_status": "submitted"}),  # only one submitted
        ReviewSubmission({"exit_status": "failed"}),
    ]

    # Preselector stub that raises an exception
    class PreselectorRaises:
        def __init__(self, cfg):
            pass

        def choose(self, problem_statement, inputs):
            raise RuntimeError("preselector boom")

    monkeypatch.setattr(reviewer_module, "Preselector", PreselectorRaises)

    cfg = make_config(preselector={"enabled": True}, model_name="m")
    chooser = reviewer_module.Chooser(cfg)

    # build_messages returns a known value
    messages_out = [{"role": "system", "content": "m2"}]
    chooser.build_messages = lambda problem_statement, inputs: messages_out

    # interpret returns None to simulate no valid interpretation
    chooser.interpret = lambda response: None

    result = chooser.choose("problem", subs)

    # Because interpret returned None, chooser should pick the first of selected_indices (which when n_submitted<2 is all indices -> 0)
    assert result.chosen_idx == 0
    assert result.preselector_output is None
    assert result.messages == messages_out
    # Ensure logger recorded that preselector must have failed (error)
    assert any("Preselector must have failed" in rec[0][0] for rec in logger.records["error"])


def test_preselector_invalid_indices_indexerror_handled(monkeypatch):
    logger, model = setup_common(monkeypatch, model_return_message="ok3")

    # 4 submissions, three are 'submitted'
    subs = [
        ReviewSubmission({"exit_status": "submitted"}),
        ReviewSubmission({"exit_status": "submitted"}),
        ReviewSubmission({"exit_status": "submitted"}),
        ReviewSubmission({"exit_status": "failed"}),
    ]

    # Preselector returns an out-of-range chosen_idx causing IndexError when mapping
    class PreselectorBadIndices:
        def __init__(self, cfg):
            pass

        def choose(self, problem_statement, inputs):
            return reviewer_module.PreselectorOutput(chosen_idx=[99], response="prebad", messages=[])

    monkeypatch.setattr(reviewer_module, "Preselector", PreselectorBadIndices)

    cfg = make_config(preselector={"enabled": True}, model_name="m")
    chooser = reviewer_module.Chooser(cfg)

    messages_out = [{"role": "system", "content": "m3"}]
    chooser.build_messages = lambda problem_statement, inputs: messages_out

    # interpret returns 2 which should be valid for the unmodified selected_indices [0,1,2]
    chooser.interpret = lambda response: 2

    result = chooser.choose("problem", subs)

    # Preselector output should be present (but invalid indices)
    assert result.preselector_output is not None
    assert getattr(result.preselector_output, "chosen_idx") == [99]
    # Since preselector indices were invalid, selected_indices should remain the original submitted indices [0,1,2]
    # interpret returned 2 -> maps to selected_indices[2] == 2
    assert result.chosen_idx == 2
    assert result.messages == messages_out
    # Check that errors about invalid indices and no valid indices were logged
    assert any("Preselector gave invalid indices" in rec[0][0] for rec in logger.records["error"])
    assert any("Preselector gave no valid indices" in rec[0][0] for rec in logger.records["error"])
