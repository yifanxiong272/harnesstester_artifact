import types
from types import SimpleNamespace
import builtins

import pytest

from rdagent.components.coder.CoSTEER import knowledge_management as km

# Helper small test doubles
class DummyTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info

class DummyEvolvableSubjects:
    def __init__(self, sub_tasks, sub_workspace_list):
        self.sub_tasks = sub_tasks
        self.sub_workspace_list = sub_workspace_list

class DummyEvoStep:
    def __init__(self, evolvable_subjects, feedback):
        self.evolvable_subjects = evolvable_subjects
        self.feedback = feedback

class DummyFeedback:
    def __init__(self, final_decision, return_checking=None, execution=None):
        self.final_decision = final_decision
        self.return_checking = return_checking
        self.execution = execution


def make_strategy_with_simple_kb():
    # Create an instance without running the real __init__ to avoid heavy setup
    strategy = km.CoSTEERRAGStrategyV2.__new__(km.CoSTEERRAGStrategyV2)
    # initial counters
    strategy.current_generated_trace_count = 0

    # Prepare a simple knowledgebase object with required attributes and a recorder
    update_calls = []

    def _update_success_task(info):
        update_calls.append(info)

    knowledgebase = SimpleNamespace(
        success_task_to_knowledge_dict={},
        task_to_component_nodes={},
        working_trace_knowledge={},
        working_trace_error_analysis={},
        update_success_task=_update_success_task,
    )
    strategy.knowledgebase = knowledgebase

    # attach simple analyze_component and analyze_error helpers
    def analyze_component(target_task_information):
        # return a predictable node list
        return [f"component_node_for:{target_task_information}"]

    def analyze_error(value_or_exec, feedback_type="value"):
        # return predictable analysis result dependent on args
        return [f"analysis:{feedback_type}:{value_or_exec}"]

    strategy.analyze_component = analyze_component
    strategy.analyze_error = analyze_error

    # expose update_calls for assertions
    strategy._update_calls = update_calls
    return strategy


def test_generate_knowledge_early_return_round_059():
    """When evolving_trace length equals current_generated_trace_count, should return None and not mutate KB."""
    strategy = make_strategy_with_simple_kb()
    strategy.current_generated_trace_count = 2

    # make a dummy evolving_trace of same length
    evolving_trace = [1, 2]

    result = strategy.generate_knowledge(evolving_trace, return_knowledge=False)

    assert result is None
    # ensure nothing was added to knowledgebase
    assert strategy.knowledgebase.working_trace_knowledge == {}
    assert strategy.knowledgebase.working_trace_error_analysis == {}
    assert strategy.knowledgebase.success_task_to_knowledge_dict == {}


def test_generate_knowledge_success_path_round_059():
    """Covers branch where some implementations are None (skipped) and a final_decision == True triggers success path."""
    strategy = make_strategy_with_simple_kb()

    # task 0 should be skipped because implementation is None or feedback is None
    t0 = DummyTask("task0_info")
    impl0 = None
    fb0 = None

    # task 1 should be processed and marked success
    t1 = DummyTask("task1_info")
    impl1 = {"code": "impl1"}
    fb1 = DummyFeedback(final_decision=True, return_checking=None, execution=None)

    subjects = DummyEvolvableSubjects(sub_tasks=[t0, t1], sub_workspace_list=[impl0, impl1])
    evo = DummyEvoStep(evolvable_subjects=subjects, feedback=[fb0, fb1])

    # run generation
    result = strategy.generate_knowledge([evo], return_knowledge=False)

    assert result is None

    # verify only task1 was added to working_trace_knowledge
    key = t1.get_task_information()
    assert key in strategy.knowledgebase.working_trace_knowledge
    wk_list = strategy.knowledgebase.working_trace_knowledge[key]
    assert isinstance(wk_list, list) and len(wk_list) == 1

    single_k = wk_list[0]
    # CoSTEERKnowledge stores the passed objects, ensure they match
    assert getattr(single_k, "implementation") == impl1
    assert getattr(single_k, "feedback") == fb1

    # success_task_to_knowledge_dict should be set for this key
    assert key in strategy.knowledgebase.success_task_to_knowledge_dict
    assert strategy.knowledgebase.success_task_to_knowledge_dict[key] == single_k

    # update_success_task should have been called with the key
    assert strategy._update_calls == [key]

    # and task_to_component_nodes should have been populated by analyze_component
    assert key in strategy.knowledgebase.task_to_component_nodes
    assert strategy.knowledgebase.task_to_component_nodes[key] == [f"component_node_for:{key}"]

    # ensure counter updated
    assert strategy.current_generated_trace_count == 1


def test_generate_knowledge_error_paths_round_059():
    """Covers both error branches: return_checking truthy (value) and falsy (use execution)"""
    strategy = make_strategy_with_simple_kb()

    # Prepare two tasks to exercise two error-analysis branches
    t_val = DummyTask("task_value_info")
    impl_val = {"code": "impl_val"}
    fb_val = DummyFeedback(final_decision=False, return_checking={"ok": True}, execution=None)

    t_exec = DummyTask("task_exec_info")
    impl_exec = {"code": "impl_exec"}
    fb_exec = DummyFeedback(final_decision=False, return_checking=None, execution={"trace": "err"})

    subjects = DummyEvolvableSubjects(
        sub_tasks=[t_val, t_exec],
        sub_workspace_list=[impl_val, impl_exec],
    )
    evo = DummyEvoStep(evolvable_subjects=subjects, feedback=[fb_val, fb_exec])

    result = strategy.generate_knowledge([evo], return_knowledge=False)
    assert result is None

    # For both tasks, working_trace_knowledge should have entries
    kv = t_val.get_task_information()
    ke = t_exec.get_task_information()
    assert kv in strategy.knowledgebase.working_trace_knowledge
    assert ke in strategy.knowledgebase.working_trace_knowledge

    # No success entries should exist (both final_decision False)
    assert kv not in strategy.knowledgebase.success_task_to_knowledge_dict
    assert ke not in strategy.knowledgebase.success_task_to_knowledge_dict

    # Verify error analysis appended for both keys and matches analyze_error return format
    assert kv in strategy.knowledgebase.working_trace_error_analysis
    assert ke in strategy.knowledgebase.working_trace_error_analysis

    err_val_result = strategy.knowledgebase.working_trace_error_analysis[kv]
    err_exec_result = strategy.knowledgebase.working_trace_error_analysis[ke]

    # analyze_error returns a list; function stores the returned list as an element in the error_analysis list
    assert err_val_result and isinstance(err_val_result, list)
    assert err_exec_result and isinstance(err_exec_result, list)

    # Check that the analysis content encodes the feedback_type used
    assert err_val_result[0] == [f"analysis:value:{fb_val.return_checking}"] or err_val_result[0] == f"analysis:value:{fb_val.return_checking}" or (isinstance(err_val_result[0], list) and err_val_result[0][0].startswith("analysis:value:"))
    assert err_exec_result[0] == [f"analysis:execution:{fb_exec.execution}"] or err_exec_result[0] == f"analysis:execution:{fb_exec.execution}" or (isinstance(err_exec_result[0], list) and err_exec_result[0][0].startswith("analysis:execution:"))

    # ensure analyze_component was used to populate component nodes for each
    assert strategy.knowledgebase.task_to_component_nodes[kv] == [f"component_node_for:{kv}"]
    assert strategy.knowledgebase.task_to_component_nodes[ke] == [f"component_node_for:{ke}"]

    # ensure counter updated
    assert strategy.current_generated_trace_count == 1
