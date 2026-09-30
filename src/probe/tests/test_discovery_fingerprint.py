"""Failure identity across disposable checkouts, without model calls."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from probe.python.run.discovery import (
    confirm_failure,
    failure_fingerprint,
    is_discovery_failure,
)
from probe.python.run.session import AssetValidationState, ValidationSession


def summary(nodeid="tests/a/test_probe.py::TestProbe::test_value[a/b:12]", **changes):
    return {
        "status": "assertion_failed",
        "passed": False,
        "timed_out": False,
        "classification_source": "structured_reporter",
        "classification_reason": "non_assertion_or_incomplete_execution",
        "failed_nodeids": [nodeid],
        "failure_excerpt": "AssertionError: expected /api/v1/value:12",
        "diagnostics": {"test_failures": [{"outcome": "failed", "phase": "call"}]},
        **changes,
    }


@pytest.mark.parametrize("uri", [False, True])
def test_fingerprint_normalizes_only_recorded_root_before_compaction(uri):
    fingerprints = []
    for root in ("/tmp/validation-short/checkout", "/tmp/" + "long-" * 50 + "/checkout"):
        prefix = ("file://" if uri else "") + root
        observed = summary(
            prefix + "/tests/a/test_probe.py::TestProbe::test_value[a/b:12]",
            failure_excerpt=f'ValueError: "{prefix}/src/value.py:12:3" ' + "detail " * 80,
        )
        fingerprints.append(failure_fingerprint(observed, copy_root=root))
    assert fingerprints[0] == fingerprints[1]


@pytest.mark.parametrize("nodeid", [
    "tests/b/test_probe.py::TestProbe::test_value[a/b:12]",
    "tests/a/test_probe.py::OtherProbe::test_value[a/b:12]",
    "tests/a/test_probe.py::TestProbe::test_other[a/b:12]",
    "tests/a/test_probe.py::TestProbe::test_value[a/b:13]",
])
def test_fingerprint_preserves_complete_test_identity(nodeid):
    assert failure_fingerprint(summary()) != failure_fingerprint(summary(nodeid))


@pytest.mark.parametrize("first,second", [
    ("expected /api/v1/a", "expected /api/v1/b"),
    ("endpoint http://host:123/api", "endpoint http://host:456/api"),
    ("value:12:3", "value:12:4"),
    ("at /tmp/validation-one/checkout/src/a.py:10", "at /tmp/validation-two/checkout/src/a.py:10"),
    ("at /fixture/checkout/src/a.py:10", "at /fixture/checkout/src/b.py:10"),
    ("at /fixture/checkout/src/a.py:10", "at /fixture/checkout/src/a.py:11"),
    ("at /fixture/checkout-other/a", "at /fixture/checkout-another/a"),
    ("at /prefix/fixture/checkout/a", "at /different/fixture/checkout/a"),
])
def test_fingerprint_preserves_semantic_paths_and_numbers(first, second):
    assert failure_fingerprint(summary(failure_excerpt=first), copy_root="/fixture/checkout") != failure_fingerprint(
        summary(failure_excerpt=second), copy_root="/fixture/checkout"
    )


def test_fingerprint_keeps_identity_values_and_sorts_nodeids():
    root = "/fixture/checkout"
    assert failure_fingerprint(summary(root + "/tests/a/test_probe.py::TestProbe::test_value[a/b:12]"), copy_root=root) == failure_fingerprint(summary())
    first = summary("tests/probe.py::test_value[/fixture/checkout/a]")
    second = summary("tests/probe.py::test_value[/another/checkout/a]")
    assert failure_fingerprint(first, copy_root="/fixture/checkout") != failure_fingerprint(
        second, copy_root="/another/checkout"
    )
    ids = ["tests/b.py::test_b", "tests/a.py::test_a"]
    assert failure_fingerprint(summary(failed_nodeids=ids)) == failure_fingerprint(
        summary(failed_nodeids=list(reversed(ids)))
    )


def test_deleted_checkout_resolves_surviving_symlink_ancestor(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    fingerprints = []
    for name in ("first", "second"):
        lexical = alias / name / "checkout"
        canonical = lexical.resolve()
        assert not lexical.exists()
        fingerprints.append(failure_fingerprint(summary(
            f"{canonical}/tests/probe.py::test_identity",
            failure_excerpt=f"ValueError: {canonical}/src/a.py:12:3",
        ), copy_root=str(lexical)))
    assert fingerprints[0] == fingerprints[1]


@pytest.mark.parametrize("status", ["assertion_failed", "needs_repair"])
@pytest.mark.parametrize("drift", [False, True])
def test_confirmation_uses_each_materialized_root(tmp_path, status, drift):
    def validation(root, name):
        return {
            "materialized": {"copy_root": root},
            "summary": summary(
                f"{root}/tests/probe.py::test_{name}", status=status,
                failure_excerpt=f"ValueError: {root}/src/a.py:10",
            ),
        }

    first = validation("/tmp/validation-first/checkout", "a")
    queued = [validation("/tmp/validation-second/checkout", "b" if drift else "a")]
    runtime = SimpleNamespace(
        options=SimpleNamespace(reveal_confirmation_runs=1),
        validation=SimpleNamespace(run=lambda **kwargs: queued.pop(0)),
    )
    state = AssetValidationState(None, tmp_path / "proposal.json", tmp_path, first)
    result = confirm_failure(runtime, state, "base")
    assert result["stable"] is (not drift)
    assert result["runs"][0]["passed"] is (not drift)


@pytest.mark.parametrize("changes", [
    {"timed_out": True},
    {"classification_source": "text"},
    {"classification_reason": "collection_error"},
    {"failed_nodeids": []},
    {"diagnostics": {"test_failures": [{"outcome": "failed", "phase": "setup"}]}},
    {"diagnostics": {"test_failures": [{"outcome": "failed", "phase": "teardown"}]}},
])
def test_nonassertion_eligibility_is_unchanged(changes):
    assert not is_discovery_failure(summary(status="needs_repair", **changes))


@pytest.mark.parametrize("exception", ["AssertionError", "ValueError"])
def test_real_pytest_failure_is_stable_across_validation_copies(tmp_path, exception):
    root = tmp_path / "prepared"
    root.mkdir()
    (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    asset = SimpleNamespace(
        test_file="tests/test_identity.py",
        append_code=f"def test_identity():\n    raise {exception}(__file__)\n",
    )
    validation = ValidationSession(
        case={"revisions": {"latest": "fixture"}}, roots={"latest": root},
        interpreters={"latest": sys.executable}, timeout=15,
    )
    sample = tmp_path / "sample"
    proposal = sample / "proposal.json"
    first = validation.run("latest", asset, proposal, sample)
    assert is_discovery_failure(first["summary"]), first["summary"]
    runtime = SimpleNamespace(
        options=SimpleNamespace(reveal_confirmation_runs=2), validation=validation,
    )
    result = confirm_failure(
        runtime, AssetValidationState(asset, proposal, sample, first), "base"
    )
    assert result["stable"], result
    assert len({first["summary"]["failure_excerpt"], *(r["latest"]["failure_excerpt"] for r in result["runs"])}) > 1
