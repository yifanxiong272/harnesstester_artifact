# file: rdagent/scenarios/qlib/factor_experiment_loader/pdf_loader.py:29-112
# asked: {"lines": [59, 60, 62, 63, 64, 65, 67, 68, 70, 71, 72, 81, 82, 83, 85, 87, 89, 90, 91, 92, 93, 94, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 109, 110, 112], "branches": [[62, 63], [62, 112], [63, 64], [63, 65], [67, 68], [67, 70], [80, 87], [80, 89], [90, 91], [90, 109], [106, 90], [106, 107]]}
# gained: {"lines": [59, 60, 62, 63, 64, 65, 67, 68, 70, 71, 72, 81, 82, 83, 85, 87, 89, 90, 91, 92, 93, 94, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 109, 110, 112], "branches": [[62, 63], [62, 112], [63, 64], [63, 65], [67, 68], [67, 70], [80, 87], [80, 89], [90, 91], [90, 109], [106, 90], [106, 107]]}

import importlib
import json
import pytest


@pytest.fixture(autouse=True)
def ensure_module_loaded():
    # Ensure module import fresh for tests
    mod = importlib.import_module("rdagent.scenarios.qlib.factor_experiment_loader.pdf_loader")
    importlib.reload(mod)
    return mod


def test_classify_reports_handles_non_pdf_and_non_str_and_majority_vote(monkeypatch, ensure_module_loaded):
    pdf_loader = ensure_module_loaded

    # Dummy T that returns a simple system prompt string
    class DummyT:
        def __init__(self, *_a, **_kw):
            pass

        def r(self):
            return "system prompt"

    monkeypatch.setattr(pdf_loader, "T", DummyT, raising=True)

    warnings = []

    def fake_warning(msg):
        warnings.append(msg)

    monkeypatch.setattr(pdf_loader, "logger", type("L", (), {"warning": staticmethod(fake_warning)}), raising=True)

    # Dummy APIBackend that will:
    # - For the first seen long content, report token count > limit so the while loop will trigger trimming once.
    # - For subsequent content (after trimming), report small token count so loop exits.
    # - Provide a sequence of JSON responses for chat completion
    class DummyAPI:
        chat_token_limit = 100  # ensure //100 == 1 so trimming removes at least 1 char

        # Shared across instances to emulate multiple calls returning queued responses
        responses = []

        seen_original = None

        def build_messages_and_calculate_token(self, user_prompt, system_prompt):
            # On the very first call with the original content, return a large number to force trimming.
            if DummyAPI.seen_original is None:
                DummyAPI.seen_original = user_prompt
            # If it's exactly the original (untrimmed) content, return a big value to trigger trimming.
            if user_prompt == DummyAPI.seen_original:
                return DummyAPI.chat_token_limit + 1000
            # Otherwise, return a small number within limits.
            return DummyAPI.chat_token_limit - 10

        def build_messages_and_create_chat_completion(self, user_prompt, system_prompt, json_mode=True):
            if not DummyAPI.responses:
                # Default fallback
                return json.dumps({"class": "0"})
            return DummyAPI.responses.pop(0)

    monkeypatch.setattr(pdf_loader, "APIBackend", DummyAPI, raising=True)

    # Prepare responses: majority should be "1"
    DummyAPI.responses = ['{"class":"1"}', '{"class":"1"}', '{"class":"0"}']

    report_dict = {
        "ignore_me.txt": "this should be skipped",
        "bad.pdf": None,  # non-str value => triggers input-format warning and class 0
        "long.pdf": "A" * 300,  # long content triggers trimming loop
    }

    res = pdf_loader.classify_report_from_dict(report_dict, vote_time=3)

    # skip .txt should not be present
    assert "ignore_me.txt" not in res

    # bad.pdf should be set to class 0 due to non-str input
    assert "bad.pdf" in res and res["bad.pdf"]["class"] == 0

    # long.pdf should reach majority class 1
    assert "long.pdf" in res and res["long.pdf"]["class"] == 1

    # Check that warnings were emitted for the non-str input
    assert any("Input format does not meet the requirements" in w and "bad.pdf" in w for w in warnings)


def test_classify_reports_handles_invalid_json(monkeypatch, ensure_module_loaded):
    pdf_loader = ensure_module_loaded

    class DummyT:
        def __init__(self, *_a, **_kw):
            pass

        def r(self):
            return "system prompt"

    monkeypatch.setattr(pdf_loader, "T", DummyT, raising=True)

    warnings = []

    def fake_warning(msg):
        warnings.append(msg)

    monkeypatch.setattr(pdf_loader, "logger", type("L", (), {"warning": staticmethod(fake_warning)}), raising=True)

    class DummyAPI2:
        chat_token_limit = 100

        def build_messages_and_calculate_token(self, user_prompt, system_prompt):
            # small token usage so trimming is skipped
            return 10

        def build_messages_and_create_chat_completion(self, user_prompt, system_prompt, json_mode=True):
            # return an invalid JSON string to trigger JSONDecodeError
            return "this is not json"

    monkeypatch.setattr(pdf_loader, "APIBackend", DummyAPI2, raising=True)

    report_dict = {"badjson.pdf": "short content"}

    res = pdf_loader.classify_report_from_dict(report_dict, vote_time=1)

    # Should parse into class 0 due to JSON decode failure
    assert "badjson.pdf" in res and res["badjson.pdf"]["class"] == 0

    # Warning about parse failure should be emitted
    assert any("Return value could not be parsed" in w and "badjson.pdf" in w for w in warnings)
