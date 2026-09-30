import types
from types import SimpleNamespace
from gpt_researcher.actions import retriever as retr_mod


class DummyA:
    pass


class DummyB:
    pass


class DummyY:
    pass


class DummyL:
    pass


class DummyM:
    pass


class DummySingle:
    pass


class DefaultCls:
    __name__ = "DefaultClsName"


def test_headers_multiple_round_115(monkeypatch):
    headers = {"retrievers": "A,B"}
    cfg = SimpleNamespace()

    def fake_get_retriever(name):
        return {"A": DummyA, "B": DummyB}.get(name)

    monkeypatch.setattr(retr_mod, "get_retriever", fake_get_retriever)
    monkeypatch.setattr(retr_mod, "get_default_retriever", lambda: DefaultCls)

    result = retr_mod.get_retrievers(headers, cfg)

    # Expect the two mapped classes in order
    assert result == [DummyA, DummyB]


def test_headers_single_round_115(monkeypatch):
    headers = {"retriever": "Solo"}
    cfg = SimpleNamespace()

    def fake_get_retriever(name):
        return {"Solo": DummyA}.get(name)

    monkeypatch.setattr(retr_mod, "get_retriever", fake_get_retriever)
    monkeypatch.setattr(retr_mod, "get_default_retriever", lambda: DefaultCls)

    result = retr_mod.get_retrievers(headers, cfg)

    assert result == [DummyA]


def test_cfg_retrievers_string_with_whitespace_and_fallback_round_115(monkeypatch):
    # cfg.retrievers is a comma-separated string with whitespace
    headers = {}
    cfg = SimpleNamespace(retrievers="X, Y", retriever=None)

    def fake_get_retriever(name):
        # Return None for X to force fallback, return a class for Y
        return {"X": None, "Y": DummyY}.get(name)

    monkeypatch.setattr(retr_mod, "get_retriever", fake_get_retriever)
    monkeypatch.setattr(retr_mod, "get_default_retriever", lambda: DefaultCls)

    result = retr_mod.get_retrievers(headers, cfg)

    # After splitting and stripping we expect order: X then Y -> fallback then DummyY
    assert result[0] is DefaultCls
    assert result[1] is DummyY
    assert len(result) == 2


def test_cfg_retrievers_list_stripping_round_115(monkeypatch):
    # cfg.retrievers is a list and items should be stripped of whitespace
    headers = {}
    cfg = SimpleNamespace(retrievers=["  L  ", " M"], retriever=None)

    def fake_get_retriever(name):
        # Map stripped names
        return {"L": DummyL, "M": None}.get(name)

    monkeypatch.setattr(retr_mod, "get_retriever", fake_get_retriever)
    monkeypatch.setattr(retr_mod, "get_default_retriever", lambda: DefaultCls)

    result = retr_mod.get_retrievers(headers, cfg)

    # Expect DummyL for first, fallback Default for second
    assert result[0] is DummyL
    assert result[1] is DefaultCls


def test_cfg_retriever_single_round_115(monkeypatch):
    # Single retriever set on cfg.retriever
    headers = {}
    cfg = SimpleNamespace(retrievers=None, retriever="SingleCfg")

    def fake_get_retriever(name):
        return {"SingleCfg": DummySingle}.get(name)

    monkeypatch.setattr(retr_mod, "get_retriever", fake_get_retriever)
    monkeypatch.setattr(retr_mod, "get_default_retriever", lambda: DefaultCls)

    result = retr_mod.get_retrievers(headers, cfg)

    assert result == [DummySingle]


def test_default_path_uses_get_default_retriever_name_and_fallback_round_115(monkeypatch):
    # No headers and no cfg settings should result in using the default retriever name
    headers = {}
    cfg = SimpleNamespace(retrievers=None, retriever=None)

    # get_default_retriever() returns DefaultCls which has __name__ = 'DefaultClsName'
    # get_retriever when called with that name returns None to force fallback
    def fake_get_retriever(name):
        assert name == DefaultCls.__name__
        return None

    monkeypatch.setattr(retr_mod, "get_retriever", fake_get_retriever)
    monkeypatch.setattr(retr_mod, "get_default_retriever", lambda: DefaultCls)

    result = retr_mod.get_retrievers(headers, cfg)

    # Fallback should return the default class object
    assert result == [DefaultCls]
