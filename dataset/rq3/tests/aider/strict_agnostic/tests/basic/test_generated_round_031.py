import pytest
from aider.models import ModelInfoManager
import requests

class _FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


def test_status_not_200_round_031(monkeypatch):
    mgr = ModelInfoManager()

    def fake_get(url, timeout=5, verify=True):
        return _FakeResponse(status_code=404, text="Not Found")

    monkeypatch.setattr(requests, "get", fake_get)

    result = mgr.fetch_openrouter_model_info("openrouter/foo/bar")
    assert result == {}, "Expected empty dict when status != 200"


def test_model_not_available_message_round_031(monkeypatch):
    mgr = ModelInfoManager()
    url_part = "qwen/qwen-2.5-72b-instruct:free"
    html = f"<html>The model {url_part} is not available</html>"

    def fake_get(url, timeout=5, verify=True):
        return _FakeResponse(status_code=200, text=html)

    monkeypatch.setattr(requests, "get", fake_get)

    result = mgr.fetch_openrouter_model_info("openrouter/" + url_part)
    assert result == {}, "Expected empty dict when page says model is not available"


def test_missing_context_or_costs_round_031(monkeypatch):
    mgr = ModelInfoManager()

    # HTML without context or cost patterns -> should return {}
    html = "<html><body>No useful info here</body></html>"

    def fake_get(url, timeout=5, verify=True):
        return _FakeResponse(status_code=200, text=html)

    monkeypatch.setattr(requests, "get", fake_get)

    result = mgr.fetch_openrouter_model_info("openrouter/any/model")
    assert result == {}, "Expected empty dict when no context or cost info present"


def test_context_present_but_no_costs_round_031(monkeypatch):
    mgr = ModelInfoManager()

    # Provide a context size but omit cost patterns -> should return {}
    html = "<div>32,768 context</div>"

    def fake_get(url, timeout=5, verify=True):
        return _FakeResponse(status_code=200, text=html)

    monkeypatch.setattr(requests, "get", fake_get)

    result = mgr.fetch_openrouter_model_info("openrouter/some/model")
    assert result == {}, "Expected empty dict when costs are missing even if context is present"


def test_all_present_returns_params_round_031(monkeypatch):
    mgr = ModelInfoManager()

    # Provide context and both cost lines. Include some HTML tags to ensure the tag-stripping
    html = (
        "<html><body>Some intro<br>32,768 context</br>"
        "<p>$ 0.50 /M input tokens</p>"
        "<p>$1.00 /M output tokens</p></body></html>"
    )

    def fake_get(url, timeout=5, verify=True):
        return _FakeResponse(status_code=200, text=html)

    monkeypatch.setattr(requests, "get", fake_get)

    result = mgr.fetch_openrouter_model_info("openrouter/any/model")
    # Expect parsed values
    assert isinstance(result, dict)
    assert result.get("max_input_tokens") == 32768
    assert result.get("max_tokens") == 32768
    assert result.get("max_output_tokens") == 32768
    # Costs are parsed and divided by 1e6
    assert abs(result.get("input_cost_per_token") - (0.50 / 1000000)) < 1e-15
    assert abs(result.get("output_cost_per_token") - (1.00 / 1000000)) < 1e-15


def test_requests_exception_round_031(monkeypatch):
    mgr = ModelInfoManager()

    def fake_get_raise(url, timeout=5, verify=True):
        raise RuntimeError("network failure simulated")

    monkeypatch.setattr(requests, "get", fake_get_raise)

    result = mgr.fetch_openrouter_model_info("openrouter/any/model")
    assert result == {}, "Expected empty dict when requests.get raises an exception"
