# file: rdagent/components/coder/factor_coder/evolving_strategy.py:60-164
# asked: {"lines": [67, 69, 70, 71, 72, 75, 76, 77, 78, 79, 82, 84, 85, 86, 87, 90, 92, 93, 94, 95, 96, 97, 99, 100, 102, 104, 105, 107, 108, 110, 111, 112, 113, 116, 118, 119, 120, 121, 122, 123, 126, 127, 129, 130, 131, 132, 133, 135, 136, 137, 138, 139, 140, 142, 143, 144, 145, 146, 149, 150, 151, 153, 154, 155, 157, 159, 161, 162, 164], "branches": [[75, 76], [75, 82], [102, 104], [102, 138], [104, 110], [104, 116], [125, 129], [125, 130], [130, 131], [130, 132], [132, 135], [132, 136], [136, 102], [136, 137], [138, 139], [138, 164], [154, 155], [154, 157]]}
# gained: {"lines": [67, 69, 70, 71, 75, 76, 77, 78, 84, 85, 86, 90, 92, 93, 94, 95, 96, 97, 99, 100, 102, 104, 105, 116, 118, 119, 120, 121, 122, 123, 126, 127, 129, 138, 139, 140, 142, 143, 144, 145, 146, 149, 150, 159], "branches": [[75, 76], [102, 104], [104, 116], [125, 129], [138, 139]]}

import json
import importlib
import pytest
from types import SimpleNamespace

mod = importlib.import_module("rdagent.components.coder.factor_coder.evolving_strategy")


class DummyTask:
    def get_task_information(self):
        return "factor_info"


class DummyScene:
    def get_scenario_all_desc(self, target_task, filtered_tag="feature"):
        return {"desc": "scenario_desc"}


class DummyTObj:
    def __init__(self, key=None):
        self.key = key

    def r(self, **kwargs):
        if "evolving_strategy_factor_implementation_v1_system" in (self.key or ""):
            return "SYSTEM_PROMPT"
        return "USER_PROMPT"


class DummyTFactory:
    def __init__(self, key=None):
        self.key = key

    def __call__(self, key):
        return DummyTObj(key)


def make_qv2(success_list=None, error_dict=None, former_failed=None):
    class QV2:
        pass

    inst = QV2()
    inst.task_to_similar_task_successful_knowledge = {"factor_info": success_list or []}
    inst.task_to_similar_error_successful_knowledge = {"factor_info": error_dict or {}}
    inst.task_to_former_failed_traces = {"factor_info": [former_failed or [], "latest_success"]}
    return QV2, inst


def make_q_non_v2(success_list=None, former_failed=None):
    class QNonV2:
        pass

    inst = QNonV2()
    inst.task_to_similar_task_successful_knowledge = {"factor_info": success_list or []}
    inst.task_to_former_failed_traces = {"factor_info": [former_failed or [], "latest_success"]}
    return inst


class DummyAPIBackend:
    def __init__(self, use_chat_cache=False, behavior=None):
        self.use_chat_cache = use_chat_cache
        self.behavior = behavior or {}
        self.chat_token_limit = self.behavior.get("chat_token_limit", 1000)
        self._create_calls = 0

    def build_messages_and_calculate_token(self, user_prompt=None, system_prompt=None):
        return self.behavior.get("token_value", 10)

    def build_messages_and_create_chat_completion(self, user_prompt=None, system_prompt=None, json_mode=False, json_target_type=None):
        self._create_calls += 1
        if "create_raises" in self.behavior:
            exc = self.behavior["create_raises"]
            if callable(exc):
                raise exc(self._create_calls)
            raise exc
        if "create_return" in self.behavior:
            return self.behavior["create_return"]
        return '{"code":"default()"}'


@pytest.fixture(autouse=True)
def setup_common(monkeypatch):
    monkeypatch.setattr(mod, "T", DummyTFactory())
    yield


def make_strategy_instance():
    inst = object.__new__(mod.FactorMultiProcessEvolvingStrategy)
    inst.scen = DummyScene()
    return inst


def test_implement_one_task_returns_code_from_json(monkeypatch):
    strategy = make_strategy_instance()
    task = DummyTask()
    QV2, qinst = make_qv2(success_list=["succ_impl"], error_dict={}, former_failed=[{"failed": "trace"}])
    monkeypatch.setattr(mod, "CoSTEERQueriedKnowledgeV2", QV2)
    monkeypatch.setattr(mod, "FACTOR_COSTEER_SETTINGS", SimpleNamespace(v2_error_summary=False, coder_use_cache=False))
    api_behavior = {"token_value": 5, "create_return": json.dumps({"code": "print(1)"})}
    monkeypatch.setattr(mod, "APIBackend", lambda use_chat_cache=False, behavior=api_behavior: DummyAPIBackend(use_chat_cache=use_chat_cache, behavior=behavior))
    code = strategy.implement_one_task(task, qinst, workspace=None, prev_task_feedback=None)
    assert code == "print(1)"


def test_implement_one_task_parses_python_block_and_uses_error_summary(monkeypatch):
    strategy = make_strategy_instance()
    task = DummyTask()
    QV2, qinst = make_qv2(success_list=["succ_impl"], error_dict={"TypeError": [["imp", "succ"]]}, former_failed=[{"failed": "trace"}])
    monkeypatch.setattr(mod, "CoSTEERQueriedKnowledgeV2", QV2)
    monkeypatch.setattr(mod, "FACTOR_COSTEER_SETTINGS", SimpleNamespace(v2_error_summary=True, coder_use_cache=True))

    # Build code_block so that it contains the 