import types
from types import SimpleNamespace
import sweagent.agent.reviewer as reviewer_module


class StubModel:
    def __init__(self, message):
        self._message = message

    def query(self, messages):
        # mimic the real model.query return shape used by Chooser.choose
        return {"message": self._message}


class StubLogger:
    def __init__(self):
        self.records = []

    def debug(self, msg, *args, **kwargs):
        self.records.append(("debug", str(msg)))

    def error(self, msg, *args, **kwargs):
        self.records.append(("error", str(msg)))

    def critical(self, msg, *args, **kwargs):
        self.records.append(("critical", str(msg)))


def make_chooser(config, model, interpret_return, build_messages_return, logger=None):
    Chooser = reviewer_module.Chooser
    # avoid running Chooser.__init__ to keep test isolated; set required attributes directly
    chooser = Chooser.__new__(Chooser)
    chooser.config = config
    chooser.logger = logger or StubLogger()
    chooser.model = model
    # interpret is called with response (string) and should return an int or None
    chooser.interpret = lambda response: interpret_return
    # build_messages should accept (problem_statement, submissions) and return list[dict]
    chooser.build_messages = lambda problem_statement, submissions: build_messages_return
    return chooser


def test_choose_with_submitted_and_no_preselector_round_002():
    # Prepare inputs: two submissions with exit_status "submitted" to trigger the n_submitted >= 2 branch
    subs = [SimpleNamespace(info={"exit_status": "submitted"}), SimpleNamespace(info={"exit_status": "submitted"}), SimpleNamespace(info={})]
    config = SimpleNamespace(preselector=False)
    model = StubModel("model-response-1")
    logger = StubLogger()

    # interpret returns index 1 relative to selected_indices -> should map to actual chosen index
    # build_messages must return list[dict] (matching pydantic expectations)
    messages_out = [{"role": "system", "content": "m1"}]
    chooser = make_chooser(config=config, model=model, interpret_return=1, build_messages_return=messages_out, logger=logger)

    out = chooser.choose("problem", subs)

    # selected_indices should be the indices of submitted entries [0,1]; interpret returned 1 -> chosen is selected_indices[1] == 1
    assert out.chosen_idx == 1
    # no preselector configured, so preselector_output must be None
    assert out.preselector_output is None
    # build_messages return is propagated into the output and preserved as list[dict]
    assert out.messages == messages_out


def test_choose_with_preselector_invalid_indices_and_model_none_round_002(monkeypatch):
    # No submitted submissions -> n_submitted < 2 branch; set preselector config True and len(selected_indices)>2
    subs = [SimpleNamespace(info={}), SimpleNamespace(info={}), SimpleNamespace(info={}), SimpleNamespace(info={})]
    config = SimpleNamespace(preselector={"some": "config"})
    model = StubModel("model-response-2")
    logger = StubLogger()

    # Create a dummy Preselector that returns a PreselectorOutput instance with an out-of-range index -> triggers IndexError path
    class DummyPreselector:
        def __init__(self, cfg):
            self.cfg = cfg

        def choose(self, problem_statement, input_submissions):
            # Return the real PreselectorOutput model instance so attribute access and pydantic checks succeed
            return reviewer_module.PreselectorOutput(chosen_idx=[0, 5])

    # Patch the Preselector used by Chooser in the module under test
    monkeypatch.setattr(reviewer_module, "Preselector", DummyPreselector)

    # interpret returns None to force the fallback branch where chosen_idx is None
    messages_out = [{"role": "system", "content": "m2"}]
    chooser = make_chooser(config=config, model=model, interpret_return=None, build_messages_return=messages_out, logger=logger)

    out = chooser.choose("problem-2", subs)

    # Because preselector returned invalid indices, the preselector_output should be the PreselectorOutput instance
    assert out.preselector_output is not None
    assert hasattr(out.preselector_output, "chosen_idx")
    assert out.preselector_output.chosen_idx == [0, 5]

    # interpret returned None so fallback sets chosen_idx to the first of selected_indices (0)
    assert out.chosen_idx == 0

    # The logger should have recorded errors about invalid preselector indices and about using the first index
    logged_errors = "\n".join(m for level, m in logger.records if level == "error")
    assert "Preselector gave invalid indices" in logged_errors
    assert ("Preselector gave no valid indices" in logged_errors) or ("ignoring it" in logged_errors)
    # Also a message about invalid chosen index should have been logged when interpret returned None
    assert any(("using first index" in m or "Invalid chosen index" in m) for level, m in logger.records)
