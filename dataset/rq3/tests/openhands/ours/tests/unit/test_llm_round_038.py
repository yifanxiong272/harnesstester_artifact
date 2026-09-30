import copy
from types import SimpleNamespace
import pytest

import openhands.llm.llm as llm_mod
from openhands.llm.llm import LLM, LLMNoResponseError


class DummySecret:
    def __init__(self, v):
        self._v = v

    def get_secret_value(self):
        return self._v


class DummyMetrics:
    def __init__(self):
        self.recorded = []

    def add_response_latency(self, latency, response_id):
        # record call for test introspection
        self.recorded.append((latency, response_id))


def make_base_config(**overrides):
    # Minimal config object with attributes accessed by LLM.__init__.
    base = SimpleNamespace(
        log_completions=False,
        log_completions_folder=None,
        model="test-model",
        temperature=1.0,
        max_output_tokens=16,
        top_k=None,
        top_p=None,
        reasoning_effort=None,
        safety_settings=None,
        aws_region_name=None,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        api_key=None,
        base_url=None,
        api_version=None,
        custom_llm_provider=None,
        timeout=None,
        drop_params=None,
        seed=None,
        num_retries=0,
        retry_min_wait=0,
        retry_max_wait=0,
        retry_multiplier=1,
        modify_params=True,
        disable_stop_word=False,
        completion_kwargs=None,
        custom_tokenizer=None,
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


# Patch module-level dependencies to deterministic test doubles
llm_mod.get_features = lambda model: SimpleNamespace(
    supports_reasoning_effort=False, supports_stop_words=False
)

# Avoid any heavy init logic by making init_model_info a no-op (but ensure max_output_tokens exists)
setattr(LLM, "init_model_info", lambda self: None)


def test_log_completions_missing_folder_round_038():
    """When log_completions is enabled but no folder is provided, __init__ raises RuntimeError."""
    cfg = make_base_config(log_completions=True, log_completions_folder=None, model="abc")
    # Provide a dummy metrics to avoid constructing the real one
    metrics = DummyMetrics()

    with pytest.raises(RuntimeError) as exc:
        LLM(cfg, service_id="svc", metrics=metrics)
    assert "log_completions_folder is required" in str(exc.value)


def test_partial_includes_safety_and_aws_round_038():
    """Confirm that partial kwargs include safety settings and AWS credentials when provided."""
    # Create config with mistral and safety + aws secrets
    cfg = make_base_config(
        model="mistral-xl",
        safety_settings={"s": "ok"},
        aws_region_name="eu-west-1",
        aws_access_key_id=DummySecret("AKIA-TEST"),
        aws_secret_access_key=DummySecret("SECRET-TEST"),
        api_key=DummySecret("APIKEY-VAL"),
    )
    metrics = DummyMetrics()

    ll = LLM(cfg, service_id="svc", metrics=metrics)

    # The underlying unwrapped partial stores its keyword arguments in .keywords
    unwrapped = ll._completion_unwrapped
    # partial stores keywords in .keywords attribute
    kw = getattr(unwrapped, "keywords", {})

    # safety settings should be present for 'mistral'
    assert kw.get("safety_settings") == cfg.safety_settings

    # AWS keys are unwrapped via get_secret_value
    assert kw.get("aws_region_name") == "eu-west-1"
    assert kw.get("aws_access_key_id") == "AKIA-TEST"
    assert kw.get("aws_secret_access_key") == "SECRET-TEST"


def test_wrapper_raises_value_error_for_empty_messages_round_038():
    """Calling the wrapper with an empty messages list raises ValueError before calling the LLM backend."""
    cfg = make_base_config(model="some-model", api_key=None)
    metrics = DummyMetrics()
    ll = LLM(cfg, service_id="svc", metrics=metrics)

    # Ensure the wrapped completion won't actually be invoked (it shouldn't be for this test)
    ll._completion_unwrapped = lambda *a, **k: {"choices": [{"message": {}}], "id": "x"}

    with pytest.raises(ValueError) as exc:
        ll._completion(messages=[])
    assert "The messages list is empty" in str(exc.value)


def test_wrapper_raises_llm_no_response_when_no_choices_round_038():
    """If the backend returns no 'choices', wrapper raises LLMNoResponseError after calling the backend."""
    cfg = make_base_config(model="some-model", api_key=None)
    metrics = DummyMetrics()
    ll = LLM(cfg, service_id="svc", metrics=metrics)

    # Replace logging and post-processing to avoid side effects
    ll.log_prompt = lambda messages: None
    ll.log_response = lambda resp: None
    ll._post_completion = lambda resp: 0.0

    # Provide a deterministic backend returning a dict with no 'choices' key
    def fake_completion(*args, **kwargs):
        return {"id": "r1"}

    ll._completion_unwrapped = fake_completion

    with pytest.raises(LLMNoResponseError) as exc:
        ll._completion(messages=[{"role": "user", "content": "hello"}])
    assert "Response choices is less than 1" in str(exc.value)
