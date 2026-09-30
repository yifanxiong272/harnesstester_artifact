import sys
import types
import pytest
from aider.models import ModelInfoManager

class _FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


def _make_fake_requests(get_func):
    m = types.SimpleNamespace()
    m.get = get_func
    return m


def test_non_200_returns_empty_round_030(monkeypatch):
    """If requests.get returns a non-200 status we should get an empty dict."""
    def fake_get(url, timeout, verify):
        return _FakeResponse(status_code=404, text="not found")

    monkeypatch.setitem(sys.modules, "requests", _make_fake_requests(fake_get))
    mgr = ModelInfoManager()
    res = mgr.fetch_openrouter_model_info("openrouter/some/model")
    assert res == {}


def test_model_unavailable_prints_and_returns_empty_round_030(monkeypatch, capsys):
    """If the page indicates the model is not available, it prints an error and returns {}."""
    url_part = "missing-model"
    html = f"<html>The model   {url_part} is not available</html>"

    def fake_get(url, timeout, verify):
        return _FakeResponse(status_code=200, text=html)

    monkeypatch.setitem(sys.modules, "requests", _make_fake_requests(fake_get))
    mgr = ModelInfoManager()
    res = mgr.fetch_openrouter_model_info(f"openrouter/{url_part}")
    captured = capsys.readouterr()
    # printed error message mentioning the short url_part
    assert "Error: Model" in captured.out
    assert url_part in captured.out
    assert res == {}


def test_missing_context_or_cost_returns_empty_round_030(monkeypatch):
    """If context or cost tokens cannot be found, the function returns {}."""
    html = "<html><body>No relevant info here</body></html>"

    def fake_get(url, timeout, verify):
        return _FakeResponse(status_code=200, text=html)

    monkeypatch.setitem(sys.modules, "requests", _make_fake_requests(fake_get))
    mgr = ModelInfoManager()
    res = mgr.fetch_openrouter_model_info("openrouter/whatever")
    assert res == {}


def test_valid_html_parsed_returns_params_round_030(monkeypatch):
    """Provides HTML with context and both input/output prices and expects parsed params."""
    # include some HTML tags to exercise the re.sub path
    html = (
        "<div>Some header</div>"
        "<p>100,000 context</p>"
        "<span>$0.12 /M input tokens</span>"
        "<span>$0.34 /M output tokens</span>"
    )

    def fake_get(url, timeout, verify):
        return _FakeResponse(status_code=200, text=html)

    monkeypatch.setitem(sys.modules, "requests", _make_fake_requests(fake_get))
    mgr = ModelInfoManager()
    res = mgr.fetch_openrouter_model_info("openrouter/anything/here")
    # Expect parsed numeric values
    assert isinstance(res, dict)
    assert res["max_input_tokens"] == 100000
    assert res["max_tokens"] == 100000
    assert res["max_output_tokens"] == 100000
    # costs were given as dollars per million, so per-token cost is dollars/1_000_000
    assert res["input_cost_per_token"] == 0.12 / 1_000_000
    assert res["output_cost_per_token"] == 0.34 / 1_000_000


def test_requests_get_raises_returns_empty_round_030(monkeypatch, capsys):
    """If requests.get raises, the function catches and returns {} (printing an error)."""
    def fake_get(url, timeout, verify):
        raise RuntimeError("boom")

    monkeypatch.setitem(sys.modules, "requests", _make_fake_requests(fake_get))
    mgr = ModelInfoManager()
    res = mgr.fetch_openrouter_model_info("openrouter/x")
    out = capsys.readouterr().out
    assert res == {}
    assert "Error fetching openrouter info:" in out
    assert "boom" in out
