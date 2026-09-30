import pytest

from sweagent.agent.action_sampler import BinaryTrajectoryComparison


class DummyTools:
    """A minimal tools stub that exposes parse_actions(completion) -> (thought, action).
    The test completions are dicts with an 'action_text' key; parse_actions returns that
    as the action so tests can deterministically control behavior."""

    def parse_actions(self, completion):
        return ("thought", completion["action_text"])


class DummyConfig:
    """Minimal config placeholder. BinaryTrajectoryComparison only stores it; tests
    for contains_edits do not rely on any config attributes."""

    system_template = "sys"
    instance_template = "inst"
    comparison_template = "cmp"


def make_sampler():
    return BinaryTrajectoryComparison(config=DummyConfig(), model=object(), tools=DummyTools())


def test_contains_edits_edit_round_049():
    sampler = make_sampler()
    completions = [{"action_text": "edit the file to fix bug"}]
    # action starts with 'edit' -> should detect an edit
    assert sampler.contains_edits(completions) is True


def test_contains_edits_str_replace_insert_round_049():
    sampler = make_sampler()
    completions = [{"action_text": "str_replace_editor insert into file content"}]
    # action starts with 'str_replace_editor insert' -> should detect an edit
    assert sampler.contains_edits(completions) is True


def test_contains_edits_second_match_round_049():
    sampler = make_sampler()
    completions = [
        {"action_text": "some unrelated action"},
        {"action_text": "str_replace_editor str_replace replace text"},
    ]
    # first completion doesn't match; second does. Ensures loop continues and returns True
    assert sampler.contains_edits(completions) is True


def test_contains_edits_no_match_round_049():
    sampler = make_sampler()
    completions = [
        {"action_text": "do something"},
        {"action_text": "another non-edit action"},
    ]
    # no completion starts with any of the keywords -> should return False
    assert sampler.contains_edits(completions) is False
