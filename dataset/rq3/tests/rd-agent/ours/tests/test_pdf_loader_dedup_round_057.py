import importlib
from types import SimpleNamespace

import pytest

MODULE_PATH = "rdagent.scenarios.qlib.factor_experiment_loader.pdf_loader"

@staticmethod
def _load_module():
    return importlib.import_module(MODULE_PATH)


def test_empty_dict_round_057():
    """
    When an empty factor_dict is passed, the function should return an empty list.
    Covers: early-return branch (len(factor_dict) == 0).
    """
    module = _load_module()
    assert module.__deduplicate_factor_dict({}) == []


def test_small_group_round_057(monkeypatch):
    """
    Tests the branch where the number of factors is smaller than
    RD_AGENT_SETTINGS.max_input_duplicate_factor_group. Ensures the
    embedding creation is called and that multiprocessing_wrapper's
    result drives the returned duplication list.
    """
    module = _load_module()

    # Make RD_AGENT_SETTINGS simple and deterministic for the small-group branch
    monkeypatch.setattr(
        module,
        "RD_AGENT_SETTINGS",
        SimpleNamespace(max_input_duplicate_factor_group=5, max_kmeans_group_number=10, multi_proc_n=1),
    )

    created_embeddings = {}

    # Patch APIBackend.create_embedding to capture input and return a deterministic embedding
    def fake_create_embedding(full_str_list):
        # return simple numeric embeddings (one-dim) for determinism
        created_embeddings['last'] = [ [float(i)] for i in range(len(full_str_list)) ]
        return created_embeddings['last']

    monkeypatch.setattr(module.APIBackend, "create_embedding", fake_create_embedding)

    # Patch multiprocessing_wrapper to return a simulated deduplication result
    def fake_multiprocessing_wrapper(tasks, n):
        # Validate tasks structure: list of (callable, args)
        assert isinstance(tasks, list)
        # Return a list where first sub-result indicates two duplicated factor names
        return [["f1", "f2"]]

    monkeypatch.setattr(module, "multiprocessing_wrapper", fake_multiprocessing_wrapper)

    factor_dict = {
        "f1": {"description": "d1", "formulation": "form1", "variables": "v1"},
        "f2": {"description": "d2", "formulation": "form2", "variables": "v2"},
        "f3": {"description": "d3", "formulation": "form3", "variables": "v3"},
    }

    result = module.__deduplicate_factor_dict(factor_dict)

    # We expect the wrapper output to be filtered and returned as the duplication list
    assert result == [["f1", "f2"]]
    # Also ensure the embedding was created for the three-factor input
    assert len(created_embeddings['last']) == 3


def test_kmeans_loop_round_057(monkeypatch):
    """
    Tests the branch where len(full_str_list) >= RD_AGENT_SETTINGS.max_input_duplicate_factor_group,
    forcing the code to enter the kmeans loop. We simulate a first k that does NOT satisfy the
    small-group condition and a later k that does, ensuring the break is taken and the
    corresponding groups are processed.
    """
    module = _load_module()

    # Configure RD_AGENT_SETTINGS so the else branch (kmeans loop) runs.
    monkeypatch.setattr(
        module,
        "RD_AGENT_SETTINGS",
        SimpleNamespace(max_input_duplicate_factor_group=2, max_kmeans_group_number=4, multi_proc_n=1),
    )

    # Patch APIBackend.create_embedding to return deterministic embeddings
    def fake_create_embedding(full_str_list):
        return [[float(i)] for i in range(len(full_str_list))]

    monkeypatch.setattr(module.APIBackend, "create_embedding", fake_create_embedding)

    # Track k values tried
    tried_ks = []

    # Patch __kmeans_embeddings to simulate first k failing the size check and second k succeeding
    def fake_kmeans_embeddings(embeddings, k):
        tried_ks.append(k)
        if k == 2:
            # first returned grouping: first group has length equal to max_input_duplicate_factor_group (2)
            return [[0, 1], [2, 3]]
        elif k == 3:
            # second returned grouping: first group has length 1 (< max_input_duplicate_factor_group) -> triggers break
            return [[0], [1, 2, 3]]
        else:
            return [[0, 1, 2, 3]]

    monkeypatch.setattr(module, "__kmeans_embeddings", fake_kmeans_embeddings)

    # Patch multiprocessing_wrapper to return results corresponding to groups produced for final k (k==3)
    def fake_multiprocessing_wrapper(tasks, n):
        # tasks correspond to factor_name_groups built from the chosen kmeans_index_group
        # For the chosen k (3) we return per-group deduplication lists; include one group with >1 names
        return [["a"], ["b", "c"]]

    monkeypatch.setattr(module, "multiprocessing_wrapper", fake_multiprocessing_wrapper)

    # Create four factors with deterministic keys that sort to ["a","b","c","d"]
    factor_dict = {
        "a": {"description": "da", "formulation": "fa", "variables": "va"},
        "b": {"description": "db", "formulation": "fb", "variables": "vb"},
        "c": {"description": "dc", "formulation": "fc", "variables": "vc"},
        "d": {"description": "dd", "formulation": "fd", "variables": "vd"},
    }

    result = module.__deduplicate_factor_dict(factor_dict)

    # We expect only the group with multiple names to be appended
    assert result == [["b", "c"]]
    # Ensure the kmeans loop tried at least k==2 and k==3
    assert 2 in tried_ks and 3 in tried_ks
