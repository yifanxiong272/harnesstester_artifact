import pytest

from sweagent.agent.reviewer import ChooserRetryLoop


class DummyChooserOutput:
    def __init__(self, chosen_idx):
        self.chosen_idx = chosen_idx


class DummyChooser:
    def __init__(self, return_idx):
        self.return_idx = return_idx
        self.call_count = 0
        self.last_args = None

    def choose(self, problem_statement, submissions):
        # record call then return a DummyChooserOutput
        self.call_count += 1
        # be explicit about copying references so tests can assert identity if needed
        self.last_args = (problem_statement, submissions)
        return DummyChooserOutput(self.return_idx)


class DummyProblemStatement:
    def __init__(self, payload):
        self._payload = payload

    def get_problem_statement(self):
        return self._payload


def make_instance():
    """Create a ChooserRetryLoop instance without running its __init__.

    This allows us to inject minimal attributes required by get_best.
    """
    inst = object.__new__(ChooserRetryLoop)
    return inst


def test_get_best_cached_round_050():
    # If _chooser_output is present, get_best should return its chosen_idx
    inst = make_instance()
    # Pre-set a cached chooser output -> should short-circuit and not call chooser.choose
    inst._chooser_output = DummyChooserOutput(2)
    inst._submissions = ["ignored"]

    # Put a chooser that would raise if called to ensure it's not invoked
    class ExplodingChooser:
        def choose(self, *a, **k):
            raise AssertionError("chooser.choose was called when it should not be")

    inst._chooser = ExplodingChooser()
    inst._problem_statement = DummyProblemStatement("ps")

    result = inst.get_best()
    assert result == 2


def test_get_best_no_submissions_round_050():
    # If no chooser_output and no submissions -> returns None and does not call chooser
    inst = make_instance()
    inst._chooser_output = None
    inst._submissions = []

    class ExplodingChooser:
        def choose(self, *a, **k):
            raise AssertionError("chooser.choose was called when it should not be")

    inst._chooser = ExplodingChooser()
    inst._problem_statement = DummyProblemStatement({"key": "value"})

    result = inst.get_best()
    assert result is None


def test_get_best_invoke_chooser_and_cache_round_050():
    # When no cached output but there are submissions, chooser.choose should be invoked,
    # its return object cached on the instance, and its chosen_idx returned.
    inst = make_instance()
    inst._chooser_output = None

    subs = ["s1", "s2"]
    inst._submissions = subs

    ps_payload = {"prompt": "choose the best"}
    inst._problem_statement = DummyProblemStatement(ps_payload)

    chooser = DummyChooser(return_idx=7)
    inst._chooser = chooser

    # First call should invoke chooser.choose exactly once
    result = inst.get_best()
    assert result == 7
    assert isinstance(inst._chooser_output, DummyChooserOutput)
    assert inst._chooser_output.chosen_idx == 7

    # chooser.choose should have been called once with the problem statement and the same submissions list
    assert chooser.call_count == 1
    # ensure the exact payload object and submissions object were passed through
    passed_ps, passed_subs = chooser.last_args
    assert passed_ps is ps_payload
    assert passed_subs is subs

    # Subsequent call should short-circuit and return cached chosen_idx without calling chooser again
    second = inst.get_best()
    assert second == 7
    assert chooser.call_count == 1
