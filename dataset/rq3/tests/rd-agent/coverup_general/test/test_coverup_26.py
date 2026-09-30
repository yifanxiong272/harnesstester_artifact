# file: rdagent/components/coder/data_science/model/eval.py:38-123
# asked: {"lines": [46, 48, 49, 51, 52, 53, 54, 55, 56, 57, 60, 61, 62, 65, 67, 68, 69, 70, 72, 73, 74, 75, 77, 78, 79, 82, 83, 84, 86, 87, 88, 90, 92, 93, 94, 95, 96, 98, 99, 100, 103, 104, 105, 106, 107, 108, 110, 111, 112, 115, 117, 118, 121, 123], "branches": [[47, 51], [47, 52], [52, 53], [52, 60], [67, 68], [67, 82], [77, 78], [77, 86], [86, 87], [86, 90], [92, 93], [92, 103]]}
# gained: {"lines": [46, 48, 49, 51, 52, 53, 54, 55, 56, 57, 60, 61, 62, 65, 67, 68, 69, 70, 72, 73, 74, 75, 77, 78, 79, 86, 87, 88, 90, 92, 103, 104, 105, 106, 107, 108, 110, 111, 112, 115, 117, 118, 121, 123], "branches": [[47, 51], [47, 52], [52, 53], [52, 60], [67, 68], [77, 78], [77, 86], [86, 87], [86, 90], [92, 103]]}

import importlib
import types
import pytest

def make_dummy_result(stdout_value, exit_code=0):
    class Result:
        def __init__(self, stdout_value, exit_code):
            self._stdout = stdout_value
            self.exit_code = exit_code
        def get_truncated_stdout(self):
            return self._stdout
    return Result(stdout_value, exit_code)

class DummyFBWorkspace:
    def __init__(self, file_dict=None, all_codes=""):
        self.file_dict = dict(file_dict or {})
        self._injected = {}
        self.all_codes = all_codes
        # attributes to control behavior
        self._run_result = make_dummy_result("ok", exit_code=0)
        self._execute_result = "workflow output"

    def inject_files(self, **kwargs):
        self._injected.update(kwargs)
        # also reflect injected files into file_dict for possible usage
        self.file_dict.update(kwargs)

    def run(self, env=None, entry=None):
        return self._run_result

    def execute(self, env=None, entry=None):
        return self._execute_result

class DummyTask:
    def __init__(self, name, info):
        self.name = name
        self._info = info
    def get_task_information(self):
        return self._info

class DummyQueriedKnowledge:
    def __init__(self, success_map=None, failed_set=None):
        self.success_task_to_knowledge_dict = success_map or {}
        self.failed_task_info_set = set(failed_set or ())

def setup_common_patches(monkeypatch, mod):
    # patch get_ds_env to return a dummy env
    monkeypatch.setattr(mod, "get_ds_env", lambda *args, **kwargs: {"env": "dummy"})

    # patch remove_eda_part to be identity
    monkeypatch.setattr(mod, "remove_eda_part", lambda x: f"removed_eda:{x}")

    # patch T to a simple templater with r method
    class SimpleT:
        def __init__(self, path):
            self.path = path
            self.last_r_args = None
        def r(self, **kwargs):
            # return a string that includes template path and kwargs for testing
            self.last_r_args = kwargs
            return f"TEMPLATE[{self.path}] ARGS:{kwargs}"
    monkeypatch.setattr(mod, "T", SimpleT)

    # patch ModelSingleFeedback in module to a simple class
    class ModelSingleFeedback:
        def __init__(self, execution=None, return_checking=None, code=None, final_decision=True, **kwargs):
            self.execution = execution
            self.return_checking = return_checking
            self.code = code
            self.final_decision = final_decision
            # store any extra kwargs for inspection
            for k, v in kwargs.items():
                setattr(self, k, v)
        @classmethod
        def val_and_update_init_dict(cls, d):
            # identity function for the init dict update (used by build function)
            return d
    monkeypatch.setattr(mod, "ModelSingleFeedback", ModelSingleFeedback)

    # prepare a build function that captures inputs and returns an instance
    captured = {}
    def fake_build(cls, system_prompt, user_prompt, init_kwargs_update_func=None):
        captured['cls'] = cls
        captured['system_prompt'] = system_prompt
        captured['user_prompt'] = user_prompt
        captured['update_func'] = init_kwargs_update_func
        # return an instance with final_decision True by default
        return ModelSingleFeedback(execution="exec", return_checking="rc", code="code", final_decision=True)
    monkeypatch.setattr(mod, "build_cls_from_json_with_retry", fake_build)
    return captured

def test_evaluate_returns_queried_success(monkeypatch):
    mod = importlib.import_module("rdagent.components.coder.data_science.model.eval")
    captured = setup_common_patches(monkeypatch, mod)

    evaluator = mod.ModelGeneralCaseSpecEvaluator.__new__(mod.ModelGeneralCaseSpecEvaluator)
    # set minimal scen attribute used in get_ds_env call
    evaluator.scen = types.SimpleNamespace(debug_path="dbg", real_debug_timeout=lambda: 10)

    # prepare task and queried knowledge that indicates success
    task = DummyTask(name="model01", info="info_key")
    # the success mapping stores an object with a 'feedback' attribute
    feedback_obj = object()
    qk = DummyQueriedKnowledge(success_map={"info_key": types.SimpleNamespace(feedback=feedback_obj)})

    impl = DummyFBWorkspace(file_dict={})
    # call evaluate and expect it to return the feedback directly
    res = evaluator.evaluate(target_task=task, implementation=impl, gt_implementation=None, queried_knowledge=qk)
    assert res is feedback_obj

def test_evaluate_returns_failed_feedback(monkeypatch):
    mod = importlib.import_module("rdagent.components.coder.data_science.model.eval")
    captured = setup_common_patches(monkeypatch, mod)

    evaluator = mod.ModelGeneralCaseSpecEvaluator.__new__(mod.ModelGeneralCaseSpecEvaluator)
    evaluator.scen = types.SimpleNamespace(debug_path="dbg", real_debug_timeout=lambda: 10)

    task = DummyTask(name="m2", info="fail_info")
    qk = DummyQueriedKnowledge(failed_set={"fail_info"})

    impl = DummyFBWorkspace(file_dict={})
    res = evaluator.evaluate(target_task=task, implementation=impl, gt_implementation=None, queried_knowledge=qk)
    # Should be an instance of patched ModelSingleFeedback with final_decision False
    assert isinstance(res, mod.ModelSingleFeedback)
    assert res.final_decision is False
    assert "failed too many times" in (res.code or "").lower()

def test_evaluate_model_removal_raises_on_none_stdout(monkeypatch):
    mod = importlib.import_module("rdagent.components.coder.data_science.model.eval")
    captured = setup_common_patches(monkeypatch, mod)

    evaluator = mod.ModelGeneralCaseSpecEvaluator.__new__(mod.ModelGeneralCaseSpecEvaluator)
    evaluator.scen = types.SimpleNamespace(debug_path="dbg", real_debug_timeout=lambda: 10)

    task = DummyTask(name="to_remove", info="i1")
    # implementation has the model file so removal branch triggers
    impl = DummyFBWorkspace(file_dict={f"{task.name}.py": "some code"})
    # set run result to have None stdout to trigger CoderError
    impl._run_result = make_dummy_result(None, exit_code=1)

    # ensure CoderError from module is raised
    with pytest.raises(mod.CoderError):
        evaluator.evaluate(target_task=task, implementation=impl, gt_implementation=None, queried_knowledge=None)

def test_evaluate_model_removed_with_main_and_build(monkeypatch):
    mod = importlib.import_module("rdagent.components.coder.data_science.model.eval")
    captured = setup_common_patches(monkeypatch, mod)

    evaluator = mod.ModelGeneralCaseSpecEvaluator.__new__(mod.ModelGeneralCaseSpecEvaluator)
    evaluator.scen = types.SimpleNamespace(debug_path="dbg", real_debug_timeout=lambda: 10)

    task = DummyTask(name="rem", info="info_rem")
    # create implementation with model file and main.py
    impl = DummyFBWorkspace(file_dict={f"{task.name}.py": "model code", "main.py": "workflow"}, all_codes="ALL")
    # run should return some stdout (not None) so code follows the non-error removal path
    impl._run_result = make_dummy_result("some stdout", exit_code=0)
    # execute should return a workflow string with eda parts that will be removed
    impl._execute_result = "EDA_START\nresults\nEDA_END"

    res = evaluator.evaluate(target_task=task, implementation=impl, gt_implementation=None, queried_knowledge=None)

    # build_cls_from_json_with_retry should have been called and returned our patched ModelSingleFeedback
    assert isinstance(res, mod.ModelSingleFeedback)
    # final_decision should remain True because ret_code was 0
    assert res.final_decision is True
    # ensure the fake build received system and user prompts strings
    assert "TEMPLATE" in captured['system_prompt']
    assert "TEMPLATE" in captured['user_prompt']

def test_evaluate_model_removed_without_main_uses_none_workflow(monkeypatch):
    mod = importlib.import_module("rdagent.components.coder.data_science.model.eval")
    captured = setup_common_patches(monkeypatch, mod)

    evaluator = mod.ModelGeneralCaseSpecEvaluator.__new__(mod.ModelGeneralCaseSpecEvaluator)
    evaluator.scen = types.SimpleNamespace(debug_path="dbg", real_debug_timeout=lambda: 10)

    task = DummyTask(name="rem2", info="info_r2")
    # implementation has only model file, no main.py
    impl = DummyFBWorkspace(file_dict={f"{task.name}.py": "model code"}, all_codes="ALLCODES")
    impl._run_result = make_dummy_result("stdout present", exit_code=0)

    res = evaluator.evaluate(target_task=task, implementation=impl, gt_implementation=None, queried_knowledge=None)

    assert isinstance(res, mod.ModelSingleFeedback)
    # check that system_prompt captured includes the task description in it (our SimpleT returns ARGS dict)
    assert "ARGS" in captured['system_prompt']
    # since no main.py, workflow passed to template should be None (the r args will include workflow_stdout)
    assert 'workflow_stdout' in captured['system_prompt']
