import importlib
from types import SimpleNamespace
import pytest

pdf_loader = importlib.import_module(
    "rdagent.scenarios.qlib.factor_experiment_loader.pdf_loader"
)


def test_deduplicate_without_viability_round_042(monkeypatch):
    """
    Scenario:
    - Patch __deduplicate_factor_dict to return two small groups so they are appended to final_duplication_names_list.
    - Set RD_AGENT_SETTINGS.max_output_duplicate_factor_group high enough so groups are considered "small" (< max).
    - No factor_viability_dict provided (None).

    Oracle:
    - B is mapped to A (so B does not appear in the result) and A, C, D remain.
    - final_duplication_names_list is sorted largest-first (['A','B'] before ['C']).
    """

    # Patch the settings to control the threshold
    monkeypatch.setattr(pdf_loader, "RD_AGENT_SETTINGS", SimpleNamespace(max_output_duplicate_factor_group=3))

    # Patch the internal deduplication function to return controlled groups
    def fake_dedup(_current):
        # Always return the same groups regardless of current_round_factor_dict
        return [["A", "B"], ["C"]]

    monkeypatch.setattr(pdf_loader, "__deduplicate_factor_dict", fake_dedup)

    # Prepare factor dict with keys that will be affected by mapping (B -> A) and untouched (C, D)
    factor_dict = {
        "A": {"desc": "alpha"},
        "B": {"desc": "beta"},
        "C": {"desc": "gamma"},
        "D": {"desc": "delta"},
    }

    result_dict, final_dup_list = pdf_loader.deduplicate_factors_by_llm(factor_dict)

    # B should be replaced by A, so B must not be present; A, C, D remain
    assert set(result_dict.keys()) == {"A", "C", "D"}

    # final_dup_list should be sorted by length descending: ['A','B'] (len2) before ['C'] (len1)
    assert final_dup_list == [["A", "B"], ["C"]]


def test_deduplicate_with_viability_and_lowercase_handling_round_042(monkeypatch):
    """
    Scenario:
    - Simulate multi-round behavior by using a fake __deduplicate_factor_dict that returns different lists
      on consecutive calls via a small closure counter.
    - Provide factor_viability_dict such that one returned duplicate group has all False (so it is skipped
      by the viability check) and other factors have True/False to test exclusion.
    - Test lowercase deduplication: 'Foo' and 'foo' should result in only the first being included.

    Oracle:
    - Groups returned in the final deduplication pass that are all non-viable are skipped (continue branch).
    - Factors marked not viable are not included in the final result.
    - Lowercase duplicates are prevented via added_lower_name_set.
    """

    # Prepare a closure to control successive returns of __deduplicate_factor_dict
    call_state = {"calls": 0}

    def fake_dedup_multi(current_round_dict):
        # First call: return a group that will trigger new_round_names (length equals threshold or larger)
        if call_state["calls"] == 0:
            call_state["calls"] += 1
            return [["X", "Y", "Z"]]
        # Second call: return a final set of groups used to build to_replace_dict; we include one group
        # composed of non-viable factors to trigger the "continue" branch, and ensure at least one small
        # group so the loop can terminate.
        else:
            call_state["calls"] += 1
            return [["P", "Q"], ["R"]]

    # Use a threshold such that a group of length 3 will be treated as a large group (force another round)
    monkeypatch.setattr(pdf_loader, "RD_AGENT_SETTINGS", SimpleNamespace(max_output_duplicate_factor_group=3))
    monkeypatch.setattr(pdf_loader, "__deduplicate_factor_dict", fake_dedup_multi)

    # Build factor_dict: include P/Q (both non-viable), R (viable), also some other factors to exercise
    # viability filtering and lowercase deduplication.
    factor_dict = {
        "P": {"desc": "p"},
        "Q": {"desc": "q"},
        "R": {"desc": "r"},
        "A": {"desc": "a"},
        "Foo": {"desc": "foo-upper"},
        "foo": {"desc": "foo-lower"},
        "Bad": {"desc": "bad"},
    }

    # Factor viability: P and Q not viable (to trigger continue), R and A and Foo/foo viable, Bad not viable
    factor_viability_dict = {
        "P": {"viability": False},
        "Q": {"viability": False},
        "R": {"viability": True},
        "A": {"viability": True},
        "Foo": {"viability": True},
        "foo": {"viability": True},
        "Bad": {"viability": False},
    }

    result_dict, final_dup_list = pdf_loader.deduplicate_factors_by_llm(factor_dict, factor_viability_dict)

    # final_dup_list should be whatever the last dedup returned appended as "small" groups.
    # In our fake, the second return includes ['P','Q'] and ['R']; since ['P','Q'] are non-viable
    # they will be skipped when building to_replace_dict. ['R'] is viable and may be chosen as target
    # for itself (no mapping introduced from this group). Because P and Q were non-viable, they should
    # also be filtered out when assembling the final llm_deduplicated_factor_dict.
    assert [sorted(group) for group in final_dup_list] == [sorted(group) for group in [["P", "Q"], ["R"]]]

    # The resulting dict should include A and either Foo or foo but not both (lowercase dedupe).
    # 'Bad' should be omitted because it's not viable. P and Q are omitted because they are non-viable.
    resulting_keys = set(result_dict.keys())
    assert "A" in resulting_keys
    # Only one of Foo/foo should be present
    assert ("Foo" in resulting_keys) ^ ("foo" in resulting_keys)
    assert "Bad" not in resulting_keys
    assert "P" not in resulting_keys and "Q" not in resulting_keys
