"""Harmless synthetic cases exercising the prepared Python probe workflow."""

from __future__ import annotations

import copy
import json
import os
import shutil
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from formal_names import install_formal_name_adapter

install_formal_name_adapter()

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from probe.python.input.target_packets import build_target_packet
from probe.python.run.generation import prior_attempt_ledger
from probe.python.run.case import run_prepared_case
from probe.python.run.options import TargetProbeRunOptions
from probe.python.run.session import TargetProbeRuntime
from probe.python.run.workflow import run_guided_case_samples, run_target_sample


SAMPLE_METADATA_FIELDS = {
    "boundary_plan",
    "plan_notes",
    "plan_context",
    "plan_context_request_count",
    "plan_retrieved_context_count",
    "plan_parse_errors",
    "plan_parse_error_count",
    "parse_errors",
    "parse_error_count",
    "dropped_duplicate_assets",
    "dropped_duplicate_asset_count",
}


REPAIR_DERIVED_FIELDS = {
    "called", "attempts", "attempt_count", "context_request_count",
    "retrieved_context_count", "parse_error_count", "diagnosis",
    "additive_variant", "use_repaired",
}


ASSET_EXPLANATION_FIELDS = {
    "supporting_evidence", "expected_observation", "novelty_from_prior", "bug_hypothesis",
}


def repair_evidence(record):
    """Project the formal grouped repair report to its original attempt records."""
    if not record.get("called"):
        return {key: value for key, value in record.items() if key != "attempt_count"}
    attempts = record.get("attempts", [record])
    assert record["attempt_count"] == len(attempts)
    return {
        "called": True,
        "attempts": [
            {key: value for key, value in item.items() if key not in REPAIR_DERIVED_FIELDS}
            for item in attempts
        ],
    }


class FixedModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def complete(self, prompt):
        self.prompts.append(prompt)
        assert self.responses, "unexpected additional model call"
        return {
            "choices": [{"message": {"content": json.dumps(self.responses.pop(0))}}]
        }

    def raw_payload(self, response):
        return {"provider": "fixture", "model": "fixture", "response": response}


def formal_evidence(value):
    """Verify derived report views, then compare their complete source evidence."""
    if isinstance(value, dict):
        result = {key: formal_evidence(item) for key, item in value.items()}
        if "sample_id" in result and "assets" in result:
            # Phase files are compared byte-for-byte separately below.
            for key in SAMPLE_METADATA_FIELDS:
                result.pop(key, None)
            assert result.pop("asset_count") == len(result["assets"])
            if "revealed_asset_ids" in result:
                assert result.pop("revealed_asset_ids") == [
                    asset["asset_id"]
                    for asset in result["assets"]
                    if asset.get("status") == "revealed"
                ]
            if "candidate_asset_ids" in result:
                assert result.pop("candidate_asset_ids") == [
                    asset["asset_id"] for asset in result["assets"]
                    if asset.get("status") == "stable_failure_candidate"
                ]
        if "repair_classification" in result:
            from probe.python.run.repair import repair_disposition

            assert result.pop("repair_classification") == repair_disposition(
                result.get("latest", result.get("buggy"))
            )
        if "semantic_fingerprint" in result and ("buggy" in result or "latest" in result):
            for key in ASSET_EXPLANATION_FIELDS:
                result.pop(key)
        if "fixed_failure_kind" in result:
            from probe.python.run.reporting import validation_failure_kind

            assert result.pop("fixed_failure_kind") == validation_failure_kind(
                result["fixed"]
            )
        if "use_minimized" in result and "called" in result:
            if "attempt_count" in result:
                assert result.pop("attempt_count") == len(
                    result.get("attempts", [result])
                )
            if "preserve_retry_count" in result:
                assert result.pop("preserve_retry_count") == 1
                assert len(result["attempts"]) == 2
            result.pop("parse_error_count", None)
        for key in ("harness_repair", "contract_agnostic_repair"):
            if key in result:
                result[key] = repair_evidence(result[key])
        if "buggy_only_failed_nodeids" in result:

            def failed_ids(revision):
                ids = result[revision].get("failed_nodeids", [])
                return (
                    {item for item in ids if isinstance(item, str)}
                    if isinstance(ids, list)
                    else set()
                )

            assert result.pop("buggy_only_failed_nodeids") == sorted(
                failed_ids("buggy") - failed_ids("fixed")
            )
        if {"required_runs", "runs", "stable"} <= result.keys():
            for run in result["runs"]:
                run.pop("buggy_failure_fingerprint", None)
        if "latest" in result and "initial_failure_fingerprint" in result.get("confirmation", {}):
            from probe.python.run.discovery import failure_fingerprint

            # Migrate only digest representation; still compare every stability decision.
            confirmation = result["confirmation"]
            confirmation["initial_failure_fingerprint"] = failure_fingerprint(result["latest"])
            for run in confirmation["runs"]:
                run["failure_fingerprint"] = failure_fingerprint(run["latest"])
        if "fixed_variants" in result:
            variants = result["fixed_variants"]
            assert result.pop("original_variant") == variants[0]
            revealed = [variant for variant in variants if variant["bug_revealed"]]
            if revealed:
                assert result.pop("revealed_variants") == revealed
                assert result.pop("revealed_variant_ids") == [
                    variant["variant_id"] for variant in revealed
                ]
                assert result.pop("revealed_asset_ids") == sorted(
                    {variant["asset_id"] for variant in revealed}
                )
        return result
    if isinstance(value, (list, tuple)):
        return type(value)(formal_evidence(item) for item in value)
    return value


def fixture(tmp_path, *, second_target=False):
    roots = {}
    for kind, increment in (("buggy", 1), ("fixed", 2)):
        root = tmp_path / kind
        root.mkdir()
        (root / "arithmetic.py").write_text(
            f'def advance(value):\n    """Advance by two."""\n    return value + {increment}\n'
            + ("\ndef double(value):\n    return value * 2\n" if second_target else "")
        )
        (root / "pytest.ini").write_text("[pytest]\n")
        roots[kind] = root
    case = {
        "case_id": "arithmetic",
        "revisions": {"buggy": "before", "fixed": "after"},
        "patch_targets": {
            "target_units": [
                {
                    "unit_id": "u1",
                    "filepath": "arithmetic.py",
                    "qualname": "advance",
                    "kind": "function",
                    "start_line": 1,
                    "end_line": 3,
                }
            ]
        },
    }
    if second_target:
        case["patch_targets"]["target_units"].append(
            {
                "unit_id": "u2",
                "filepath": "arithmetic.py",
                "qualname": "double",
                "kind": "function",
                "start_line": 5,
                "end_line": 6,
            }
        )
    packet = build_target_packet(
        project="fixture",
        strategy="target_probe_ldh",
        project_root=roots["buggy"],
        target_units=case["patch_targets"]["target_units"],
    )
    entry = packet["public_target_routes"]["targets"][0]["entrypoints"][0][
        "entrypoint_id"
    ]
    boundary = {
        "boundary_id": "boundary-001",
        "target_unit_ids": ["u1"],
        "route": {"entrypoint_id": entry},
        "probe": {
            "test_intent": "advance by two",
            "activation_conditions": ["call advance with zero"],
        },
        "invariant": {
            "independent_oracle": "zero advances to two",
            "supporting_evidence": "public docstring",
            "expected_observation": "two",
            "oracle_mode": "assertion",
        },
        "oracle_family": "arithmetic increment",
        "novelty_from_prior": "first attempt",
        "bug_hypothesis": "incorrect increment",
    }
    plan = {"boundary_plan": [boundary], "context_requests": []}
    asset = {
        "asset_id": "asset-001",
        "boundary_id": "boundary-001",
        "input_construction": "call with zero",
        "observable_oracle": "public return is two",
        "primary_oracle": "public result equality",
        "mocking_plan": "none",
        "test_file": "tests/generated/benchmarkbr/test_advance.py",
        "append_code": "from arithmetic import advance\n\ndef test_advance():\n    assert advance(0) == 2\n",
    }
    return roots, case, packet, plan, asset


def options(**extra):
    return TargetProbeRunOptions(
        model="fixture",
        env_file=None,
        strategy="target_probe_ldh",
        direct_samples=1,
        samples=0,
        soft_samples=0,
        minimize_buggy_failures_per_sample=0,
        case_time_budget_seconds=60,
        **extra,
    )


@pytest.mark.parametrize("renamed", [False, True])
@pytest.mark.parametrize("metadata", [{}, {"record": {}}, {"record": {"called": True}}])
def test_canonical_result_metadata_matches_formal(tmp_path, renamed, metadata):
    if not os.environ.get("PROBE_FORMAL_ROOT"):
        pytest.skip("set PROBE_FORMAL_ROOT to compare with the formal implementation")
    import common

    common.__path__.append(str(Path(os.environ["PROBE_FORMAL_ROOT"]) / "src/common"))
    from common.test_augment.python.run.candidate import asset_result_row as formal
    from common.test_augment.python.models import ProbeAsset as FormalProbeAsset
    from probe.python.prompt.proposal import parse_probe_plan, parse_proposal_partial
    from probe.python.run.candidate import asset_result_row
    from probe.python.run.generation import packet_public_entrypoints
    from probe.python.run.session import AssetValidationState

    _, _, packet, plan, raw = fixture(tmp_path)
    raw["unexpected_metadata"] = "discarded by parsing"
    parsed_plan, _ = parse_probe_plan(plan)
    proposal, _ = parse_proposal_partial(
        {"assets": [raw]},
        canonical_plan=parsed_plan,
        public_entrypoints=packet_public_entrypoints(packet),
    )
    asset = proposal.assets[0]
    original = replace(asset, asset_id="original") if renamed else asset
    snapshot = asset.to_dict()
    buggy = {"summary": {"status": "assertion_failed", "passed": False}}
    state = AssetValidationState(asset, tmp_path / "proposal.json", tmp_path, buggy)
    kwargs = dict(
        minimization=metadata,
        original_asset=original,
        harness_repair=metadata,
    )
    actual = asset_result_row(state, **kwargs)
    from probe.python.run.repair import repair_disposition

    expected = formal(
        FormalProbeAsset(**snapshot),
        state.proposal_path,
        buggy,
        **kwargs,
        repair_classification=repair_disposition(buggy["summary"]),
    )
    classification = expected.pop("repair_classification")
    assert classification == repair_disposition(actual["buggy"])
    expected_ledger = prior_attempt_ledger([{"assets": [expected]}])
    for key in ASSET_EXPLANATION_FIELDS:
        assert expected.pop(key) == snapshot[key]
    assert actual == expected
    assert asset.to_dict() == snapshot
    assert not (
        {"append_code", "mocking_plan", "unexpected_metadata"} | ASSET_EXPLANATION_FIELDS
    ) & actual.keys()
    assert prior_attempt_ledger([{"assets": [actual]}]) == expected_ledger


@pytest.mark.parametrize(
    "buggy_ids,fixed_ids",
    [
        ([], []),
        (["z", "a", "a", "shared"], ["shared", "fixed"]),
        (["same"], ["same"]),
        (["a", 1, None], None),
        (("tuple",), ["fixed"]),
    ],
)
@pytest.mark.parametrize("fixed_passed", [False, True])
def test_paired_failure_ids_retain_source_evidence(
    tmp_path, buggy_ids, fixed_ids, fixed_passed
):
    if not os.environ.get("PROBE_FORMAL_ROOT"):
        pytest.skip("set PROBE_FORMAL_ROOT to compare with the formal implementation")
    import common

    common.__path__.append(str(Path(os.environ["PROBE_FORMAL_ROOT"]) / "src/common"))
    from common.test_augment.python.run.candidate import fixed_variant_record as formal
    from probe.python.run.candidate import fixed_variant_record

    buggy = {"status": "assertion_failed", "failed_nodeids": buggy_ids}
    fixed = {
        "status": "passed" if fixed_passed else "assertion_failed",
        "failed_nodeids": fixed_ids,
    }
    state = SimpleNamespace(
        asset=SimpleNamespace(asset_id="a", test_file="tests/generated/test_a.py"),
        proposal_path=tmp_path / "proposal.json",
        buggy={"summary": buggy},
    )
    original = copy.deepcopy((buggy, fixed))
    actual = fixed_variant_record("base", state, {"summary": fixed})
    expected = formal("base", state, {"summary": fixed})
    assert actual == formal_evidence(expected)
    assert "buggy_only_failed_nodeids" not in actual
    assert (actual["buggy"], actual["fixed"]) == original
    assert (buggy, fixed) == original


@pytest.mark.parametrize("count", [1, 3])
@pytest.mark.parametrize("changed_outcome", [None, "buggy", "fixed"])
def test_confirmation_uses_revision_outcomes(tmp_path, count, changed_outcome):
    if not os.environ.get("PROBE_FORMAL_ROOT"):
        pytest.skip("set PROBE_FORMAL_ROOT to compare with the formal implementation")
    import common

    common.__path__.append(str(Path(os.environ["PROBE_FORMAL_ROOT"]) / "src/common"))
    from common.test_augment.python.run.candidate import (
        confirm_reveal_candidate as formal,
    )
    from probe.python.run.candidate import confirm_reveal_candidate

    state = SimpleNamespace(
        asset=object(), proposal_path=tmp_path / "proposal.json", sample_dir=tmp_path
    )
    results = []
    for confirm in (confirm_reveal_candidate, formal):
        calls = []

        def validate(**kwargs):
            calls.append(kwargs)
            attempt = (len(calls) + 1) // 2
            passed = kwargs["revision_kind"] == "fixed"
            if attempt == count and kwargs["revision_kind"] == changed_outcome:
                passed = not passed
            return {
                "summary": {
                    "passed": passed,
                    "status": "passed" if passed else "assertion_failed",
                    "failed_nodeids": [] if passed else [f"test.py::case_{attempt}"],
                    "failure_excerpt": "" if passed else f"assertion {attempt}",
                }
            }

        runtime = SimpleNamespace(
            options=SimpleNamespace(reveal_confirmation_runs=count),
            validation=SimpleNamespace(run=validate),
        )
        results.append((confirm(runtime=runtime, state=state, variant="base"), calls))
    actual, calls = results[0]
    assert (actual, calls) == formal_evidence(results[1])
    assert len(calls) == count * 2
    assert actual["stable"] is (changed_outcome is None)
    assert [run["buggy"]["failure_excerpt"] for run in actual["runs"][:-1]] == [
        f"assertion {attempt}" for attempt in range(1, count)
    ]


class ScriptedValidation:
    def __init__(self, scenario):
        self.scenario = scenario
        self.calls = []

    def run(self, revision_kind, proposal, proposal_path, sample_dir):
        self.calls.append((revision_kind, proposal.asset_id, proposal.append_code))
        if (
            self.scenario == "repair_validation_error"
            and Path(sample_dir).name.startswith(
                ("harness-repair-", "contract-agnostic-repair-")
            )
        ) or (
            self.scenario == "minimize_validation_error"
            and Path(sample_dir).name == "minimized"
        ):
            raise RuntimeError("fixture validation failure")
        count = sum(kind == revision_kind for kind, _, _ in self.calls)
        passed = revision_kind == "fixed"
        status = "passed" if passed else "assertion_failed"
        if self.scenario == "both_fail":
            passed, status = False, "assertion_failed"
        elif self.scenario == "unstable" and revision_kind != "fixed" and count > 1:
            passed, status = True, "passed"
        elif self.scenario == "nonassertion" and revision_kind != "fixed":
            status = "needs_repair"
        elif (
            self.scenario.startswith("repair")
            and "missing_name" in proposal.append_code
        ):
            passed, status = False, "needs_repair"
        if (
            self.scenario.startswith("minimize_preserve")
            and revision_kind != "fixed"
            and Path(sample_dir).name == "minimized"
            and (
                "minimization-preserve-001" not in Path(sample_dir).parts
                or self.scenario.endswith("lost")
            )
        ):
            passed, status = True, "passed"
        summary = {
            "passed": passed,
            "status": status,
            "phase": "pytest",
            "exit_code": 0 if passed else 1,
            "timed_out": False,
            "failed_nodeids": [] if passed else [proposal.test_file + "::test_advance"],
            "failure_excerpt": ""
            if passed
            else "ImportError: missing_name"
            if status == "needs_repair"
            else "AssertionError: 1 != 2",
        }
        return {"summary": summary, "result": {"evidence": summary}, "materialized": {}}


@pytest.mark.parametrize(
    "scenario,expected,strategy",
    [
        (scenario, expected, strategy)
        for scenario, expected in [
            ("stable", True),
            ("unstable", False),
            ("both_fail", False),
            ("nonassertion", True),
            ("repair_direct", True),
            ("repair_context", True),
            ("repair_retain", False),
            ("repair_disabled", False),
            ("repair_budget_exhausted", False),
            ("repair_extra", True),
            ("repair_twice", True),
            ("repair_invalid_between", True),
            ("repair_twice_minimize", True),
            ("repair_then_retain", False),
            ("repair_then_invalid", False),
            ("repair_validation_error", False),
            ("repair_boundary_switch", False),
            ("repair_target_override", True),
            ("initial_context", True),
            ("minimize", True),
            ("minimize_preserve", True),
            ("minimize_preserve_lost", True),
            ("minimize_invalid", True),
            ("minimize_extra", True),
            ("minimize_validation_error", False),
            ("minimize_boundary_switch", True),
            ("minimize_target_override", True),
        ]
        for strategy in ("target_probe_ldh", "target_probe_contract_agnostic")
        if strategy == "target_probe_ldh"
        or scenario not in {"repair_context", "initial_context"}
    ],
)
@pytest.mark.parametrize("discovery", [False, True])
def test_candidate_outcomes(tmp_path, monkeypatch, scenario, expected, strategy, discovery):
    if discovery and scenario == "nonassertion":
        pytest.skip("structured discovery exceptions are covered separately")
    mode = "single_revision_discovery" if discovery else "paired_reveal"
    if discovery and scenario == "both_fail":
        expected = True
    roots, case, packet, plan, asset = fixture(
        tmp_path, second_target=scenario.endswith("boundary_switch")
    )
    packet["strategy"] = strategy
    packet["evaluation_mode"] = mode
    repair_key = (
        "harness_repair"
        if strategy == "target_probe_ldh"
        else "contract_agnostic_repair"
    )
    repair_budget = 0 if scenario == "repair_budget_exhausted" else 1
    if scenario.endswith("boundary_switch"):
        boundary = copy.deepcopy(plan["boundary_plan"][0])
        boundary.update(boundary_id="boundary-002", target_unit_ids=["u2"])
        boundary["route"]["entrypoint_id"] = packet["public_target_routes"]["targets"][
            1
        ]["entrypoints"][0]["entrypoint_id"]
        plan["boundary_plan"].append(boundary)
    if scenario == "initial_context":
        plan["context_requests"] = [
            {
                "kind": "function_definition",
                "filepath": "arithmetic.py",
                "qualname": "advance",
                "reason": "inspect contract",
            }
        ]
    original = (
        {
            **asset,
            "append_code": asset["append_code"].replace(
                "import advance", "import missing_name"
            ),
        }
        if scenario.startswith("repair")
        else asset
    )
    responses = [plan, {"assets": [original]}]
    if scenario == "repair_context":
        responses.append(
            {
                "action": "request_context",
                "diagnosis": "wrong import",
                "requests": [
                    {
                        "kind": "module_context",
                        "filepath": "arithmetic.py",
                        "reason": "check public name",
                    }
                ],
            }
        )
        responses.append({"assets": [asset]})
    elif scenario.endswith(("boundary_switch", "target_override")):
        changed = {
            **asset,
            **(
                {"boundary_id": "boundary-002"}
                if scenario.endswith("boundary_switch")
                else {"target_unit_ids": ["unknown"]}
            ),
        }
        responses.append(
            {
                "assets": [changed],
                **({"action": "repair"} if scenario.startswith("repair") else {}),
            }
        )
    elif scenario in {"repair_direct", "repair_extra", "repair_validation_error"}:
        responses.append(
            {
                "action": "repair",
                "diagnosis": "wrong import",
                "assets": [asset] * (2 if scenario == "repair_extra" else 1),
            }
        )
    elif scenario in {
        "repair_twice", "repair_then_retain", "repair_then_invalid",
        "repair_invalid_between", "repair_twice_minimize",
    }:
        responses.append(
            {
                "action": "repair",
                "assets": [{
                    **original,
                    "asset_id": "attempt-1",
                    "append_code": original["append_code"] + "\n# first repair\n",
                }],
            }
        )
        if scenario == "repair_invalid_between":
            responses.append({"action": "repair", "assets": [{}]})
        responses.append(
            {"action": "repair", "assets": [{**asset, "asset_id": "attempt-2"}]}
            if scenario in {"repair_twice", "repair_invalid_between", "repair_twice_minimize"}
            else {"action": "retain_original"}
            if scenario == "repair_then_retain"
            else {"action": "repair", "assets": [{}]}
        )
        if scenario == "repair_twice_minimize":
            responses.append({"assets": [{**asset, "asset_id": "minimized"}]})
    elif scenario == "repair_retain":
        responses.append(
            {"action": "retain_original", "diagnosis": "retain original evidence"}
        )
    elif scenario == "minimize_invalid":
        responses.append({"assets": []})
    elif scenario.startswith("minimize"):
        responses.append(
            {"assets": [asset] * (2 if scenario == "minimize_extra" else 1)}
        )
        if scenario.startswith("minimize_preserve"):
            responses.append({"assets": [asset]})
    original_responses = copy.deepcopy(responses)
    original_packet = copy.deepcopy(packet)
    model = FixedModel(responses)
    validation = ScriptedValidation(scenario)
    runtime = TargetProbeRuntime(
        manifest={
            "case_id": case["case_id"],
            "evaluation_mode": mode,
            "source_roots": ["arithmetic.py"],
            f"{'latest' if discovery else 'buggy'}_checkout": {"path": str(roots["buggy"])},
        },
        options=replace(
            options(),
            evaluation_mode=mode,
            strategy=strategy,
            minimize_buggy_failures_per_sample=int(
                scenario.startswith("minimize") or scenario == "repair_twice_minimize"
            ),
            harness_repair_attempts=3
            if scenario == "repair_invalid_between"
            else 2
            if scenario in {
                "repair_twice", "repair_then_retain", "repair_then_invalid",
                "repair_twice_minimize",
            }
            else int(scenario != "repair_disabled"),
        ),
        model=model,
        validation=validation,
    )
    row = run_target_sample(
        runtime=runtime,
        packet=packet,
        sample_id="direct-001",
        sample_dir=tmp_path / "samples/direct-001",
        prior_attempts=[],
        prompt_style="direct",
        harness_repair_budget=repair_budget,
    )
    assert row.get("stable_failure_candidate" if discovery else "bug_revealed", False) is expected, row
    if discovery:
        assert all(call[0] == "latest" for call in validation.calls)
        assert all("fixed" not in result and "buggy" not in result for result in row["assets"])
    assert not SAMPLE_METADATA_FIELDS & row.keys()
    assert not {"asset_count", "revealed_asset_ids"} & row.keys()
    for result in row["assets"]:
        assert "repair_classification" not in result
        minimized = result.get("minimization", {})
        for attempt in [minimized, *minimized.get("attempts", [])]:
            assert not {
                "attempt_count", "preserve_retry_count", "parse_error_count"
            } & attempt.keys()
    assert not model.responses
    if scenario in {"repair_disabled", "repair_budget_exhausted"}:
        assert row["assets"][0][repair_key]["called"] is False
        assert len(model.prompts) == 2
    repair = row["assets"][0].get(repair_key, {})
    if repair.get("called"):
        assert set(repair) == {"called", "attempts"}
        for index, attempt in enumerate(repair["attempts"], 1):
            assert attempt["attempt"] == index
            assert not REPAIR_DERIVED_FIELDS & attempt.keys()
        if scenario in {
            "repair_twice", "repair_then_retain", "repair_then_invalid",
            "repair_twice_minimize",
        }:
            assert len(repair["attempts"]) == 2
        if scenario == "repair_invalid_between":
            assert len(repair["attempts"]) == 3
            assert "error" in repair["attempts"][1]
            assert "first repair" in model.prompts[3]
            assert "first repair" in model.prompts[4]
        for attempt in repair["attempts"]:
            if "sample_dir" in attempt:
                assert Path(attempt["sample_dir"]).parent.name == asset["asset_id"]
    if expected and not discovery:
        successful = row["assets"][0]
        revealed = [v for v in successful["fixed_variants"] if v["bug_revealed"]]
        assert revealed[0]["confirmation"]["stable"]
        for variant in revealed:
            for run in variant["confirmation"]["runs"]:
                assert set(run) == {"attempt", "passed", "buggy", "fixed"}
    if scenario == "repair_context":
        attempt = repair["attempts"][0]
        decision = json.loads(Path(attempt["context_request_path"]).read_text())
        context = json.loads(Path(attempt["retrieved_context_path"]).read_text())
        assert decision["action"] == "request_context"
        assert len(context["requested_context"]["requests"]) == 1
        assert context["requested_context"]["requests"][0]["status"] == "found"
        assert "def advance" in model.prompts[-1]
    if scenario == "initial_context":
        assert "def advance" in model.prompts[1]
    if scenario == "minimize":
        assert row["assets"][0]["minimization"]["use_minimized"]
    if scenario == "repair_twice_minimize":
        result = row["assets"][0]
        assert result["asset_id"] == "minimized"
        if not discovery:
            assert [v["variant"] for v in result["fixed_variants"]] == [
                "base", "repaired", "minimized",
            ]
        assert Path(result["proposal_path"]).parent == (
            Path(repair["attempts"][-1]["sample_dir"]) / "minimized"
        )
    if scenario.endswith("boundary_switch"):
        stage = repair_key if scenario.startswith("repair") else "minimization"
        record = row["assets"][0][stage]
        if scenario.startswith("repair"):
            record = record["attempts"][-1]
        assert "boundary_id" in record["error"]["message"]
    if scenario.startswith("minimize_preserve"):
        record = row["assets"][0]["minimization"]
        assert len(record["attempts"]) == 2
        assert record["use_minimized"] is (scenario == "minimize_preserve")
    if os.environ.get("PROBE_FORMAL_ROOT"):
        from test_compaction import formal_prompts_without_test_command, formal_run_options
        import common

        formal_prompts_without_test_command(monkeypatch)
        common.__path__.append(
            str(Path(os.environ["PROBE_FORMAL_ROOT"]) / "src/common")
        )
        from common.test_augment.python.run.workflow import (
            run_target_sample as formal_sample,
        )

        formal_model = FixedModel(original_responses)
        formal_validation = ScriptedValidation(scenario)
        formal_runtime = SimpleNamespace(
            manifest=runtime.manifest,
            options=formal_run_options(runtime.options),
            model=formal_model,
            validation=formal_validation,
        )
        sample_dir = tmp_path / "samples/direct-001"

        def outputs():
            return {
                p.relative_to(sample_dir): json.loads(p.read_bytes())
                if p.name == "result.json"
                else p.read_bytes()
                for p in sample_dir.rglob("*")
                if p.is_file()
            }

        saved_outputs = outputs()
        shutil.rmtree(sample_dir)
        formal_row = formal_sample(
            runtime=formal_runtime,
            packet=original_packet,
            sample_id="direct-001",
            sample_dir=tmp_path / "samples/direct-001",
            prior_attempts=[],
            prompt_style="direct",
            harness_repair_budget=repair_budget,
        )
        assert formal_evidence(formal_row) == row
        assert prior_attempt_ledger([row], evaluation_mode=mode) == prior_attempt_ledger([formal_row], evaluation_mode=mode)
        assert formal_model.prompts == model.prompts
        assert formal_validation.calls == validation.calls
        assert saved_outputs == formal_evidence(outputs())


def test_lanes_exhaustion_and_checkpoints(tmp_path):
    roots, case, packet, *_ = fixture(tmp_path)
    packet["target_units"].append({**packet["target_units"][0], "unit_id": "u2"})
    model = FixedModel(
        [{"boundary_plan": [], "exhausted_reason": "no additional family"}] * 3
    )
    runtime = TargetProbeRuntime(
        manifest={"case_id": case["case_id"]},
        options=replace(options(), samples=1, soft_samples=1),
        model=model,
        validation=ScriptedValidation("stable"),
    )
    rows = run_guided_case_samples(
        runtime=runtime, packet=packet, run_dir=tmp_path / "run"
    )
    assert [row["lane"] for row in rows] == [
        "direct_probe",
        "hard_core",
        "soft_extension",
    ]
    assert all(row["status"] == "exhausted" for row in rows)
    assert len(list((tmp_path / "run/samples").glob("*/result.json"))) == 3
    assert not runtime.validation.calls


@pytest.mark.parametrize(
    "scenario",
    [
        "forged_metadata",
        "redefined_plan",
        "unknown_boundary",
        "nonlist_plan",
        "nonobject_boundary",
        "missing_exhaustion",
        "exhausted",
        "unknown_target",
        "empty_targets",
        "duplicate_targets",
        "unknown_entrypoint",
        "mixed_assets",
        "plan_notes",
        "focused_target_override",
        "focused_plan_mismatch",
        "focused_joint_targets",
        "whole_target_alternative",
        "mixed_target_assets",
    ],
)
def test_canonical_plan_binding_matches_formal(tmp_path, monkeypatch, scenario):
    from test_compaction import (
        formal_module, formal_prompts_without_test_command, formal_run_options,
    )

    formal_prompts_without_test_command(monkeypatch)
    formal_sample = formal_module("workflow").run_target_sample
    roots, case, packet, plan, asset = fixture(tmp_path, second_target=True)
    implementation = {"assets": [asset]}
    boundary = plan["boundary_plan"][0]
    if scenario.startswith("focused"):
        packet["focus_target_unit_id"] = "u1"
    if scenario == "forged_metadata":
        asset.update(
            target_unit_ids=["unknown"],
            public_entrypoint_id="unknown",
            oracle_mode="crash",
            test_intent="different intent",
        )
    elif scenario == "redefined_plan":
        replacement = copy.deepcopy(boundary)
        replacement["target_unit_ids"] = ["u2"]
        replacement["probe"]["test_intent"] = "different intent"
        implementation["boundary_plan"] = [replacement]
    elif scenario == "nonlist_plan":
        plan["boundary_plan"] = {}
    elif scenario == "nonobject_boundary":
        plan["boundary_plan"] = ["not a boundary"]
    elif scenario in {"missing_exhaustion", "exhausted"}:
        plan["boundary_plan"] = []
        if scenario == "exhausted":
            plan["exhausted_reason"] = "no remaining boundary"
    elif scenario == "unknown_boundary":
        asset["boundary_id"] = "unknown"
    elif scenario in {"unknown_target", "empty_targets", "duplicate_targets"}:
        boundary["target_unit_ids"] = {
            "unknown_target": ["unknown"],
            "empty_targets": [],
            "duplicate_targets": ["u1", "u1"],
        }[scenario]
    elif scenario == "unknown_entrypoint":
        boundary["route"]["entrypoint_id"] = "unknown"
    elif scenario == "mixed_assets":
        implementation["assets"].append({**asset, "boundary_id": "unknown"})
    elif scenario == "plan_notes":
        plan["plan_notes"] = ["planning note"]
        implementation["plan_notes"] = ["implementation note"]
    elif scenario == "focused_target_override":
        asset["target_unit_ids"] = ["u2"]
    elif scenario == "focused_joint_targets":
        boundary["target_unit_ids"] = ["u1", "u2"]
    elif scenario in {
        "focused_plan_mismatch",
        "whole_target_alternative",
        "mixed_target_assets",
    }:
        other = copy.deepcopy(boundary)
        other["target_unit_ids"] = ["u2"]
        other["route"]["entrypoint_id"] = packet["public_target_routes"]["targets"][1][
            "entrypoints"
        ][0]["entrypoint_id"]
        if scenario == "mixed_target_assets":
            other["boundary_id"] = "boundary-002"
            plan["boundary_plan"].append(other)
            implementation["assets"].append(
                {**asset, "asset_id": "asset-002", "boundary_id": "boundary-002"}
            )
        else:
            plan["boundary_plan"] = [other]
            if scenario == "whole_target_alternative":
                packet["whole_target_pass"] = True
    sample_dir = tmp_path / "samples/direct-001"

    def run(sample):
        model = FixedModel(copy.deepcopy([plan, implementation]))
        validation = ScriptedValidation("stable")
        runtime = TargetProbeRuntime(
            manifest={
                "case_id": case["case_id"],
                "buggy_checkout": {"path": str(roots["buggy"])},
                "source_roots": ["arithmetic.py"],
            },
            options=formal_run_options(options()) if sample is formal_sample else options(),
            model=model,
            validation=validation,
        )
        try:
            result = sample(
                runtime=runtime,
                packet=copy.deepcopy(packet),
                sample_id="direct-001",
                sample_dir=sample_dir,
                prior_attempts=[],
                prompt_style="direct",
                harness_repair_budget=1,
            )
        except (Exception, SystemExit) as error:
            result = {"error": [type(error).__name__, str(error)]}
        outputs = {
            p.relative_to(sample_dir): p.read_bytes()
            for p in sample_dir.rglob("*")
            if p.is_file()
        }
        shutil.rmtree(sample_dir)
        return result, model.prompts, validation.calls, outputs

    actual = run(run_target_sample)
    assert actual == formal_evidence(run(formal_sample))
    if scenario in {
        "forged_metadata",
        "redefined_plan",
        "mixed_assets",
        "plan_notes",
        "focused_target_override",
        "focused_joint_targets",
        "whole_target_alternative",
        "mixed_target_assets",
    }:
        assert actual[0]["bug_revealed"]
        assert [row["target_unit_ids"] for row in actual[0]["assets"]] == (
            [["u1", "u2"]]
            if scenario == "focused_joint_targets"
            else [["u2"]]
            if scenario == "whole_target_alternative"
            else [["u1"], ["u2"]]
            if scenario == "mixed_target_assets"
            else [["u1"]]
        )
    elif scenario == "exhausted":
        assert actual[0]["status"] == "exhausted"
        assert actual[2] == []
    else:
        assert "error" in actual[0]
        assert actual[2] == []


@pytest.mark.parametrize(
    "phase", ["plan", "implementation", "repair-decision", "repair", "minimization"]
)
@pytest.mark.parametrize(
    "failure", ["model", "raw_payload", "prompt_write", "raw_write"]
)
def test_phase_failure_artifacts_match_formal(tmp_path, monkeypatch, phase, failure):
    from test_compaction import (
        formal_module, formal_prompts_without_test_command, formal_run_options,
    )

    formal_prompts_without_test_command(monkeypatch)
    formal_sample = formal_module("workflow").run_target_sample
    roots, _, packet, plan, asset = fixture(tmp_path)
    sample_dir = tmp_path / "samples/direct-001"
    directory = sample_dir
    original = copy.deepcopy(asset)
    responses = [plan, {"assets": [original]}]
    if phase.startswith("repair"):
        original["append_code"] = original["append_code"].replace(
            "import advance", "import missing_name"
        )
        responses.extend(
            [
                {
                    "action": "request_context",
                    "requests": [
                        {
                            "kind": "module_context",
                            "filepath": "arithmetic.py",
                            "reason": "inspect",
                        }
                    ],
                },
                {"assets": [asset]},
            ]
        )
        directory /= "assets/asset-001/harness-repair-001"
    elif phase == "minimization":
        responses.append({"assets": [asset]})
        directory /= "assets/asset-001"
    fail_call = {
        "plan": 1,
        "implementation": 2,
        "repair-decision": 3,
        "repair": 4,
        "minimization": 3,
    }[phase]

    class FailingModel(FixedModel):
        raised = False

        def complete(self, prompt):
            response = super().complete(prompt)
            if failure == "model" and len(self.prompts) == fail_call:
                raise TimeoutError("fixture model timeout")
            return response

        def raw_payload(self, response):
            if (
                failure == "raw_payload"
                and len(self.prompts) == fail_call
                and not self.raised
            ):
                self.raised = True
                raise ValueError("fixture response serialization failure")
            return super().raw_payload(response)

    def run(sample):
        if failure.endswith("_write"):
            suffix = "prompt.md" if failure == "prompt_write" else "raw.json"
            (directory / f"{phase}.{suffix}").mkdir(parents=True)
        model = FailingModel(copy.deepcopy(responses))
        validation = ScriptedValidation(
            "repair_context" if phase.startswith("repair") else "stable"
        )
        runtime = TargetProbeRuntime(
            manifest={
                "source_roots": ["arithmetic.py"],
                "buggy_checkout": {"path": str(roots["buggy"])},
            },
            options=replace(
                options(),
                minimize_buggy_failures_per_sample=int(phase == "minimization"),
            ),
            model=model,
            validation=validation,
        )
        if sample is formal_sample:
            runtime = replace(runtime, options=formal_run_options(runtime.options))
        try:
            result = sample(
                runtime=runtime,
                packet=copy.deepcopy(packet),
                sample_id="direct-001",
                sample_dir=sample_dir,
                prior_attempts=[],
                prompt_style="direct",
                harness_repair_budget=1,
            )
        except (Exception, SystemExit) as error:
            result = {"error": [type(error).__name__, str(error)]}
        outputs = {
            p.relative_to(sample_dir): p.read_bytes()
            for p in sample_dir.rglob("*")
            if p.is_file()
        }
        shutil.rmtree(sample_dir)
        return result, model.prompts, validation.calls, outputs

    actual = run(run_target_sample)
    assert actual == formal_evidence(run(formal_sample))
    assert len(actual[1]) == fail_call - int(failure == "prompt_write")


def test_real_pytest_isolated_and_confirmed(tmp_path):
    roots, case, packet, plan, asset = fixture(tmp_path)
    case["validation"] = {"test_command": ["unused-command-must-not-run"]}
    before = {
        kind: {
            p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()
        }
        for kind, root in roots.items()
    }
    model = FixedModel([plan, {"assets": [asset]}])
    run_dir = run_prepared_case(
        case=case,
        buggy_root=roots["buggy"],
        fixed_root=roots["fixed"],
        config={
            "project": "fixture",
            "source_roots": ["arithmetic.py"],
            "repository_url": "https://example.test/fixture",
        },
        options=options(),
        run_dir=tmp_path / "result",
        interpreters={kind: sys.executable for kind in roots},
        model=model,
    )
    assert not (run_dir / "summary.json").exists()
    row = json.loads((run_dir / "samples/direct-001/result.json").read_text())
    assert row["bug_revealed"], row
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["case_id"] == case["case_id"]
    assert manifest["evaluation_mode"] == row["evaluation_mode"] == "paired_reveal"
    assert not {"out_root", "run_id", "evaluation_mode"} & manifest["options"].keys()
    assert manifest["revisions"] == case["revisions"]
    assert manifest["repository_url"] == "https://example.test/fixture"
    packet = json.loads((run_dir / "packet.json").read_text())
    assert not {"case_id", "revision", "repository_url", "test_command"} & packet.keys()
    assert all('"test_command"' not in prompt for prompt in model.prompts)
    assert "packet_count" not in manifest
    for kind, root in roots.items():
        assert manifest[f"{kind}_checkout"] == {"path": str(root.resolve())}
    assert manifest["options"] == {
        key: str(value) if isinstance(value, Path) else value
        for key, value in vars(options()).items()
        if key != "evaluation_mode"
    }
    assert len(list(run_dir.rglob("buggy.pytest-report.json"))) >= 3
    assert not list(run_dir.rglob("validation-*"))
    for kind, root in roots.items():
        assert before[kind] == {
            p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()
        }


def test_output_must_not_overwrite_checkout(tmp_path):
    roots, case, *_ = fixture(tmp_path)
    with pytest.raises(ValueError, match="disjoint"):
        run_prepared_case(
            case=case,
            buggy_root=roots["buggy"],
            fixed_root=roots["fixed"],
            config={"project": "fixture"},
            options=options(),
            run_dir=roots["buggy"] / "output",
            interpreters={},
        )


@pytest.mark.parametrize("discovery", [False, True])
def test_budget_keeps_completed_checkpoint(tmp_path, discovery):
    from probe.python.run.deadline import CaseTimeBudgetExceeded

    roots, case, *_ = fixture(tmp_path)
    inputs = {"buggy_root": roots["buggy"], "fixed_root": roots["fixed"]}
    if discovery:
        inputs = {"latest_root": roots["buggy"]}
        case["revisions"] = {"latest": "frozen-latest"}
        case["target_units"] = case.pop("patch_targets")["target_units"]

    class ExpiringModel(FixedModel):
        def complete(self, prompt):
            if not self.responses:
                raise CaseTimeBudgetExceeded("fixture deadline")
            return super().complete(prompt)

    validation = SimpleNamespace(
        run=lambda **_: {"summary": {"passed": True, "status": "passed"}}
    )
    model = ExpiringModel(
        [{"boundary_plan": [], "exhausted_reason": "no additional family"}]
    )
    run_dir = run_prepared_case(
        case=case,
        **inputs,
        config={"project": "fixture", "source_roots": ["arithmetic.py"]},
        options=replace(options(), direct_samples=2),
        run_dir=tmp_path / "result",
        interpreters={},
        model=model,
        validation=validation,
    )
    assert not (run_dir / "summary.json").exists()
    progress = json.loads((run_dir / "progress.json").read_text())
    assert progress["error"] == {
        "type": "CaseTimeBudgetExceeded",
        "message": "fixture deadline",
    }
    assert len(progress["samples"]) == 1
    row = json.loads(Path(progress["samples"][0]["result_path"]).read_text())
    assert row["sample_id"] == "direct-001"
    assert row["status"] == "exhausted"
    assert row["evaluation_mode"] == ("single_revision_discovery" if discovery else "paired_reveal")
    assert set(progress["samples"][0]) == {"sample_id", "result_path"}


def test_validation_failure_cleans_workspace(tmp_path, monkeypatch):
    from probe.python.run import session

    roots, case, *_ = fixture(tmp_path)

    def fail(*args, **kwargs):
        raise RuntimeError("fixture runner failure")

    monkeypatch.setattr(session, "run_pytest_command", fail)
    validation = session.ValidationSession(case, roots, {"buggy": sys.executable}, 10)
    with pytest.raises(RuntimeError, match="fixture runner"):
        validation.run(
            "buggy",
            SimpleNamespace(
                test_file="tests/generated/test_fixture.py",
                append_code="def test_fixture():\n    assert True\n",
            ),
            tmp_path / "proposal.json",
            tmp_path / "output",
        )
    assert not list((tmp_path / "output").glob("validation-*"))
    assert json.loads((tmp_path / "output/buggy.materialized.json").read_text())[
        "cleanup"
    ]["removed"]


def test_traceback_context_resolves_a_disposable_source_frame(tmp_path):
    from probe.python.run.repair import repair_traceback_context
    from probe.python.run.session import ValidationSession

    roots, case, _, _, asset = fixture(tmp_path)
    (roots["buggy"] / "arithmetic.py").write_text(
        'def advance(value):\n    raise ValueError("fixture failure")\n'
    )
    result = ValidationSession(case, roots, {"buggy": sys.executable}, 10).run(
        "buggy",
        SimpleNamespace(**asset),
        tmp_path / "proposal.json",
        tmp_path / "output",
    )
    context = repair_traceback_context(
        {
            "buggy_checkout": {"path": str(roots["buggy"])},
            "source_roots": ["arithmetic.py"],
        },
        result["summary"],
    )
    assert context, result["summary"]
    assert any(item["filepath"] == "arithmetic.py" for item in context)
    assert "fixture failure" in json.dumps(context)
