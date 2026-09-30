# file: aider/exceptions.py:80-108
# asked: {"lines": [86, 99, 100, 101, 102, 103, 104], "branches": [[85, 86], [87, 98], [98, 99], [100, 101], [100, 108]]}
# gained: {"lines": [86, 99, 100, 101, 102, 103, 104], "branches": [[85, 86], [87, 98], [98, 99], [100, 101]]}

import sys
import types

import pytest

from aider.exceptions import LiteLLMExceptions, ExInfo


def make_litellm_module():
    mod = types.ModuleType("litellm")

    class APIConnectionError(Exception):
        def __init__(self, msg=""):
            super().__init__(msg)

    class APIError(Exception):
        def __init__(self, msg=""):
            super().__init__(msg)

    mod.APIConnectionError = APIConnectionError
    mod.APIError = APIError
    return mod


def _make_lle_without_init():
    # Create an instance without calling __init__ to avoid _load() which requires a full litellm module
    lle = LiteLLMExceptions.__new__(LiteLLMExceptions)
    return lle


def test_api_connection_error_boto3(monkeypatch):
    # Arrange: inject a fake litellm module with the required exception classes
    litellm_mod = make_litellm_module()
    monkeypatch.setitem(sys.modules, "litellm", litellm_mod)

    ex_inst = litellm_mod.APIConnectionError("something about boto3 is missing")

    lle = _make_lle_without_init()
    result = lle.get_ex_info(ex_inst)

    # Assert expected ExInfo for boto3-related APIConnectionError
    assert isinstance(result, ExInfo)
    assert result.name == "APIConnectionError"
    assert result.retry is False
    assert result.description == "You need to: pip install boto3"


def test_api_connection_error_openrouter_with_choices(monkeypatch):
    # Arrange: inject fake litellm and create an APIConnectionError whose str contains both
    # "OpenrouterException" and "'choices'"
    litellm_mod = make_litellm_module()
    monkeypatch.setitem(sys.modules, "litellm", litellm_mod)

    msg = "OpenrouterException occurred with response containing 'choices' in payload"
    ex_inst = litellm_mod.APIConnectionError(msg)

    lle = _make_lle_without_init()
    result = lle.get_ex_info(ex_inst)

    # Assert the OpenRouter-specific ExInfo is returned
    assert isinstance(result, ExInfo)
    assert result.name == "APIConnectionError"
    assert result.retry is True
    assert (
        result.description
        == "OpenRouter or the upstream API provider is down, overloaded or rate limiting your requests."
    )


def test_api_connection_error_no_inner_matches_returns_default(monkeypatch):
    # Arrange: inject fake litellm module; create APIConnectionError that doesn't match boto3 or Openrouter
    litellm_mod = make_litellm_module()
    monkeypatch.setitem(sys.modules, "litellm", litellm_mod)

    ex_inst = litellm_mod.APIConnectionError("an unrelated connection error message")

    lle = _make_lle_without_init()
    result = lle.get_ex_info(ex_inst)

    # Since there is no mapping for this exception class in lle.exceptions, expect the default ExInfo(None,...)
    assert isinstance(result, ExInfo)
    assert result.name is None and result.retry is None and result.description is None


def test_api_error_insufficient_credits(monkeypatch):
    # Arrange: inject fake litellm module and create APIError with a message that triggers the credits branch
    litellm_mod = make_litellm_module()
    monkeypatch.setitem(sys.modules, "litellm", litellm_mod)

    msg = 'Insufficient credits detected in response body: {"error":"something","code":402}'
    ex_inst = litellm_mod.APIError(msg)

    lle = _make_lle_without_init()
    result = lle.get_ex_info(ex_inst)

    # Assert the specific APIError ExInfo is returned
    assert isinstance(result, ExInfo)
    assert result.name == "APIError"
    assert result.retry is False
    assert result.description == "Insufficient credits with the API provider. Please add credits."
