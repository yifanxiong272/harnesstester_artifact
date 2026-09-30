# file: sweagent/agent/action_sampler.py:250-264
# asked: {"lines": [251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264], "branches": [[254, 255], [254, 257], [257, 258], [257, 261], [261, 262], [261, 264]]}
# gained: {"lines": [251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264], "branches": [[254, 255], [254, 257], [257, 258], [261, 262]]}

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from sweagent.agent.action_sampler import BinaryTrajectoryComparison
from sweagent.exceptions import FormatError


def test_get_completions_raises_format_error(monkeypatch):
    model = MagicMock()
    # model returns something but filter_parseable_completions will make it empty
    model.query.return_value = [{"text": "irrelevant"}]
    tools = MagicMock()
    config = SimpleNamespace(min_n_samples=1, max_n_samples=1)

    sampler = BinaryTrajectoryComparison(config, model, tools)

    # Make parseable filtering return empty -> triggers FormatError
    monkeypatch.setattr(sampler, "filter_parseable_completions", lambda completions: [])
    # filter_duplicates shouldn't be reached for non-empty but set harmlessly
    monkeypatch.setattr(sampler, "filter_duplicates", lambda completions: completions)

    with pytest.raises(FormatError) as excinfo:
        sampler.get_completions(history=[])
    assert "No completions could be parsed." in str(excinfo.value)
    # ensure model.query was called with n=min_n_samples
    assert model.query.call_count == 1
    assert model.query.call_args_list[0][1]["n"] == config.min_n_samples


def test_get_completions_requests_more_samples_and_logs_warning(monkeypatch):
    model = MagicMock()
    # first query returns one completion, second query returns another
    first = [{"text": "first"}]
    second = [{"text": "second"}]
    model.query.side_effect = [first, second]

    tools = MagicMock()
    # parse_actions should be called when final completions length == 1
    tools.parse_actions.return_value = (None, "PARSED_ACTION")

    config = SimpleNamespace(min_n_samples=2, max_n_samples=5)

    sampler = BinaryTrajectoryComparison(config, model, tools)

    # capture logging calls
    logger = MagicMock()
    sampler._logger = logger

    # filter_parseable_completions: keep whatever is passed through
    def filter_parseable(completions):
        return completions

    # filter_duplicates: if multiple completions passed (after concatenation), reduce to a single one
    def filter_duplicates(completions):
        if len(completions) > 1:
            # simulate deduplication to a single representative completion
            return [completions[-1]]
        return completions

    monkeypatch.setattr(sampler, "filter_parseable_completions", filter_parseable)
    monkeypatch.setattr(sampler, "filter_duplicates", filter_duplicates)
    # force contains_edits to True to trigger additional sampling
    monkeypatch.setattr(sampler, "contains_edits", lambda comps: True)

    result = sampler.get_completions(history=[])

    # After deduplication we forced a single result coming from 'second'
    assert result == second

    # model.query should be called twice: first with min_n_samples, then with max-min
    assert model.query.call_count == 2
    assert model.query.call_args_list[0][1]["n"] == config.min_n_samples
    assert model.query.call_args_list[1][1]["n"] == config.max_n_samples - config.min_n_samples

    # parse_actions should have been called for the single completion and a warning logged
    tools.parse_actions.assert_called_once_with(second[0])
    logger.debug.assert_called_once_with("Edits were proposed, will sample more")
    logger.warning.assert_called_once()
