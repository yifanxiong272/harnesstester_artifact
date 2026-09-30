import importlib
import types
import pytest

# Import the module under test
eval_mod = importlib.import_module("rdagent.components.coder.data_science.model.eval")

# Helper fakes used across tests
class FakeModelSingleFeedback:
    # Provide the attribute expected by the production code
    val_and_update_init_dict = staticmethod(lambda d: d)

    def __init__(self, **kwargs):
        # Accept arbitrary kwargs used in the code path and retain them
        self.__dict__.update(kwargs)
        # default final_decision if not provided
        if not hasattr(self, "final_decision"):
            self.final_decision = True

class FakeResult:
    def __init__(self, stdout, exit_code):
        self._stdout = stdout
        self.exit_code = exit_code

    def get_truncated_stdout(self):
        return self._stdout

class FakeImplementation:
    def __init__(self, file_dict=None, all_codes="all_codes_here"):
        self.file_dict = dict(file_dict or {})
        self.all_codes = all_codes
        self.injected = {}
        # record calls
        self.ran = []
        self.execed = []

    def inject_files(self, **kwargs):
        self.file_dict.update(kwargs)
        self.injected.update(kwargs)

    def run(self, env=None, entry=None):
        self.ran.append((env, entry))
        # entry is like 'python test/model_test.py'
        # Behavior configured by placing a special key in file_dict: '__run_result__'
        res = self.file_dict.get('__run_result__')
        if isinstance(res, FakeResult):
            return res
        # default: return non-empty stdout and success
        return FakeResult('ok-stdout', 0)

    def execute(self, env=None, entry=None):
        self.execed.append((env, entry))
        # behavior configured by file_dict key '__exec_result__'
        return self.file_dict.get('__exec_result__', 'workflow-stdout')

class FakeTask:
    def __init__(self, name="model01", info="task-info"):
        self.name = name
        self._info = info

    def get_task_information(self):
        return self._info

class FakeQueriedKnowledge:
    def __init__(self, success_map=None, failed_set=None):
        self.success_task_to_knowledge_dict = success_map or {}
        self.failed_task_info_set = failed_set or set()

# Fake scen required by evaluator base class
class FakeScen:
    def __init__(self, debug_path="fake/debug/path", timeout=30):
        self.debug_path = debug_path
        self._timeout = timeout

    def real_debug_timeout(self):
        return self._timeout

# Fake T factory used for template resolution in the module
class _Tobj:
    def __init__(self, key):
        self.key = key

    def r(self, **kwargs):
        # Return a string that includes the template key so tests can assert which branch was used
        # Include kwargs content in a deterministic way
        payload = ",".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"T_RES::{self.key}::{payload}"

def _T(key):
    return _Tobj(key)

# Fake get_ds_env to avoid external dependencies
def _get_ds_env(**kwargs):
    return {"env_marker": "fake_env", **kwargs}

# Fake remove_eda_part to show it's been invoked
def _remove_eda_part(s):
    return f"removed::{s}"

# Fake builder that mimics build_cls_from_json_with_retry contract
def _build_cls_from_json_with_retry(cls, system_prompt=None, user_prompt=None, init_kwargs_update_func=None):
    # Return an instance of the provided cls (we patch ModelSingleFeedback to FakeModelSingleFeedback in tests)
    inst = cls()
    # Attach prompts so tests can assert the right prompt template was used
    inst.system_prompt = system_prompt
    inst.user_prompt = user_prompt
    return inst


@pytest.fixture(autouse=True)
def patch_module_helpers(monkeypatch):
    """Patch environment-related helpers in the module to deterministic fakes."""
    # Ensure the module uses our fake ModelSingleFeedback to construct the ad-hoc failed-feedback
    monkeypatch.setattr(eval_mod, "ModelSingleFeedback", FakeModelSingleFeedback, raising=False)
    monkeypatch.setattr(eval_mod, "T", _T, raising=False)
    monkeypatch.setattr(eval_mod, "get_ds_env", _get_ds_env, raising=False)
    monkeypatch.setattr(eval_mod, "remove_eda_part", _remove_eda_part, raising=False)
    monkeypatch.setattr(eval_mod, "build_cls_from_json_with_retry", _build_cls_from_json_with_retry, raising=False)
    # No real network or filesystem access in tests
    yield


def test_success_short_circuit_round_060():
    """If queried_knowledge.success_task_to_knowledge_dict contains the task info, its feedback is returned."""
    task = FakeTask(name="model01", info="task-info-1")
    # Provide a fake feedback object
    sentinel_feedback = object()
    qk = FakeQueriedKnowledge(success_map={"task-info-1": types.SimpleNamespace(feedback=sentinel_feedback)})
    impl = FakeImplementation(file_dict={})

    evaluator = eval_mod.ModelGeneralCaseSpecEvaluator(FakeScen())
    fb = evaluator.evaluate(
        target_task=task,
        implementation=impl,
        gt_implementation=impl,
        queried_knowledge=qk,
    )

    assert fb is sentinel_feedback


def test_failed_short_circuit_round_060():
    """If queried_knowledge.failed_task_info_set contains the task info, a ModelSingleFeedback with final_decision=False is returned."""
    task = FakeTask(name="modelX", info="info-X")
    qk = FakeQueriedKnowledge(success_map={}, failed_set={"info-X"})
    impl = FakeImplementation(file_dict={})

    evaluator = eval_mod.ModelGeneralCaseSpecEvaluator(FakeScen())
    fb = evaluator.evaluate(
        target_task=task,
        implementation=impl,
        gt_implementation=impl,
        queried_knowledge=qk,
    )

    # The code constructs ModelSingleFeedback with final_decision=False in this branch
    assert isinstance(fb, FakeModelSingleFeedback)
    assert fb.final_decision is False
    # The messages should match the short-circuit strings set by the production code
    assert "skip implementation" in getattr(fb, "execution", "")


def test_run_stdout_none_raises_round_060():
    """When implementation.run() returns a result with None stdout the code raises CoderError."""
    task = FakeTask(name="my_model", info="info-raise")
    impl = FakeImplementation(file_dict={"my_model.py": "print('x')"})
    # Configure run to return a FakeResult with None stdout
    impl.file_dict['__run_result__'] = FakeResult(None, 1)

    evaluator = eval_mod.ModelGeneralCaseSpecEvaluator(FakeScen())
    with pytest.raises(eval_mod.CoderError):
        evaluator.evaluate(
            target_task=task,
            implementation=impl,
            gt_implementation=impl,
            queried_knowledge=None,
        )


def test_full_flow_with_test_and_main_round_060():
    """Full flow when model file exists, run succeeds and main.py exists: prompts come from model_eval.system and build function is used."""
    task = FakeTask(name="modelA", info="info-A")
    # Provide implementation that contains the model file and main.py
    impl = FakeImplementation(file_dict={
        "modelA.py": "print('model')",
        "main.py": "print('main')",
    }, all_codes="all_codes_here")
    # Configure run to return successful stdout
    impl.file_dict['__run_result__'] = FakeResult('unit-test-ok', 0)
    # Configure execute to return some workflow output
    impl.file_dict['__exec_result__'] = 'workflow-output'

    evaluator = eval_mod.ModelGeneralCaseSpecEvaluator(FakeScen())
    fb = evaluator.evaluate(
        target_task=task,
        implementation=impl,
        gt_implementation=impl,
        queried_knowledge=None,
    )

    # The fake builder attaches prompts to the returned instance
    assert isinstance(fb, FakeModelSingleFeedback)
    # Because ret_code == 0 and fake fb final_decision defaults True, final_decision remains True
    assert fb.final_decision is True
    # Check that system_prompt indicates the non-removed model flow template was used
    assert ".prompts:model_eval.system" in fb.system_prompt
    # The user prompt should contain the run stdout we provided
    assert "unit-test-ok" in fb.user_prompt


def test_model_removed_with_main_round_060():
    """When the model file is removed (not present), the rm prompt templates are used and workflow stdout is included when main.py executed."""
    task = FakeTask(name="gone_model", info="info-gone")
    # No model file, but main.py exists and execute returns workflow output
    impl = FakeImplementation(file_dict={
        "main.py": "print('main')",
    }, all_codes="all_codes_here")
    impl.file_dict['__exec_result__'] = 'workflow-main-output'
    # Make sure run() isn't relevant here; run is only for model file presence

    evaluator = eval_mod.ModelGeneralCaseSpecEvaluator(FakeScen())
    fb = evaluator.evaluate(
        target_task=task,
        implementation=impl,
        gt_implementation=impl,
        queried_knowledge=None,
    )

    assert isinstance(fb, FakeModelSingleFeedback)
    # system prompt created via the rm template in the removed-model branch
    assert ".prompts:model_eval_rm.system" in fb.system_prompt
    # user prompt should include the stdout message used by the removed branch
    assert "Model gone_model" in fb.user_prompt or "removal succeeded" in fb.user_prompt
