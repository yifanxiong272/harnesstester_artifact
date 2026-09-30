import pytest
from pydantic import BaseModel
from browser_use.agent.service import Agent


class DummyModel(BaseModel):
    value: str = "x"


def test_tuple_processing_round_093(monkeypatch):
    # record calls
    calls = {"pydantic": 0, "dict": 0}

    def fake_replace_shortened_urls_in_string(text, url_replacements):
        # deterministic replacement behavior
        return f"REPLACED:{text}"

    def fake_recursive_all_strings_inside_pydantic_model(model, url_replacements):
        # mark that the model was processed (side-effect observable)
        calls["pydantic"] += 1
        setattr(model, "__processed__", True)

    def fake_recursive_process_dict(d, url_replacements):
        # mark dict as processed (side-effect observable)
        calls["dict"] += 1
        d["__processed__"] = True

    monkeypatch.setattr(Agent, "_replace_shortened_urls_in_string", fake_replace_shortened_urls_in_string)
    monkeypatch.setattr(Agent, "_recursive_process_all_strings_inside_pydantic_model", fake_recursive_all_strings_inside_pydantic_model)
    monkeypatch.setattr(Agent, "_recursive_process_dict", fake_recursive_process_dict)

    # prepare inputs covering tuple branches: str, BaseModel, dict, nested list, other
    nested_list = ["inner"]
    model_instance = DummyModel()
    original = ("short", model_instance, {"k": "v"}, nested_list, 42)
    url_replacements = {"short": "s"}

    result = Agent._recursive_process_list_or_tuple(original, url_replacements)

    # tuple result expected
    assert isinstance(result, tuple)

    # string in tuple was processed through fake_replace_shortened_urls_in_string
    assert result[0] == "REPLACED:short"

    # BaseModel instance should be the same object and have been processed (side-effect)
    assert result[1] is model_instance
    assert getattr(result[1], "__processed__", False) is True
    assert calls["pydantic"] == 1

    # dict should have been processed in place by fake_recursive_process_dict
    assert isinstance(result[2], dict)
    assert result[2].get("__processed__") is True
    assert calls["dict"] == 1

    # nested list returned as processed element and its string replaced
    assert isinstance(result[3], list)
    assert result[3][0] == "REPLACED:inner"

    # other element unchanged
    assert result[4] == 42


def test_list_processing_round_093(monkeypatch):
    # record calls
    calls = {"pydantic": 0, "dict": 0}

    def fake_replace_shortened_urls_in_string(text, url_replacements):
        return f"REPLACED:{text}"

    def fake_recursive_all_strings_inside_pydantic_model(model, url_replacements):
        calls["pydantic"] += 1
        setattr(model, "__processed__", True)

    def fake_recursive_process_dict(d, url_replacements):
        calls["dict"] += 1
        d["__processed__"] = True

    monkeypatch.setattr(Agent, "_replace_shortened_urls_in_string", fake_replace_shortened_urls_in_string)
    monkeypatch.setattr(Agent, "_recursive_process_all_strings_inside_pydantic_model", fake_recursive_all_strings_inside_pydantic_model)
    monkeypatch.setattr(Agent, "_recursive_process_dict", fake_recursive_process_dict)

    # prepare inputs covering list branches: str, BaseModel, dict, nested tuple, nested list
    nested_tuple = ("t",)
    nested_list = ["nested_t"]
    model_instance = DummyModel()
    container = ["a", model_instance, {"x": "y"}, nested_tuple, nested_list]
    url_replacements = {"a": "A"}

    returned = Agent._recursive_process_list_or_tuple(container, url_replacements)

    # list path modifies in-place and returns the same container object
    assert returned is container

    # first element replaced in-place
    assert container[0] == "REPLACED:a"

    # BaseModel instance processed (side-effect)
    assert container[1] is model_instance
    assert getattr(container[1], "__processed__", False) is True
    assert calls["pydantic"] == 1

    # dict processed in-place
    assert container[2].get("__processed__") is True
    assert calls["dict"] == 1

    # nested tuple should be replaced with processed tuple where its string is replaced
    assert isinstance(container[3], tuple)
    assert container[3][0] == "REPLACED:t"

    # nested list should have been processed and its element replaced
    assert isinstance(container[4], list)
    assert container[4][0] == "REPLACED:nested_t"
