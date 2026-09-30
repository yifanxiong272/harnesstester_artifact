import types
from types import SimpleNamespace

import pytest

from rdagent.components.coder.CoSTEER import knowledge_management as km


def make_trace_entry(return_checking: bool):
    """Create a minimal trace entry with the expected .feedback.return_checking attribute."""
    return SimpleNamespace(feedback=SimpleNamespace(return_checking=return_checking))


def make_task(info):
    """Create a minimal task object with get_task_information() method."""

    class T:
        def get_task_information(self):
            return info

    return T()


def make_self(fail_task_trial_limit: int, success_dict=None, working_trace=None):
    """Create a fake self with .settings.fail_task_trial_limit and .knowledgebase attributes used by the method."""
    settings = SimpleNamespace(fail_task_trial_limit=fail_task_trial_limit)
    kb = SimpleNamespace()
    kb.success_task_to_knowledge_dict = success_dict if success_dict is not None else {}
    kb.working_trace_knowledge = working_trace if working_trace is not None else {}
    return SimpleNamespace(settings=settings, knowledgebase=kb)


def make_evo_with_subtasks(tasks):
    return SimpleNamespace(sub_tasks=tasks)


def make_queried_v2():
    # Minimal shape expected by former_trace_query: has failed_task_info_set and task_to_former_failed_traces
    return SimpleNamespace(failed_task_info_set=set(), task_to_former_failed_traces={})


def test_failed_task_info_added_round_104():
    """If a task has trials >= fail_task_trial_limit it should be recorded in failed_task_info_set and assigned ([], None).

    Covers branch where first if (len >= limit) is True and the subsequent detailed branch is skipped.
    """
    key = "task-A"
    # create two trace entries to meet the fail limit
    trace_list = [make_trace_entry(True), make_trace_entry(False)]
    working_trace = {key: trace_list}

    self_obj = make_self(fail_task_trial_limit=2, success_dict={}, working_trace=working_trace)
    evo = make_evo_with_subtasks([make_task(key)])
    queried = make_queried_v2()

    # Call the unbound method with our fake self
    res = km.CoSTEERRAGStrategyV2.former_trace_query(
        self_obj,
        evo,
        queried,
    )

    # Assertions: failed_task_info_set contains the key and the mapping entry is ([], None)
    assert key in queried.failed_task_info_set
    assert queried.task_to_former_failed_traces[key] == ([], None)
    # function returns the same object
    assert res is queried


def test_former_trace_pop_and_latest_attempt_none_round_104():
    """Test that middle entries are popped when previous.return_checking is True and current is False,
    and latest_attempt remains None if the remaining last element was the original last.

    This exercises the while loop that pops elements and the path where latest_attempt is not set.
    """
    key = "task-B"
    # Original working trace: [A(True), B(False), C(True)] -> B should be popped -> former_trace becomes [A,C]
    A = make_trace_entry(True)
    B = make_trace_entry(False)
    C = make_trace_entry(True)
    original = [A, B, C]

    working_trace = {key: original}
    self_obj = make_self(fail_task_trial_limit=10, success_dict={}, working_trace=working_trace)
    evo = make_evo_with_subtasks([make_task(key)])
    queried = make_queried_v2()

    res = km.CoSTEERRAGStrategyV2.former_trace_query(
        self_obj,
        evo,
        queried,
        v2_query_former_trace_limit=5,
        v2_add_fail_attempt_to_latest_successful_execution=True,
    )

    # After popping, the recorded former traces should reflect the popped element and latest_attempt should be None
    ft, latest = queried.task_to_former_failed_traces[key]
    # former_trace should be a list of the two surviving entries
    assert ft == [A, C]
    assert latest is None
    assert res is queried


def test_latest_attempt_assigned_round_104():
    """When the last element in the copy is popped, the former_trace_knowledge last element may correspond
    to an earlier index in the original working trace; in that case latest_attempt should be assigned to the
    last element of the original working_trace_knowledge.

    This covers the branch where latest_attempt is set.
    """
    key = "task-C"
    # Original: [A(True), B(True), C(False)] -> C (original last) will be popped by the loop,
    # leaving former_trace [A, B]. former_trace[-1] (B) has index 1 < len(original)-1 (2),
    # so latest_attempt should be original[-1] (C)
    A = make_trace_entry(True)
    B = make_trace_entry(True)
    C = make_trace_entry(False)
    original = [A, B, C]

    working_trace = {key: original}
    self_obj = make_self(fail_task_trial_limit=10, success_dict={}, working_trace=working_trace)
    evo = make_evo_with_subtasks([make_task(key)])
    queried = make_queried_v2()

    res = km.CoSTEERRAGStrategyV2.former_trace_query(
        self_obj,
        evo,
        queried,
        v2_query_former_trace_limit=5,
        v2_add_fail_attempt_to_latest_successful_execution=True,
    )

    ft, latest = queried.task_to_former_failed_traces[key]
    # former_trace should have had the last element removed
    assert ft == [A, B]
    # latest_attempt should be the original last element
    assert latest is C
    assert res is queried
