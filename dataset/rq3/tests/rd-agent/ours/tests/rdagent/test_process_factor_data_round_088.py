import importlib
from types import SimpleNamespace
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal


MODULE_PATH = "rdagent.scenarios.qlib.developer.utils"


def _patch_module(module, message_and_df_list):
    # Fake classes to satisfy isinstance checks and attributes used in process_factor_data
    class FakeCoSTEERMultiFeedback(list):
        pass

    class FakeImplementation:
        def execute(self, *args, **kwargs):
            # Not actually called because multiprocessing_wrapper is patched
            return None

    class FakeHypothesis:
        def __init__(self, concise_justification):
            self.concise_justification = concise_justification

    class FakeExperiment:
        def __init__(self, concise_justification, sub_tasks_count=1):
            self.sub_tasks = [1] * sub_tasks_count
            # prop_dev_feedback must be instance of CoSTEERMultiFeedback
            self.prop_dev_feedback = FakeCoSTEERMultiFeedback([True] * sub_tasks_count)
            # sub_workspace_list must be iterable of implementations
            self.sub_workspace_list = [FakeImplementation()] * sub_tasks_count
            self.hypothesis = FakeHypothesis(concise_justification)

    # patch module symbols where the function resolves them
    module.QlibFactorExperiment = FakeExperiment
    module.CoSTEERMultiFeedback = FakeCoSTEERMultiFeedback
    module.RD_AGENT_SETTINGS = SimpleNamespace(multi_proc_n=1)

    # simple logger stub to avoid side-effects
    class DummyLogger:
        def info(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            pass

    module.logger = DummyLogger()

    # Patch multiprocessing_wrapper to return the prepared message_and_df_list
    def _mp_stub(tasks, n=None):
        # Ensure the tasks parameter shape is as expected (list of callables tuples)
        assert isinstance(tasks, list)
        return message_and_df_list

    module.multiprocessing_wrapper = _mp_stub

    return FakeExperiment


def test_success_single_instance_round_088():
    """
    Provide a single QlibFactorExperiment instance (tests branch that converts single instance to list).
    multiprocessing_wrapper returns one DataFrame whose datetime differences are 2 minutes -> should be accepted
    and returned as a concatenated DataFrame.
    """
    module = importlib.import_module(MODULE_PATH)

    # Build a DataFrame with MultiIndex containing a 'datetime' level with 2-minute difference
    tuples = [
        (pd.Timestamp("2020-01-01 00:00:00"), "assetA"),
        (pd.Timestamp("2020-01-01 00:02:00"), "assetA"),
    ]
    mi = pd.MultiIndex.from_tuples(tuples, names=["datetime", "asset"])
    df = pd.DataFrame({"f1": [1, 2]}, index=mi)

    # Patch module to return this DataFrame from multiprocessing_wrapper
    FakeExperiment = _patch_module(module, [("ok", df)])

    # Create a single instance (not a list) to exercise the isinstance -> list conversion branch
    exp = FakeExperiment("justification-success", sub_tasks_count=1)

    result = module.process_factor_data(exp)

    # The returned DataFrame should be equal to the original one (concat of single df)
    assert_frame_equal(result, df)


def test_minute_diff_triggers_empty_error_round_088():
    """
    multiprocessing_wrapper returns a DataFrame whose datetime differences are exactly 1 minute.
    This should not be appended to factor_dfs and, since no other valid dfs exist, FactorEmptyError is raised.
    This test passes a list (not a single instance) to hit the other branch of the initial isinstance check.
    """
    module = importlib.import_module(MODULE_PATH)

    # Build a DataFrame with datetime differences of exactly 1 minute
    tuples = [
        (pd.Timestamp("2020-01-01 00:00:00"), "assetA"),
        (pd.Timestamp("2020-01-01 00:01:00"), "assetA"),
    ]
    mi = pd.MultiIndex.from_tuples(tuples, names=["datetime", "asset"])
    df_minute = pd.DataFrame({"f1": [1, 2]}, index=mi)

    FakeExperiment = _patch_module(module, [("ok", df_minute)])

    exp = FakeExperiment("justification-minute", sub_tasks_count=1)

    # Pass as a list to exercise the pathway where exp_or_list is already a list
    with pytest.raises(module.FactorEmptyError) as excinfo:
        module.process_factor_data([exp])

    assert "No valid factor data found" in str(excinfo.value)


def test_none_df_builds_error_message_round_088():
    """
    multiprocessing_wrapper returns a (message, None) pair.
    This should accumulate the message into error_message and be reported in the FactorEmptyError.
    """
    module = importlib.import_module(MODULE_PATH)

    FakeExperiment = _patch_module(module, [("some failure occurred", None)])

    exp = FakeExperiment("justification-none", sub_tasks_count=1)

    with pytest.raises(module.FactorEmptyError) as excinfo:
        module.process_factor_data(exp)

    # The raised error message should include the provided failure message
    assert "some failure occurred" in str(excinfo.value)
