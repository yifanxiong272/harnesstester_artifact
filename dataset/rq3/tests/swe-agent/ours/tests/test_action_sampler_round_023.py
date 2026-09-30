import types
import pytest
from types import SimpleNamespace

from sweagent.agent.action_sampler import BinaryTrajectoryComparison
from sweagent.exceptions import FormatError


class DummyModel:
    def __init__(self, responses_by_n):
        # responses_by_n: dict[int, list]
        self.responses_by_n = dict(responses_by_n)
        self.calls = []

    def query(self, history, n):
        # record call and return configured response for n
        self.calls.append((list(history), int(n)))
        return list(self.responses_by_n.get(int(n), []))


class FakeLogger:
    def __init__(self):
        self.debug_called = False
        self.warning_called = False
        self.last_warning = None
        self.last_debug_msg = None

    def debug(self, *args, **kwargs):
        self.debug_called = True
        self.last_debug_msg = (args, kwargs)

    def warning(self, *args, **kwargs):
        self.warning_called = True
        self.last_warning = (args, kwargs)


class DummyTools:
    def __init__(self, action_to_return=(None, "actionX")):
        self.action_to_return = action_to_return
        self.parse_calls = []

    def parse_actions(self, completion):
        self.parse_calls.append(completion)
        return self.action_to_return


def make_sampler_without_init(model, tools, config, logger, *,
                               filter_parseable=None, filter_duplicates=None, contains_edits=None):
    # create instance without running __init__ and patch attributes/methods
    sampler = object.__new__(BinaryTrajectoryComparison)
    sampler._model = model
    sampler._tools = tools
    sampler.config = config
    sampler._logger = logger

    # override methods/attributes used by get_completions
    if filter_parseable is not None:
        sampler.filter_parseable_completions = filter_parseable
    if filter_duplicates is not None:
        sampler.filter_duplicates = filter_duplicates
    if contains_edits is not None:
        sampler.contains_edits = contains_edits

    return sampler


def test_no_parseable_completions_round_023():
    # model returns some raw completions, but filter_parseable_completions removes them -> FormatError
    model = DummyModel({1: ["raw1"]})
    tools = DummyTools()
    logger = FakeLogger()
    config = SimpleNamespace(min_n_samples=1, max_n_samples=1)

    # filter_parseable_completions returns empty list regardless of input
    sampler = make_sampler_without_init(
        model,
        tools,
        config,
        logger,
        filter_parseable=lambda comps: [],
        filter_duplicates=lambda comps: comps,
        contains_edits=lambda comps: False,
    )

    with pytest.raises(FormatError) as ei:
        sampler.get_completions([])

    assert "No completions could be parsed." in str(ei.value)
    # ensure the model was queried once with the configured min_n_samples
    assert model.calls == ([[] , 1] if False else [( [], 1)])


def test_extra_sampling_on_edits_round_023():
    # initial query returns one parseable completion; contains_edits True and min < max
    # should cause a second query with n = max - min and final deduped combined results returned
    history = [{"h": 1}]
    # configure model: when asked n=1 return ['A']; when n=2 return ['B', 'A']
    model = DummyModel({1: ["A"], 2: ["B", "A"]})
    tools = DummyTools()
    logger = FakeLogger()
    config = SimpleNamespace(min_n_samples=1, max_n_samples=3)

    # create a filter_parseable that returns whatever it's given (but we instrument calls)
    parse_calls = []

    def filter_parseable(completions):
        # record inputs to verify later
        parse_calls.append(list(completions))
        # assume all completions passed in are parseable
        return list(completions)

    def filter_duplicates(completions):
        # preserve order and unique
        seen = set()
        out = []
        for c in completions:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    sampler = make_sampler_without_init(
        model,
        tools,
        config,
        logger,
        filter_parseable=filter_parseable,
        filter_duplicates=filter_duplicates,
        contains_edits=lambda comps: True,
    )

    result = sampler.get_completions(history)

    # model.query should have been called twice with expected n values
    assert model.calls == [(history, 1), (history, 2)]

    # parseable filter should have been called twice: once for initial, once for combined
    assert parse_calls[0] == ["A"]
    # second call should receive combined original + new list
    assert parse_calls[1] == ["A", "B", "A"] or parse_calls[1] == ["A", "B"]

    # duplicates removed, final ordering should be ['A','B']
    assert result == ["A", "B"]

    # logger.debug should have been invoked when edits were detected
    assert logger.debug_called is True


def test_single_completion_triggers_warning_round_023():
    # when final completions length is 1, tools.parse_actions must be called and logger.warning invoked
    model = DummyModel({1: ["only_one"]})
    tools = DummyTools(action_to_return=("thought", "SINGLE_ACTION"))
    logger = FakeLogger()
    config = SimpleNamespace(min_n_samples=1, max_n_samples=1)

    sampler = make_sampler_without_init(
        model,
        tools,
        config,
        logger,
        filter_parseable=lambda comps: list(comps),
        filter_duplicates=lambda comps: list(comps),
        contains_edits=lambda comps: False,
    )

    result = sampler.get_completions([])

    # returned completions should be the single item
    assert result == ["only_one"]

    # tools.parse_actions called with that completion
    assert tools.parse_calls == ["only_one"]

    # logger.warning should have recorded the action value in its args
    assert logger.warning_called is True
    # the logged action should be present in the last warning arguments
    args, kwargs = logger.last_warning
    # message format: "Only identical actions were proposed (action=%s)", action
    assert "Only identical actions were proposed" in args[0]
    assert args[1] == "SINGLE_ACTION"
