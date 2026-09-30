# file: rdagent/scenarios/qlib/developer/utils.py:13-67
# asked: {"lines": [23, 24, 25, 28, 29, 30, 33, 35, 36, 37, 38, 39, 43, 44, 46, 47, 48, 49, 50, 51, 54, 56, 57, 58, 62, 63, 65, 66], "branches": [[23, 24], [23, 25], [28, 29], [28, 62], [29, 28], [29, 30], [30, 28], [30, 33], [44, 28], [44, 46], [46, 47], [46, 56], [48, 49], [48, 54], [62, 63], [62, 65]]}
# gained: {"lines": [23, 24, 25, 28, 29, 30, 33, 35, 36, 37, 38, 39, 43, 44, 46, 47, 48, 49, 50, 51, 54, 56, 57, 58, 62, 63, 65, 66], "branches": [[23, 24], [23, 25], [28, 29], [28, 62], [29, 30], [30, 33], [44, 28], [44, 46], [46, 47], [46, 56], [48, 49], [48, 54], [62, 63], [62, 65]]}

import pandas as pd
import pytest
from datetime import datetime, timedelta

import rdagent.scenarios.qlib.developer.utils as utils_module


class DummyCoSTEERMultiFeedback:
    def __init__(self, items=None):
        # items represent feedback flags for each sub_workspace; truthy items will cause execution
        if items is None:
            items = [True]
        self._items = list(items)

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)


class DummyImplementation:
    def __init__(self, name="impl"):
        self.name = name

    def execute(self, arg):
        # Not used by tests because multiprocessing_wrapper is monkeypatched,
        # but kept for completeness.
        return f"executed-{self.name}", None


class DummyHypothesis:
    def __init__(self, concise_justification="dummy-just"):
        self.concise_justification = concise_justification


class DummyQlibFactorExperiment:
    def __init__(self, sub_tasks, prop_dev_feedback, sub_workspace_list, hypothesis):
        self.sub_tasks = sub_tasks
        self.prop_dev_feedback = prop_dev_feedback
        self.sub_workspace_list = sub_workspace_list
        self.hypothesis = hypothesis


def make_datetime_multiindex(start, minutes, count):
    times = [start + timedelta(minutes=minutes * i) for i in range(count)]
    tuples = [(f"sym{i%2}", times[i]) for i in range(count)]
    return pd.MultiIndex.from_tuples(tuples, names=["symbol", "datetime"]), times


def test_process_factor_data_success_single_exp(monkeypatch):
    # Arrange
    # Monkeypatch class names used in module so isinstance checks work
    monkeypatch.setattr(utils_module, "CoSTEERMultiFeedback", DummyCoSTEERMultiFeedback, raising=False)
    monkeypatch.setattr(utils_module, "QlibFactorExperiment", DummyQlibFactorExperiment, raising=False)

    # Create an experiment with one sub_task and one implementation & feedback
    prop_fb = DummyCoSTEERMultiFeedback([True])
    impl = DummyImplementation("ok")
    hyp = DummyHypothesis("success-case")
    exp = DummyQlibFactorExperiment(sub_tasks=[1], prop_dev_feedback=prop_fb, sub_workspace_list=[impl], hypothesis=hyp)

    # Create a DataFrame where datetime diffs are 2 minutes (so not equal to 1 minute)
    start = datetime(2020, 1, 1, 9, 30)
    idx, _ = make_datetime_multiindex(start, minutes=2, count=3)
    df = pd.DataFrame({"f1": [1, 2, 3]}, index=idx)

    captured = {}

    def fake_multiprocessing_wrapper(callables, n=None):
        # Verify that the wrapper is being called with a sequence built from implementations
        captured["callables"] = callables
        return [("ok", df)]

    monkeypatch.setattr(utils_module, "multiprocessing_wrapper", fake_multiprocessing_wrapper, raising=False)

    # Act
    result = utils_module.process_factor_data(exp)

    # Assert
    # Should return the concatenated dataframe (only one df -> same as df)
    pd.testing.assert_frame_equal(result, df)
    # Ensure multiprocessing wrapper received the expected callable structure
    assert isinstance(captured["callables"], list)
    assert all(isinstance(tpl, tuple) and len(tpl) == 2 for tpl in captured["callables"])


def test_process_factor_data_failure_time_diff_and_none(monkeypatch):
    # Arrange - cover branches where df has 1-minute diffs (warning) and where df is None (error_message)
    monkeypatch.setattr(utils_module, "CoSTEERMultiFeedback", DummyCoSTEERMultiFeedback, raising=False)
    monkeypatch.setattr(utils_module, "QlibFactorExperiment", DummyQlibFactorExperiment, raising=False)

    prop_fb = DummyCoSTEERMultiFeedback([True, True])
    impl1 = DummyImplementation("one_minute")
    impl2 = DummyImplementation("none_df")
    hyp = DummyHypothesis("failure-case")
    exp = DummyQlibFactorExperiment(sub_tasks=[1, 2], prop_dev_feedback=prop_fb, sub_workspace_list=[impl1, impl2], hypothesis=hyp)

    # Create a DataFrame where datetime diffs are exactly 1 minute
    start = datetime(2020, 1, 1, 9, 30)
    idx1, _ = make_datetime_multiindex(start, minutes=1, count=3)
    df_one_min = pd.DataFrame({"f1": [1, 2, 3]}, index=idx1)

    # Second implementation returns None with an error message
    def fake_multiprocessing_wrapper(callables, n=None):
        # Return first tuple with df that has 1-minute diffs (should be ignored),
        # second tuple with error message and None df (should contribute to error_message).
        return [("ok", df_one_min), ("error occurred", None)]

    monkeypatch.setattr(utils_module, "multiprocessing_wrapper", fake_multiprocessing_wrapper, raising=False)

    # Act & Assert: should raise FactorEmptyError because no valid factor_dfs were appended
    with pytest.raises(utils_module.FactorEmptyError) as excinfo:
        utils_module.process_factor_data([exp])

    # The error message should contain the appended error message part from the None df case
    assert "error occurred" in str(excinfo.value)
