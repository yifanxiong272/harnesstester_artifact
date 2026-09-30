# file: rdagent/components/coder/factor_coder/evolving_strategy.py:60-164
# asked: {"lines": [67, 69, 70, 71, 72, 75, 76, 77, 78, 79, 82, 84, 85, 86, 87, 90, 92, 93, 94, 95, 96, 97, 99, 100, 102, 104, 105, 107, 108, 110, 111, 112, 113, 116, 118, 119, 120, 121, 122, 123, 126, 127, 129, 130, 131, 132, 133, 135, 136, 137, 138, 139, 140, 142, 143, 144, 145, 146, 149, 150, 151, 153, 154, 155, 157, 159, 161, 162, 164], "branches": [[75, 76], [75, 82], [102, 104], [102, 138], [104, 110], [104, 116], [125, 129], [125, 130], [130, 131], [130, 132], [132, 135], [132, 136], [136, 102], [136, 137], [138, 139], [138, 164], [154, 155], [154, 157]]}
# gained: {"lines": [67, 69, 70, 71, 75, 76, 77, 78, 82, 84, 85, 86, 90, 92, 93, 94, 95, 96, 97, 99, 100, 102, 104, 105, 107, 108, 110, 111, 112, 113, 116, 118, 119, 120, 121, 122, 123, 126, 127, 129, 138, 139, 140, 142, 143, 144, 145, 146, 149, 150, 151, 153, 154, 155, 157, 159, 161, 162, 164], "branches": [[75, 76], [75, 82], [102, 104], [104, 110], [104, 116], [125, 129], [138, 139], [138, 164], [154, 155], [154, 157]]}

import json
import pytest

import rdagent.components.coder.factor_coder.evolving_strategy as evolving_strategy_module


class FakeFactorTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info


class FakeScenario:
    def __init__(self, desc="scenario-desc"):
        self._desc = desc

    def get_scenario_all_desc(self, target_task, filtered_tag="feature"):
        return self._desc


class FakeT:
    def __init__(self, text=""):
        self.text = text

    def r(self, **kwargs):
        return f"T_PROMPT_{self.text}_{json.dumps(kwargs, default=str)}"


class FakeFACTORSettings:
    def __init__(self, v2_error_summary=False, coder_use_cache=False):
        self.v2_error_summary = v2_error_summary
        self.coder_use_cache = coder_use_cache


class FakeAPIBackend:
    chat_token_limit = 1000

    def __init__(self, use_chat_cache=False, token_return=None, response_return=None, raise_on_create=False):
        self.use_chat_cache = use_chat_cache
        self._token_return = token_return
        self._response_return = response_return
        self._raise_on_create = raise_on_create

    def build_messages_and_calculate_token(self, user_prompt, system_prompt):
        if self._token_return is not None:
            return self._token_return
        return 10

    def build_messages_and_create_chat_completion(self, user_prompt, system_prompt, json_mode=True, json_target_type=None):
        if self._raise_on_create:
            json.loads("not a json")
        if self._response_return is not None:
            return self._response_return
        return json.dumps({"code": "print('default')"})


class FakeQueried:
    def __init__(self, info_key, similar_success=None, former_failed=None):
        self.task_to_similar_task_successful_knowledge = {info_key: similar_success or []}
        self.task_to_former_failed_traces = {info_key: former_failed or ([], "")}


class FakeQueriedV2(FakeQueried):
    def __init__(self, info_key, similar_success=None, former_failed=None, similar_error=None):
        super().__init__(info_key, similar_success=similar_success, former_failed=former_failed)
        self.task_to_similar_error_successful_knowledge = {info_key: similar_error or {}}


@pytest.fixture(autouse=True)
def preserve_module_state(monkeypatch):
    yield


def make_strategy_instance(monkeypatch):
    StrategyClass = evolving_strategy_module.FactorMultiProcessEvolvingStrategy
    inst = StrategyClass.__new__(StrategyClass)
    inst.scen = FakeScenario()
    monkeypatch.setattr(evolving_strategy_module, "T", lambda text="": FakeT(text))
    monkeypatch.setattr(evolving_strategy_module, "FACTOR_COSTEER_SETTINGS", FakeFACTORSettings())
    return inst


def test_implement_one_task_returns_code_from_json(monkeypatch):
    inst = make_strategy_instance(monkeypatch)

    info = "task-1"
    target_task = FakeFactorTask(info)
    queried = FakeQueried(info_key=info, similar_success=["succ_imp"], former_failed=(["failed_trace"], "latest_exec"))

    monkeypatch.setattr(evolving_strategy_module, "FACTOR_COSTEER_SETTINGS", FakeFACTORSettings(v2_error_summary=False, coder_use_cache=False))

    def fake_api_init(use_chat_cache=False):
        return FakeAPIBackend(use_chat_cache=use_chat_cache, token_return=5, response_return=json.dumps({"code": "print(1)"}))
    monkeypatch.setattr(evolving_strategy_module, "APIBackend", fake_api_init)

    code = inst.implement_one_task(target_task=target_task, queried_knowledge=queried, workspace=None, prev_task_feedback=None)

    assert code == "print(1)"


def test_implement_one_task_parses_python_code_block_when_json_invalid_and_calls_error_summary(monkeypatch):
    inst = make_strategy_instance(monkeypatch)

    info = "task-2"
    target_task = FakeFactorTask(info)
    queried_v2 = FakeQueriedV2(
        info_key=info,
        similar_success=["succ"],
        former_failed=(["failed1", "failed2"], "latest_exec"),
        similar_error={info: {"err": [["imp", "succ"]]}}
    )

    monkeypatch.setattr(evolving_strategy_module, "CoSTEERQueriedKnowledgeV2", FakeQueriedV2)
    monkeypatch.setattr(evolving_strategy_module, "FACTOR_COSTEER_SETTINGS", FakeFACTORSettings(v2_error_summary=True, coder_use_cache=False))

    called = {"flag": False}

    def fake_error_summary(target_task_param, queried_former_failed_knowledge_to_render, queried_similar_error_knowledge_to_render):
        assert queried_former_failed_knowledge_to_render == ["failed1", "failed2"]
        assert queried_similar_error_knowledge_to_render == {info: {"err": [["imp", "succ"]]}}
        called["flag"] = True
        return "ERROR_CRITICS"
    inst.error_summary = fake_error_summary

    def fake_api_init(use_chat_cache=False):
        # build the response string without embedding a raw multi-line literal directly to avoid tooling issues
        code_block = ("some text\n" + ("`" * 3) + "python\n" + "x = 2\n" + ("`" * 3))
        return FakeAPIBackend(use_chat_cache=use_chat_cache, token_return=5, response_return=code_block)
    monkeypatch.setattr(evolving_strategy_module, "APIBackend", fake_api_init)

    code = inst.implement_one_task(target_task=target_task, queried_knowledge=queried_v2, workspace=None, prev_task_feedback=None)

    assert called["flag"] is True
    assert code.strip() == "x = 2"


def test_implement_one_task_returns_empty_after_retries_on_bad_responses(monkeypatch):
    inst = make_strategy_instance(monkeypatch)

    info = "task-3"
    target_task = FakeFactorTask(info)
    queried = FakeQueried(info_key=info, similar_success=["succ"], former_failed=(["f1", "f2"], "latest"))

    monkeypatch.setattr(evolving_strategy_module, "FACTOR_COSTEER_SETTINGS", FakeFACTORSettings(v2_error_summary=False, coder_use_cache=False))

    def fake_api_init(use_chat_cache=False):
        return FakeAPIBackend(use_chat_cache=use_chat_cache, token_return=5, response_return="not json and no code block")
    monkeypatch.setattr(evolving_strategy_module, "APIBackend", fake_api_init)

    code = inst.implement_one_task(target_task=target_task, queried_knowledge=queried, workspace=None, prev_task_feedback=None)

    assert code == ""
