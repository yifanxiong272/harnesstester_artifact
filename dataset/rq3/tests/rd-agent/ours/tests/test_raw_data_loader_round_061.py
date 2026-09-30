import importlib
import types
import pytest

MODULE_PATH = "rdagent.components.coder.data_science.raw_data_loader"


class _FakeT:
    def __init__(self, key):
        self.key = key

    def r(self, **kwargs):
        parts = [self.key]
        for k in sorted(kwargs.keys()):
            parts.append(f"{k}={repr(kwargs[k])}")
        return "|".join(parts)


class _FakeSpecSession:
    def __init__(self, returns):
        if isinstance(returns, (list, tuple)):
            self._iter = iter(returns)
            self._last = None
        else:
            self._iter = None
            self._single = returns

    def build_chat_completion(self, user_prompt=None):
        if self._iter is not None:
            try:
                val = next(self._iter)
                self._last = val
                return val
            except StopIteration:
                return self._last
        else:
            return self._single


class _FakeAPIBackend:
    def __init__(self, messages_returns=None, session_returns=None):
        if isinstance(messages_returns, (list, tuple)):
            self._messages = list(messages_returns)
        else:
            self._messages = [messages_returns]
        self._session_returns = session_returns

    def build_chat_session(self, session_system_prompt=None):
        return _FakeSpecSession(self._session_returns)

    def build_messages_and_create_chat_completion(self, *, user_prompt, system_prompt):
        if len(self._messages) > 1:
            return self._messages.pop(0)
        return self._messages[0]


class _FakePythonAgentOut:
    @staticmethod
    def extract_output(obj):
        return obj

    @staticmethod
    def get_spec():
        return "PY_AGENT_SPEC"


class _FakePath:
    def __init__(self, text="FAKE_FILE"):
        self._text = text

    def __truediv__(self, other):
        return _FakePath(self._text)

    def read_text(self):
        return self._text


class _FakeScenario:
    def __init__(self):
        self.processed_data_folder_description = "processed_folder"

    def get_scenario_all_desc(self, eda_output=None):
        return {"eda": eda_output, "desc": "scenario_desc"}

    def get_runtime_environment(self):
        return {"env": "runtime"}


class _SimpleTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info


class _ImplWrapper:
    def __init__(self, load_code):
        self.implementation = types.SimpleNamespace(file_dict={"load_data.py": load_code})


def _make_loader_instance(module):
    cls = getattr(module, "DataLoaderMultiProcessEvolvingStrategy")
    inst = object.__new__(cls)
    inst.scen = _FakeScenario()
    return inst


def _make_qk_for_task(task_info, former_failed_list=None, similar_list=None):
    # Build a queried_knowledge-like simple namespace with mappings containing the task key
    if similar_list is None:
        similar_list = []
    # former_failed_list should be a list of _ImplWrapper
    if former_failed_list is None:
        former_failed_list = []
    # Task mapping: similar -> list, former_failed -> (list, meta)
    return types.SimpleNamespace(
        task_to_similar_task_successful_knowledge={task_info: similar_list},
        task_to_former_failed_traces={task_info: (former_failed_list, "meta")},
    )


def test_spec_generation_and_success_break_round_061(monkeypatch):
    """
    DS_RD_SETTING.spec_enabled = True
    workspace has no spec files -> triggers spec generation branch
    Provide queried_knowledge with proper mappings to avoid KeyError/IndexError.
    """
    module = importlib.import_module(MODULE_PATH)

    monkeypatch.setattr(module, "T", _FakeT)
    monkeypatch.setattr(module, "APIBackend", lambda: _FakeAPIBackend(messages_returns=["generated_code_v1"], session_returns=[
        "spec_dl",
        "spec_feature",
        "spec_model",
        "spec_ensemble",
        "spec_workflow",
    ]))
    monkeypatch.setattr(module, "PythonAgentOut", _FakePythonAgentOut)

    monkeypatch.setattr(module, "DS_RD_SETTING", types.SimpleNamespace(spec_enabled=True))

    workspace = types.SimpleNamespace(file_dict={})
    task = _SimpleTask("taskA")

    # Provide queried_knowledge containing the expected key "taskA" and empty lists
    qk = _make_qk_for_task("taskA")

    inst = _make_loader_instance(module)

    res = inst.implement_one_task(target_task=task, queried_knowledge=qk, workspace=workspace, prev_task_feedback=None)

    assert res["spec/data_loader.md"] == "spec_dl"
    assert res["spec/feature.md"] == "spec_feature"
    assert res["spec/model.md"] == "spec_model"
    assert res["spec/ensemble.md"] == "spec_ensemble"
    assert res["spec/workflow.md"] == "spec_workflow"
    assert res["load_data.py"] == "generated_code_v1"


def test_existing_spec_and_retry_then_break_round_061(monkeypatch):
    """
    DS_RD_SETTING.spec_enabled = True
    workspace contains spec files so branch uses workspace specs
    Queried former failed traces include one with same code (filtered out) and one different (kept)
    Agent first returns the same code as workspace (force retry), then returns new code and breaks.
    """
    module = importlib.import_module(MODULE_PATH)

    monkeypatch.setattr(module, "T", _FakeT)

    api = _FakeAPIBackend(messages_returns=["old_code", "new_code"], session_returns=None)
    monkeypatch.setattr(module, "APIBackend", lambda: api)
    monkeypatch.setattr(module, "PythonAgentOut", _FakePythonAgentOut)

    monkeypatch.setattr(module, "DS_RD_SETTING", types.SimpleNamespace(spec_enabled=True))

    workspace = types.SimpleNamespace(file_dict={
        "spec/data_loader.md": "dl_from_workspace",
        "spec/feature.md": "feature_ws",
        "spec/model.md": "model_ws",
        "spec/ensemble.md": "ens_ws",
        "spec/workflow.md": "wf_ws",
        "load_data.py": "old_code",
    })

    k_same = _ImplWrapper("old_code")
    k_other = _ImplWrapper("different_old_code")
    # Provide queried_knowledge mapping with both required keys
    qk = _make_qk_for_task("taskA", former_failed_list=[k_same, k_other], similar_list=[])

    task = _SimpleTask("taskA")
    inst = _make_loader_instance(module)

    res = inst.implement_one_task(target_task=task, queried_knowledge=qk, workspace=workspace, prev_task_feedback=None)

    assert res["spec/data_loader.md"] == "dl_from_workspace"
    assert res["spec/feature.md"] == "feature_ws"
    assert res["spec/model.md"] == "model_ws"
    assert res["load_data.py"] == "new_code"


def test_spec_disabled_raises_codererror_round_061(monkeypatch):
    """
    DS_RD_SETTING.spec_enabled = False
    DIRNAME patched to avoid filesystem access
    APIBackend always returns the same code as workspace so after 5 iterations, CoderError is raised.
    Provide queried_knowledge mapping to satisfy indexing logic.
    """
    module = importlib.import_module(MODULE_PATH)

    monkeypatch.setattr(module, "T", _FakeT)
    monkeypatch.setattr(module, "DIRNAME", _FakePath(text="EVAL_TEST_CONTENT"))

    api = _FakeAPIBackend(messages_returns=["identical_code"], session_returns=None)
    monkeypatch.setattr(module, "APIBackend", lambda: api)
    monkeypatch.setattr(module, "PythonAgentOut", _FakePythonAgentOut)

    monkeypatch.setattr(module, "DS_RD_SETTING", types.SimpleNamespace(spec_enabled=False))

    workspace = types.SimpleNamespace(file_dict={"load_data.py": "identical_code"})
    task = _SimpleTask("taskA")

    # Provide queried_knowledge mapping so the code does not crash before the retry loop
    qk = _make_qk_for_task("taskA")

    inst = _make_loader_instance(module)

    with pytest.raises(module.CoderError) as exc:
        inst.implement_one_task(target_task=task, queried_knowledge=qk, workspace=workspace, prev_task_feedback=None)

    assert "Failed to generate a new data loader code." in str(exc.value)
