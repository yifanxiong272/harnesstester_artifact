import importlib
import json
import types

import pytest


MODULE_PATH = "rdagent.scenarios.qlib.factor_experiment_loader.pdf_loader"


class DummyTObj:
    def __init__(self, value):
        self.value = value

    def r(self):
        # return a deterministic system prompt
        return f"system:{self.value}"


class FakeAPIBackend:
    # shared across instances to simulate repeated calls from new instances
    chat_token_limit = 1000
    token_calls = 0

    def __init__(self):
        # nothing instance-specific required
        pass

    def build_messages_and_calculate_token(self, user_prompt=None, system_prompt=None):
        # First call (token_calls == 0) will report > chat_token_limit to trigger truncation
        # subsequent calls report <= chat_token_limit
        FakeAPIBackend.token_calls += 1
        if FakeAPIBackend.token_calls == 1:
            return FakeAPIBackend.chat_token_limit * 2
        return FakeAPIBackend.chat_token_limit // 2

    def build_messages_and_create_chat_completion(self, user_prompt=None, system_prompt=None, json_mode=False):
        # Decide response based on user_prompt content to allow deterministic branching
        s = (user_prompt or "")
        if "bad-json" in s:
            return "not-a-json"
        # if contains 'class1' return class 1, if contains 'class0' return class 0
        if "class1" in s or "good" in s:
            return json.dumps({"class": "1"})
        return json.dumps({"class": "0"})


@pytest.fixture(autouse=True)
def patch_module(monkeypatch):
    """Patch the target module to use deterministic, in-process fakes.

    - Replace APIBackend with FakeAPIBackend
    - Replace T with a simple callable returning DummyTObj
    - Replace tqdm with identity to avoid progress-bar side-effects
    - Replace logger.warning to capture warnings when desired
    """
    mod = importlib.import_module(MODULE_PATH)

    # patch APIBackend and T
    monkeypatch.setattr(mod, "APIBackend", FakeAPIBackend)
    monkeypatch.setattr(mod, "T", lambda s: DummyTObj(s))

    # tqdm should return the iterable passed in
    monkeypatch.setattr(mod, "tqdm", lambda it: it)

    # capture warnings via a list attached to module for assertions
    warnings = []

    def fake_warn(msg):
        warnings.append(msg)

    monkeypatch.setattr(mod, "logger", types.SimpleNamespace(warning=fake_warn))
    # expose warnings list for tests
    mod._test_warnings = warnings

    # reset FakeAPIBackend counters for deterministic behaviour
    FakeAPIBackend.token_calls = 0

    yield


def test_classify_non_pdf_and_non_str_round_063():
    """Non-pdf keys should be skipped; pdf entries with non-str values should log a warning
    and be classified as 0.
    """
    mod = importlib.import_module(MODULE_PATH)

    # Prepare input: one non-pdf (skipped), one pdf with wrong type (triggers warning)
    report_dict = {
        "ignored.txt": "some text",
        "wrong.pdf": 12345,  # non-str should trigger the warning and produce class 0
    }

    res = mod.classify_report_from_dict(report_dict, vote_time=1, substrings=())

    # Only the pdf key should be present in results and classified as 0
    assert "wrong.pdf" in res
    assert res["wrong.pdf"]["class"] == 0

    # Ensure the logger.warning was called with the filename
    warnings = getattr(mod, "_test_warnings")
    assert any("wrong.pdf" in str(w) for w in warnings), f"expected warning mentioning 'wrong.pdf', got {warnings}"


def test_classify_votes_and_truncation_round_063():
    """Test behavior when token calculation initially exceeds limit (truncation loop)
    and when chat completions return valid JSON strings leading to a majority vote of 1.

    Also test that an entry that returns invalid JSON results in class 0.
    """
    mod = importlib.import_module(MODULE_PATH)

    # Provide two pdfs: one that will be voted into class 1, another that will return invalid JSON
    long_good_content = ("good " * 300) + " class1"
    long_bad_json = ("bad-json " * 300)

    report_dict = {
        "good_report.pdf": long_good_content,
        "bad_report.pdf": long_bad_json,
    }

    # vote_time=3: requires at least 2 same votes to break early (int(3/2)=1, so >1 -> 2)
    res = mod.classify_report_from_dict(report_dict, vote_time=3, substrings=())

    # good_report.pdf should be classified as 1 because FakeAPIBackend returns class 1 for 'good'
    assert res["good_report.pdf"]["class"] == 1

    # bad_report.pdf should end up as class 0 because the backend returns invalid JSON for 'bad-json'
    assert res["bad_report.pdf"]["class"] == 0

    # Ensure truncation happened at least once by observing FakeAPIBackend.token_calls > 0
    # (The first build_messages_and_calculate_token call is made and increments the counter)
    assert FakeAPIBackend.token_calls >= 1
