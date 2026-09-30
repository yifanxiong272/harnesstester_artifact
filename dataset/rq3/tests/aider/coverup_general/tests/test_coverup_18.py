# file: aider/models.py:264-311
# asked: {"lines": [272, 273, 274, 275, 277, 278, 279, 280, 281, 283, 284, 286, 287, 288, 289, 290, 291, 292, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 308, 309, 310, 311], "branches": [[278, 279], [278, 280], [283, 286], [283, 288], [290, 291], [290, 294], [299, 300], [299, 301]]}
# gained: {"lines": [272, 273, 274, 275, 277, 278, 279, 280, 281, 283, 284, 286, 287, 288, 289, 290, 291, 292, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 308, 309, 310, 311], "branches": [[278, 279], [278, 280], [283, 286], [283, 288], [290, 291], [290, 294], [299, 300], [299, 301]]}

import re
import requests
import pytest

from aider.models import ModelInfoManager


class DummyResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


def test_fetch_openrouter_status_not_200(monkeypatch):
    mgr = ModelInfoManager()
    model = "openrouter/some/path"

    def fake_get(url, timeout=5, verify=True):
        # Simulate non-200 status
        return DummyResponse(status_code=404, text="Not Found")

    monkeypatch.setattr(requests, "get", fake_get)
    result = mgr.fetch_openrouter_model_info(model)
    assert result == {}, "Expected empty dict when HTTP status is not 200"


def test_fetch_openrouter_model_not_available(monkeypatch, capsys):
    mgr = ModelInfoManager()
    url_part = "vendor/model-name:tag"
    model = "openrouter/" + url_part

    # Build html that matches the "is not available" regex
    html = f"<html><body>The model {url_part} is not available on this page</body></html>"

    def fake_get(url, timeout=5, verify=True):
        assert url.endswith(url_part)
        return DummyResponse(status_code=200, text=html)

    monkeypatch.setattr(requests, "get", fake_get)
    result = mgr.fetch_openrouter_model_info(model)
    captured = capsys.readouterr()
    # The function prints an error message with ANSI color; ensure something was printed
    assert "not available" in captured.out.lower()
    assert result == {}, "Expected empty dict when model is reported as not available"


def test_fetch_openrouter_missing_values(monkeypatch):
    mgr = ModelInfoManager()
    url_part = "vendor/partial-model"
    model = "openrouter/" + url_part

    # HTML has neither context nor cost lines
    html = "<html><body>No useful pricing or context info here</body></html>"

    def fake_get(url, timeout=5, verify=True):
        return DummyResponse(status_code=200, text=html)

    monkeypatch.setattr(requests, "get", fake_get)
    result = mgr.fetch_openrouter_model_info(model)
    assert result == {}, "Expected empty dict when required fields are missing"


def test_fetch_openrouter_success(monkeypatch):
    mgr = ModelInfoManager()
    url_part = "openvendor/my-model"
    model = "openrouter/" + url_part

    # Provide HTML with context and both input/output costs.
    # Use a comma in the context to exercise the replace(",","") logic.
    html = """
    <html>
      <body>
        <div>8,192 context</div>
        <div>$0.10 /M input tokens</div>
        <div>$0.20 /M output tokens</div>
      </body>
    </html>
    """

    def fake_get(url, timeout=5, verify=True):
        assert url.endswith(url_part)
        return DummyResponse(status_code=200, text=html)

    monkeypatch.setattr(requests, "get", fake_get)
    result = mgr.fetch_openrouter_model_info(model)
    # Verify the parsed values
    assert isinstance(result, dict), "Expected a dict on success"
    assert result["max_input_tokens"] == 8192
    assert result["max_tokens"] == 8192
    assert result["max_output_tokens"] == 8192
    # Costs are converted dividing by 1_000_000
    assert pytest.approx(result["input_cost_per_token"], rel=1e-9) == 0.10 / 1_000_000
    assert pytest.approx(result["output_cost_per_token"], rel=1e-9) == 0.20 / 1_000_000


def test_fetch_openrouter_exception(monkeypatch, capsys):
    mgr = ModelInfoManager()
    model = "openrouter/whatever"

    def fake_get(url, timeout=5, verify=True):
        raise RuntimeError("boom")

    monkeypatch.setattr(requests, "get", fake_get)
    result = mgr.fetch_openrouter_model_info(model)
    captured = capsys.readouterr()
    # The function prints an error message in the exception handler
    assert "Error fetching openrouter info" in captured.out or "Error fetching openrouter info" in captured.err
    assert result == {}, "Expected empty dict when an exception is raised during requests.get"
