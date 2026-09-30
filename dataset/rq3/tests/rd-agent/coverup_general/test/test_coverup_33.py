# file: rdagent/scenarios/qlib/factor_experiment_loader/pdf_loader.py:453-512
# asked: {"lines": [454, 455, 456, 457, 459, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 474, 475, 477, 478, 479, 480, 482, 483, 486, 487, 488, 489, 490, 491, 493, 495, 496, 497, 498, 503, 505, 506, 507, 509, 510, 512], "branches": [[454, 455], [454, 456], [462, 463], [462, 474], [478, 479], [478, 482], [482, 486], [482, 491], [487, 482], [487, 488], [505, 506], [505, 512], [509, 505], [509, 510]]}
# gained: {"lines": [454, 455, 456, 457, 459, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 474, 475, 477, 478, 479, 480, 482, 483, 486, 487, 488, 489, 490, 491, 493, 495, 496, 497, 498, 503, 505, 506, 507, 509, 510, 512], "branches": [[454, 455], [454, 456], [462, 463], [462, 474], [478, 479], [478, 482], [482, 486], [487, 488], [505, 506], [505, 512], [509, 505], [509, 510]]}

import pytest

import rdagent.scenarios.qlib.factor_experiment_loader.pdf_loader as pdf_loader


def _make_factor(name):
    return {
        "description": f"desc_{name}",
        "formulation": f"form_{name}",
        "variables": f"vars_{name}",
    }


def test___deduplicate_factor_dict_empty():
    fn = getattr(pdf_loader, "__deduplicate_factor_dict")
    result = fn({})
    assert result == []


def test___deduplicate_factor_dict_small_group(monkeypatch):
    fn = getattr(pdf_loader, "__deduplicate_factor_dict")

    # Prepare a small factor dict (2 items)
    factor_dict = {"b": _make_factor("b"), "a": _make_factor("a")}

    # Configure RD_AGENT_SETTINGS so that len(full_str_list) < max_input_duplicate_factor_group
    monkeypatch.setattr(pdf_loader.RD_AGENT_SETTINGS, "max_input_duplicate_factor_group", 10)
    monkeypatch.setattr(pdf_loader.RD_AGENT_SETTINGS, "multi_proc_n", 1)
    monkeypatch.setattr(pdf_loader.RD_AGENT_SETTINGS, "max_kmeans_group_number", 10)

    # Provide a Dummy APIBackend with a create_embedding attribute
    called_embeddings = {}

    class DummyBackend:
        @staticmethod
        def create_embedding(full_str_list):
            called_embeddings["called"] = True
            called_embeddings["full_str_list"] = list(full_str_list)
            return [[i] for i, _ in enumerate(full_str_list)]

    monkeypatch.setattr(pdf_loader, "APIBackend", DummyBackend)

    # Stub multiprocessing_wrapper to capture the tasks it was asked to run and return a simulated result list
    captured = {}

    def fake_multiprocessing_wrapper(tasks, n):
        captured["tasks"] = tasks
        captured["n"] = n
        return [["a", "b"]]

    monkeypatch.setattr(pdf_loader, "multiprocessing_wrapper", fake_multiprocessing_wrapper)

    res = fn(factor_dict)

    # Assertions about behavior and return value
    assert called_embeddings.get("called", False) is True
    # The full_str_list should contain formatted strings for the sorted factor names ['a','b']
    assert any("Factor name: a" in s for s in called_embeddings["full_str_list"])
    assert any("Factor name: b" in s for s in called_embeddings["full_str_list"])

    # multiprocessing_wrapper should have been called with a single task (one group containing both factors)
    assert len(captured["tasks"]) == 1
    assert captured["n"] == pdf_loader.RD_AGENT_SETTINGS.multi_proc_n

    # The result should report the duplicated pair
    assert isinstance(res, list)
    assert len(res) == 1
    assert set(res[0]) == {"a", "b"}


def test___deduplicate_factor_dict_kmeans_branch(monkeypatch):
    fn = getattr(pdf_loader, "__deduplicate_factor_dict")

    # Prepare a larger factor dict (4 items)
    factor_dict = {
        "z": _make_factor("z"),
        "c": _make_factor("c"),
        "a": _make_factor("a"),
        "m": _make_factor("m"),
    }

    # Configure RD_AGENT_SETTINGS so that len(full_str_list) >= max_input_duplicate_factor_group and loop runs
    monkeypatch.setattr(pdf_loader.RD_AGENT_SETTINGS, "max_input_duplicate_factor_group", 3)
    monkeypatch.setattr(pdf_loader.RD_AGENT_SETTINGS, "max_kmeans_group_number", 6)
    monkeypatch.setattr(pdf_loader.RD_AGENT_SETTINGS, "multi_proc_n", 2)

    # Provide Dummy APIBackend
    class DummyBackend2:
        @staticmethod
        def create_embedding(full_str_list):
            return [[i, i * 0.1] for i in range(len(full_str_list))]

    monkeypatch.setattr(pdf_loader, "APIBackend", DummyBackend2)

    # Stub __kmeans_embeddings to return a grouping where the first group's length < max_input_duplicate_factor_group
    def fake_kmeans_embeddings(embeddings, k):
        return [[0, 1], [2, 3]]

    monkeypatch.setattr(pdf_loader, "__kmeans_embeddings", fake_kmeans_embeddings)

    # Stub multiprocessing_wrapper to return per-group deduplication results.
    def fake_multiprocessing_wrapper(tasks, n):
        assert isinstance(tasks, list)
        assert len(tasks) == 2
        return [["a", "c"], ["m"]]

    monkeypatch.setattr(pdf_loader, "multiprocessing_wrapper", fake_multiprocessing_wrapper)

    res = fn(factor_dict)

    # After sorting factor names: ['a','c','m','z']
    # Expect only the first returned group with >1 items to be included
    assert isinstance(res, list)
    assert len(res) == 1
    assert set(res[0]) == {"a", "c"}
