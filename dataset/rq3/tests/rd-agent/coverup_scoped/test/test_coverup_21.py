# file: rdagent/scenarios/qlib/factor_experiment_loader/pdf_loader.py:515-566
# asked: {"lines": [519, 520, 523, 524, 526, 527, 528, 529, 531, 533, 534, 536, 539, 541, 542, 543, 545, 546, 547, 548, 550, 551, 552, 553, 554, 556, 557, 558, 560, 561, 562, 563, 564, 566], "branches": [[523, 524], [523, 539], [527, 528], [527, 533], [528, 529], [528, 531], [533, 534], [533, 536], [542, 543], [542, 556], [543, 545], [543, 550], [546, 547], [546, 548], [551, 542], [551, 552], [552, 553], [552, 554], [558, 560], [558, 566], [560, 558], [560, 561], [561, 562], [561, 563]]}
# gained: {"lines": [519, 520, 523, 524, 526, 527, 528, 529, 531, 533, 534, 536, 539, 541, 542, 543, 545, 546, 547, 548, 550, 551, 552, 553, 554, 556, 557, 558, 560, 561, 562, 563, 564, 566], "branches": [[523, 524], [527, 528], [527, 533], [528, 529], [528, 531], [533, 534], [533, 536], [542, 543], [542, 556], [543, 545], [543, 550], [546, 547], [546, 548], [551, 542], [551, 552], [552, 553], [552, 554], [558, 560], [558, 566], [560, 558], [560, 561], [561, 562], [561, 563]]}

import pytest

from rdagent.scenarios.qlib.factor_experiment_loader import pdf_loader


def test_deduplicate_without_viability_multiround(monkeypatch):
    # Prepare factor dict with intentional case-duplicate 'Foo' and 'foo'
    factor_dict = {
        "a1": {"meta": "v1"},
        "a2": {"meta": "v2"},
        "a3": {"meta": "v3"},
        "a4": {"meta": "v4"},
        "b1": {"meta": "v5"},
        "b2": {"meta": "v6"},
        "Foo": {"meta": "v7"},
        "foo": {"meta": "v8"},
    }

    # Set threshold so groups of length >=3 are reprocessed
    monkeypatch.setattr(pdf_loader.RD_AGENT_SETTINGS, "max_output_duplicate_factor_group", 3)

    call_count = {"n": 0}

    def fake_dedupe(current_round_factor_dict):
        # First call returns a big group to force a second round
        if call_count["n"] == 0:
            call_count["n"] += 1
            return [["a1", "a2", "a3", "a4"]]
        # Second call returns small groups which should be appended to final list
        call_count["n"] += 1
        return [["b1", "b2"], ["a1", "a3"], ["Foo", "foo"]]

    monkeypatch.setattr(pdf_loader, "__deduplicate_factor_dict", fake_dedupe)

    deduped_dict, final_duplication_names_list = pdf_loader.deduplicate_factors_by_llm(factor_dict)

    # final_duplication_names_list should be the groups returned in the second call, sorted by len desc
    assert final_duplication_names_list == [["b1", "b2"], ["a1", "a3"], ["Foo", "foo"]]

    # to_replace built from the last duplication_names_list (fake_dedupe second call):
    # 'b2' -> 'b1', 'a3' -> 'a1', 'foo' -> 'Foo'
    # So deduped_dict should include keys not in to_replace and not duplicate after lowercasing.
    # Given our insertion order, 'Foo' appears before 'foo', so 'foo' should be excluded by lowercase uniqueness.
    expected_keys = {"a1", "a2", "a4", "b1", "Foo"}
    assert set(deduped_dict.keys()) == expected_keys

    # Ensure the values are exactly those from the original factor_dict for included keys
    for k in expected_keys:
        assert deduped_dict[k] is factor_dict[k]


def test_deduplicate_with_viability_and_skip_nonviable(monkeypatch):
    # Prepare factor dict
    factor_dict = {
        "A": {"meta": "A"},
        "B": {"meta": "B"},
        "C": {"meta": "C"},
        "D": {"meta": "D"},
    }

    # Make max group large so all groups get appended to final list without new rounds
    monkeypatch.setattr(pdf_loader.RD_AGENT_SETTINGS, "max_output_duplicate_factor_group", 10)

    # Return two groups: ['A','B'] and ['C','D']
    def fake_dedupe(_):
        return [["A", "B"], ["C", "D"]]

    monkeypatch.setattr(pdf_loader, "__deduplicate_factor_dict", fake_dedupe)

    # Provide viability: A False, B True -> pick B as target for first group.
    # C False, D False -> group should be skipped when building replacements.
    factor_viability_dict = {
        "A": {"viability": False},
        "B": {"viability": True},
        "C": {"viability": False},
        "D": {"viability": False},
    }

    deduped_dict, final_duplication_names_list = pdf_loader.deduplicate_factors_by_llm(
        factor_dict, factor_viability_dict=factor_viability_dict
    )

    # final_duplication_names_list should include both groups (viability not considered here)
    assert final_duplication_names_list == [["A", "B"], ["C", "D"]]

    # Replacement mapping: from first group A->B applied; second group has no True -> ignored
    # Final dictionary should exclude A (replaced) and exclude non-viable C and D;
    # Only B remains.
    assert set(deduped_dict.keys()) == {"B"}
    assert deduped_dict["B"] is factor_dict["B"]
