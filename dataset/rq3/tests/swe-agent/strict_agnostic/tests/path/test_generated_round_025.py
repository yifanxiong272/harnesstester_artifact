import logging
import pytest
from sweagent.agent.action_sampler import BinaryTrajectoryComparison
from sweagent.exceptions import FormatError


class SimpleConfig:
    def __init__(self, min_n_samples=1, max_n_samples=1):
        self.min_n_samples = min_n_samples
        self.max_n_samples = max_n_samples


class DummyTools:
    def __init__(self):
        self.parse_called_with = []

    def parse_actions(self, completion):
        # deterministic, observable action string
        self.parse_called_with.append(completion)
        return ("thought", "ACT:" + str(completion))


def test_get_completions_raises_when_no_completions_round_025():
    """When the model returns no completions (after parsing/filtering), a FormatError is raised.

    This covers the empty-completions branch that raises the FormatError.
    """
    config = SimpleConfig(min_n_samples=1, max_n_samples=1)

    class Model:
        def query(self, history, n):
            # return empty list to simulate no completions
            return []

    tools = DummyTools()
    sampler = BinaryTrajectoryComparison(config, Model(), tools)

    # Ensure filtering remains deterministic and returns empty
    sampler.filter_parseable_completions = lambda comps: []
    sampler.filter_duplicates = lambda comps: []

    with pytest.raises(FormatError) as excinfo:
        sampler.get_completions(history=[])
    assert "No completions could be parsed." in str(excinfo.value)


def test_get_completions_warns_when_single_action_round_025(caplog):
    """If exactly one completion remains, parse_actions is called and a warning is emitted.

    This covers the len(completions) == 1 warning branch and verifies parse_actions was used.
    """
    caplog.set_level(logging.WARNING)
    config = SimpleConfig(min_n_samples=1, max_n_samples=1)

    class Model:
        def query(self, history, n):
            # return a single completion
            return ["only_completion"]

    tools = DummyTools()
    sampler = BinaryTrajectoryComparison(config, Model(), tools)

    # Keep parseable and duplicate filtering trivial/predictable
    sampler.filter_parseable_completions = lambda comps: comps
    sampler.filter_duplicates = lambda comps: comps
    sampler.contains_edits = lambda comps: False

    res = sampler.get_completions(history=[])

    # result should be the single completion we returned
    assert res == ["only_completion"]

    # parse_actions on tools must have been called with that completion
    assert tools.parse_called_with == ["only_completion"]

    # a warning should have been emitted containing the expected message
    assert any("Only identical actions were proposed" in rec.message for rec in caplog.records)
    # and the logged message should include the action string produced by DummyTools.parse_actions
    assert any("ACT:only_completion" in rec.message for rec in caplog.records)


def test_get_completions_samples_more_when_edits_round_025(caplog):
    """When contains_edits is True and min_n_samples < max_n_samples, the model is queried again.

    This covers the branch that logs a debug message and calls model.query a second time with
    (max_n_samples - min_n_samples), then returns the combined parsed/deduped completions.
    """
    caplog.set_level(logging.DEBUG)

    class Model:
        def __init__(self):
            # record n values requested
            self.calls = []

        def query(self, history, n):
            self.calls.append(n)
            # behave differently depending on the requested n to make returned lists observable
            if n == 1:
                return ["c1"]
            if n == 2:
                return ["c2", "c3"]
            return []

    model = Model()
    tools = DummyTools()
    config = SimpleConfig(min_n_samples=1, max_n_samples=3)
    sampler = BinaryTrajectoryComparison(config, model, tools)

    # Make parsing a no-op (all completions are parseable) and dedup predictable
    sampler.filter_parseable_completions = lambda comps: comps
    sampler.filter_duplicates = lambda comps: list(dict.fromkeys(comps))

    # Force the code path that requests more samples
    sampler.contains_edits = lambda comps: True

    res = sampler.get_completions(history=[])

    # model.query should have been called twice: first with min_n_samples, then with (max-min)
    assert model.calls == [config.min_n_samples, config.max_n_samples - config.min_n_samples]

    # final combined completions should include all returned values in order and deduped
    assert res == ["c1", "c2", "c3"]

    # debug message about sampling more should be emitted
    assert any("Edits were proposed, will sample more" in rec.message for rec in caplog.records)
