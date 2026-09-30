"""Compare coverage normalization and accepted-test state merges with formal code."""

from copy import deepcopy
import importlib
import os
from pathlib import Path

import pytest

from augment.python.run.coverage_state import branch_keys
from augment.python.run import coverage_state


@pytest.fixture
def formal():
    root = os.environ.get("AUGMENT_FORMAL_ROOT") or os.environ.get("PROBE_FORMAL_ROOT")
    if not root:
        pytest.skip("set AUGMENT_FORMAL_ROOT for reference checks")
    import common

    directory = str(Path(root) / "src/common")
    if directory not in common.__path__:
        common.__path__.append(directory)
    return importlib.import_module("common.test_augmentF.python.run.coverage_state")


@pytest.mark.parametrize(
    "arcs",
    [
        None,
        {},
        (),
        [],
        [[1, 2], [1, 2], [2, -1]],
        [["2", "3"], [True, False]],
        [[1], [1, 2, 3], "1->2", (1, 2)],
        [["bad", 2]],
        [[None, 2]],
    ],
)
def test_branch_normalization_matches_formal(formal, arcs):
    try:
        expected = formal.branch_keys(arcs)
    except (TypeError, ValueError) as exc:
        with pytest.raises(type(exc)) as actual:
            branch_keys(arcs)
        assert str(actual.value) == str(exc)
    else:
        assert branch_keys(arcs) == expected


def snapshot():
    return {
        "ldh_coverage": {
            "files": {
                "agent.py": {
                    "lines": [2, 3, 4],
                    "covered_lines": [2],
                    "uncovered_lines": [3, 4],
                    "covered_branches": ["2->3"],
                    "uncovered_branches": ["2->4", "3->-1"],
                },
            },
        },
        "general_coverage": {
            "files": {
                "agent.py": {
                    "total_lines": 5,
                    "covered_lines": [1, 2],
                    "uncovered_lines": [3, 4, 5],
                    "total_branches": 3,
                    "covered_branches": ["2->3"],
                    "uncovered_branches": ["2->4", "3->-1"],
                },
                "other.py": {
                    "total_lines": 2,
                    "covered_lines": [],
                    "uncovered_lines": [1, 2],
                    "total_branches": 0,
                    "covered_branches": [],
                    "uncovered_branches": [],
                },
            },
            "totals": {},
        },
    }


def compare_merge(formal, name, actual, expected, measured):
    original = deepcopy(measured)
    # Only the formal comparison uses the archived snapshot field name.
    if "ldh_coverage" in expected:
        expected["ldcr_coverage"] = expected.pop("ldh_coverage")
    try:
        getattr(formal, name)(expected, measured)
    except (KeyError, TypeError, ValueError, AttributeError, SystemExit) as exc:
        with pytest.raises(type(exc)) as error:
            getattr(coverage_state, name)(actual, measured)
        assert str(error.value) == str(exc).replace("ldcr_coverage", "ldh_coverage")
    else:
        assert getattr(coverage_state, name)(actual, measured) is None
    finally:
        if "ldcr_coverage" in expected:
            expected["ldh_coverage"] = expected.pop("ldcr_coverage")
    assert actual == expected
    assert measured == original


def test_summary_matches_formal_with_renamed_fields(formal):
    actual = snapshot()
    expected = deepcopy(actual)
    expected["ldcr_coverage"] = expected.pop("ldh_coverage")
    summary = formal.coverage_summary(
        snapshot=expected,
        iteration=0,
        snapshot_path=Path("coverage.json"),
        ranking_count=0,
        selected_objective_ids=[],
    )
    assert coverage_state.coverage_summary(actual) == {
        "ldh_lines": summary["ldcr_lines"],
        "branches": summary["branches"],
        "project_coverage": summary["project_coverage"],
    }


@pytest.mark.parametrize("name", ["update_snapshot", "update_general_coverage"])
def test_repeated_merges_preserve_state(formal, name):
    actual = snapshot()
    expected = deepcopy(actual)
    measurements = [
        {},
        {"files": {"agent.py": {"executed_lines": [2, 99]}}},
        {"files": {"agent.py": {"executed_lines": [3, "4", "bad", None]}}},
        {"files": {"agent.py": {"executed_branches": [[2, 4], [2, 4], [3, -1]]}}},
        {"files": {"agent.py": {"executed_lines": [5]}}},
        {"files": {"other.py": {"executed_lines": [2]}, "unknown.py": {}}},
        {"files": {}},
    ]
    for measured in measurements * 2:
        compare_merge(formal, name, actual, expected, measured)


@pytest.mark.parametrize("name", ["update_snapshot", "update_general_coverage"])
@pytest.mark.parametrize(
    "measured",
    [
        {"files": None},
        {"files": []},
        {"files": {"agent.py": None}},
        {"files": {"agent.py": {"executed_lines": None}}},
        {"files": {"agent.py": {"executed_branches": [["bad", 2]]}}},
    ],
)
def test_coverage_edge_cases_preserve_state_and_errors(formal, name, measured):
    actual = snapshot()
    compare_merge(formal, name, actual, deepcopy(actual), measured)


@pytest.mark.parametrize("name", ["update_snapshot", "update_general_coverage"])
@pytest.mark.parametrize(
    "state",
    [
        {},
        {"ldh_coverage": {"files": []}},
        {"general_coverage": {"files": []}},
        {"general_coverage": {"files": {"agent.py": None}}},
    ],
)
def test_snapshot_edge_cases_preserve_state_and_errors(formal, name, state):
    compare_merge(
        formal, name, deepcopy(state), deepcopy(state), {"files": {"agent.py": {}}}
    )
