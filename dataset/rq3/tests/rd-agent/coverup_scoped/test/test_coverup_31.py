# file: rdagent/scenarios/data_science/proposal/exp_gen/proposal.py:706-773
# asked: {"lines": [718, 719, 721, 722, 723, 724, 725, 726, 728, 729, 731, 732, 733, 734, 735, 739, 740, 741, 742, 746, 749, 750, 754, 755, 757, 758, 760, 761, 765, 766, 767, 769, 770, 772, 773], "branches": [[719, 721], [719, 728], [749, 750], [749, 754], [757, 758], [757, 760], [766, 767], [766, 772], [769, 770], [769, 772]]}
# gained: {"lines": [718, 719, 721, 722, 723, 724, 725, 726, 728, 729, 731, 732, 733, 734, 735, 739, 740, 741, 742, 746, 749, 750, 754, 755, 757, 758, 760, 761, 765, 766, 767, 769, 770, 772, 773], "branches": [[719, 721], [719, 728], [749, 750], [749, 754], [757, 758], [757, 760], [766, 767], [766, 772], [769, 770], [769, 772]]}

import json
import pytest

import rdagent.scenarios.data_science.proposal.exp_gen.proposal as proposal_module
from rdagent.scenarios.data_science.proposal.exp_gen.proposal import DSProposalV2ExpGen


class MockAPIBackend:
    # class variable to hold the response to return
    response_str = json.dumps({})

    def __init__(self, *args, **kwargs):
        pass

    def build_messages_and_create_chat_completion(self, *args, **kwargs):
        return self.__class__.response_str

    def supports_response_schema(self):
        return False


class DummyTemplate:
    def __init__(self, key):
        self.key = key

    def r(self, *args, **kwargs):
        # return a deterministic string for prompts; accept kwargs
        return f"prompt-for-{self.key}"


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, msg):
        self.infos.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)


def make_instance():
    # create instance without calling __init__ to avoid heavy initialization
    inst = object.__new__(DSProposalV2ExpGen)
    return inst


def test_hypothesis_critique_with_full_critiques(monkeypatch):
    """
    Response contains 'critiques' key with all problem critiques.
    Expect the function to return that dict unchanged.
    """
    # patch dependencies in module
    monkeypatch.setattr(proposal_module, "APIBackend", MockAPIBackend)
    monkeypatch.setattr(proposal_module, "T", DummyTemplate)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(proposal_module, "logger", dummy_logger)

    # prepare input
    hypothesis_dict = {
        "problem_a": {"component": "compA", "hypothesis": "hA", "reason": "rA"},
        "problem_b": {"component": "compB", "hypothesis": "hB", "reason": "rB"},
    }
    problems_dict = {
        "problem_a": {"problem": "orig A"},
        "problem_b": {"problem": "orig B"},
    }

    # API returns a JSON string with 'critiques' key containing both problems
    MockAPIBackend.response_str = json.dumps(
        {"critiques": {"problem_a": {"critique": "good A"}, "problem_b": {"critique": "good B"}}}
    )

    inst = make_instance()

    result = inst.hypothesis_critique(
        hypothesis_dict,
        problems_dict,
        scenario_desc="scen",
        sota_exp_desc="sota",
        exp_feedback_list_desc="fb",
    )

    assert isinstance(result, dict)
    assert result == {"problem_a": {"critique": "good A"}, "problem_b": {"critique": "good B"}}
    # no warnings should have been logged
    assert dummy_logger.warnings == []
    # info should mention number of critiques
    assert any("Generated critiques for" in m for m in dummy_logger.infos)


def test_hypothesis_critique_with_missing_critiques_key_but_all_problems_present(monkeypatch):
    """
    Response JSON does not have 'critiques' key but includes keys for all expected problems.
    Expect the function to accept response_dict directly as critiques.
    """
    monkeypatch.setattr(proposal_module, "APIBackend", MockAPIBackend)
    monkeypatch.setattr(proposal_module, "T", DummyTemplate)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(proposal_module, "logger", dummy_logger)

    hypothesis_dict = {
        "p1": {"component": "c1", "hypothesis": "h1", "reason": "r1"},
        "p2": {"component": "c2", "hypothesis": "h2", "reason": "r2"},
    }
    problems_dict = {"p1": {"problem": "orig1"}, "p2": {"problem": "orig2"}}

    # API returns a JSON string without 'critiques' but with keys for p1 and p2
    MockAPIBackend.response_str = json.dumps(
        {"p1": {"critique": "c1"}, "p2": {"critique": "c2"}}
    )

    inst = make_instance()
    result = inst.hypothesis_critique(
        hypothesis_dict,
        problems_dict,
        scenario_desc="s",
        sota_exp_desc="sota",
        exp_feedback_list_desc="fb",
    )

    assert result == {"p1": {"critique": "c1"}, "p2": {"critique": "c2"}}
    # no warnings
    assert dummy_logger.warnings == []
    assert any("Generated critiques for" in m for m in dummy_logger.infos)


def test_hypothesis_critique_with_partial_critiques_adds_defaults(monkeypatch):
    """
    Response contains 'critiques' key but is missing some problem keys.
    Expect missing critiques to be added with default message and a warning logged.
    """
    monkeypatch.setattr(proposal_module, "APIBackend", MockAPIBackend)
    monkeypatch.setattr(proposal_module, "T", DummyTemplate)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(proposal_module, "logger", dummy_logger)

    hypothesis_dict = {
        "x": {"component": "cx", "hypothesis": "hx", "reason": "rx"},
        "y": {"component": "cy", "hypothesis": "hy", "reason": "ry"},
    }
    problems_dict = {"x": {"problem": "ox"}, "y": {"problem": "oy"}}

    # Only x is present in critiques
    MockAPIBackend.response_str = json.dumps({"critiques": {"x": {"critique": "ok x"}}})

    inst = make_instance()
    result = inst.hypothesis_critique(
        hypothesis_dict,
        problems_dict,
        scenario_desc="scen",
        sota_exp_desc="sota",
        exp_feedback_list_desc="fb",
    )

    # Both keys should now be present
    assert "x" in result and "y" in result
    assert result["x"] == {"critique": "ok x"}
    assert result["y"] == {"critique": "No specific critique available for this hypothesis."}
    # warning should have been logged about missing critiques
    assert any("Missing critiques for problems" in w or "Missing critiques for" in w for w in dummy_logger.warnings)
    assert any("Generated critiques for" in m for m in dummy_logger.infos)


def test_hypothesis_critique_raises_when_response_missing_expected_problems(monkeypatch):
    """
    Response lacks 'critiques' key and does not include all expected problem names.
    Expect ValueError to be raised.
    """
    monkeypatch.setattr(proposal_module, "APIBackend", MockAPIBackend)
    monkeypatch.setattr(proposal_module, "T", DummyTemplate)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(proposal_module, "logger", dummy_logger)

    hypothesis_dict = {
        "a": {"component": "ca", "hypothesis": "ha", "reason": "ra"},
        "b": {"component": "cb", "hypothesis": "hb", "reason": "rb"},
    }
    problems_dict = {"a": {"problem": "oa"}, "b": {"problem": "ob"}}

    # Response only contains 'a' key, missing 'b'; no 'critiques' key
    MockAPIBackend.response_str = json.dumps({"a": {"critique": "only a"}})

    inst = make_instance()

    with pytest.raises(ValueError) as exc:
        inst.hypothesis_critique(
            hypothesis_dict,
            problems_dict,
            scenario_desc="scen",
            sota_exp_desc="sota",
            exp_feedback_list_desc="fb",
        )

    assert "Critique response missing expected problems" in str(exc.value)
