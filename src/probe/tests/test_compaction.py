"""Differential checks for the paired-only orchestration and output helpers."""

from __future__ import annotations

import copy
import importlib
import io
import json
import os
import sys
from dataclasses import asdict, replace
from itertools import product
from pathlib import Path
from types import SimpleNamespace

import pytest

from formal_names import align_formal_names, install_formal_name_adapter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from probe.python.run import workflow
from probe.python.run.options import TargetProbeRunOptions, validate_run_options


@pytest.mark.parametrize("field", ["timeout", "model_timeout", "minimization_failure_excerpt_chars"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), 0, -1, True])
def test_invalid_execution_limits_are_rejected(field, value):
    options = TargetProbeRunOptions(model="fixture", env_file=None)
    with pytest.raises(ValueError, match=field):
        validate_run_options(replace(options, **{field: value}))


def test_excerpt_limit_is_integer_but_timeouts_accept_fractional_seconds():
    options = TargetProbeRunOptions(model="fixture", env_file=None)
    with pytest.raises(ValueError, match="minimization_failure_excerpt_chars"):
        validate_run_options(replace(options, minimization_failure_excerpt_chars=1.5))
    validate_run_options(replace(options, timeout=0.5, model_timeout=0.25))


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
@pytest.mark.parametrize("usage_kind", ["missing", "null", "detailed"])
def test_raw_model_usage_is_preserved(tmp_path, monkeypatch, provider, usage_kind):
    from probe.python.run import client
    from probe.python.run.options import validate_run_options
    from probe.python.run.session import ModelSession, complete_and_record

    options = TargetProbeRunOptions(
        model="fixture-model", provider=provider, env_file=None
    )
    validate_run_options(options)
    response = {
        "model": "fixture-model-snapshot",
        "choices": [{"message": {"content": "fixture"}}],
    }
    if usage_kind != "missing":
        response["usage"] = (
            None
            if usage_kind == "null"
            else {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
                "prompt_tokens_details": {"cached_tokens": 40},
                "completion_tokens_details": {"reasoning_tokens": 10},
            }
        )
    requests = []

    def open_request(request, timeout):
        requests.append(json.loads(request.data))
        return io.BytesIO(json.dumps(response).encode())

    monkeypatch.setattr(client.urllib.request, "urlopen", open_request)
    model = ModelSession(
        model=options.model,
        provider=provider,
        env={"LLM_API_KEY": "fixture"},
        timeout=120,
        retries=0,
    )
    raw_path = tmp_path / "implementation.raw.json"
    result = complete_and_record(SimpleNamespace(model=model), "fixture", raw_path)
    assert result == response
    assert json.loads(raw_path.read_text()) == {
        "provider": provider,
        "model": options.model,
        "response": response,
    }
    assert len(requests) == 1
    assert requests[0]["model"] == options.model
    assert "max_completion_tokens" not in requests[0]
    assert list(tmp_path.iterdir()) == [raw_path]


def formal_module(name, package="run"):
    root = os.environ.get("PROBE_FORMAL_ROOT")
    if not root:
        pytest.skip("set PROBE_FORMAL_ROOT to compare with the formal implementation")
    import common

    directory = str(Path(root) / "src/common")
    if directory not in common.__path__:
        common.__path__.append(directory)
    install_formal_name_adapter()
    return importlib.import_module(f"common.test_augment.python.{package}.{name}")


def test_formal_name_adapter_preserves_prompt_prose_and_behavior():
    source = '''TARGET_PROBE_LDCR_STRATEGY = "target_probe_ldcr"
current = asset.get("current", {})
return current_outcome_category(asset), "current_passed", current
"the current implementation; currently selected; LDCR-only"
'''
    assert align_formal_names(source) == '''TARGET_PROBE_LDH_STRATEGY = "target_probe_ldh"
current = asset.get("latest", {})
return latest_outcome_category(asset), "latest_passed", current
"the current implementation; currently selected; LDH-only"
'''


def formal_run_options(options, **extra):
    """Use the same workflow options for the formal reference runner."""
    return SimpleNamespace(**{**asdict(options), **extra})


@pytest.mark.parametrize("custom_root", [False, True])
@pytest.mark.parametrize("custom_run_id", [False, True])
def test_python_cli_resolves_output_without_redundant_options(
    tmp_path, monkeypatch, custom_root, custom_run_id
):
    from cli.runner import build_parser
    from probe.python import runner

    case_path = tmp_path / "case.json"
    case_path.write_text(json.dumps({"case_id": "fixture"}))
    argv = [
        "probe", "--project", "pr-agent", "--case-json", str(case_path),
        "--buggy-root", str(tmp_path / "buggy"),
        "--fixed-root", str(tmp_path / "fixed"), "--python-bin", sys.executable,
    ]
    if custom_root:
        argv.extend(["--out-root", str(tmp_path / "custom")])
    if custom_run_id:
        argv.extend(["--run-id", "chosen"])
    args = build_parser().parse_args(argv)
    monkeypatch.setattr(runner, "ARTIFACT_ROOT", tmp_path)
    monkeypatch.setattr(runner.time, "time_ns", lambda: 1234)
    calls = []

    def run(**kwargs):
        calls.append(kwargs)
        return kwargs["run_dir"]

    monkeypatch.setattr(runner, "run_prepared_case", run)
    output = runner.run_probe(args, {"project": "pr-agent"})
    expected_root = tmp_path / ("custom" if custom_root else "outputs/pr-agent/probe")
    assert output == expected_root / ("chosen" if custom_run_id else "fixture-1234")
    assert len(calls) == 1
    assert calls[0]["run_dir"] == output
    configured = calls[0]["options"]
    assert not {"out_root", "run_id"} & vars(configured).keys()
    assert configured.evaluation_mode == "paired_reveal"
    assert configured.direct_samples == 10
    assert configured.samples == 10
    assert configured.soft_samples == 2
    assert configured.minimization_preserve_attempts == 1


def formal_prompts_without_test_command(monkeypatch):
    """Apply the approved single-field prompt change to the reference renderer."""
    formal = formal_module("prompts", "prompt")
    workflow = formal_module("workflow")
    original = formal.prompt_packet

    def project(*args, **kwargs):
        payload = original(*args, **kwargs)
        payload.pop("test_command")
        return payload

    monkeypatch.setattr(formal, "prompt_packet", project)
    monkeypatch.setattr(workflow, "prompt_packet", project)
    return formal


def test_supported_strategies_and_removed_baseline(tmp_path):
    from cli.runner import build_parser
    from probe.python.run.options import TARGET_PROBE_STRATEGIES
    from probe.python.run.case import run_prepared_case

    assert TARGET_PROBE_STRATEGIES == {
        "target_probe_ldh",
        "target_probe_contract_agnostic",
    }
    options = TargetProbeRunOptions(model="fixture", env_file=None)
    assert options.strategy == "target_probe_ldh"
    parser = build_parser()
    args = [
        "probe",
        "--project",
        "pr-agent",
        "--case-json",
        "case.json",
        "--buggy-root",
        "buggy",
        "--fixed-root",
        "fixed",
    ]
    assert parser.parse_args(args).strategy == options.strategy
    with pytest.raises(SystemExit):
        parser.parse_args([*args, "--strategy", "target_probe_baseline"])
    with pytest.raises(SystemExit, match="unsupported target-probing strategy"):
        run_prepared_case(
            case={},
            config={},
            buggy_root=tmp_path / "buggy",
            fixed_root=tmp_path / "fixed",
            interpreters={},
            options=TargetProbeRunOptions(
                model="fixture",
                env_file=None,
                strategy="target_probe_baseline",
            ),
            run_dir=tmp_path / "output",
        )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("mode", ["paired_reveal", "single_revision_discovery"])
def test_prior_attempt_ledger_matches_formal(mode):
    from probe.python.run.generation import prior_attempt_ledger

    expected = formal_module("generation").prior_attempt_ledger
    base = {
        "target_unit_ids": ["second", "first"],
        "test_intent": "compare an arithmetic result",
        "input_construction": "zero",
        "primary_oracle": "equality",
        "oracle_family": " shared family ",
    }
    assets = [
        {**base, "asset_id": f"a{i}", ("latest" if mode == "single_revision_discovery" else "buggy"): summary}
        for i, summary in enumerate(
            [
                {"passed": True},
                {"status": "passed"},
                {"status": "assertion_failed"},
                {"status": "needs_repair"},
                {},
            ]
        )
    ]
    assets += [
        {**base, "status": "stable_failure_candidate", "stable_failure_candidate": True},
        {**base, "status": "unstable_failure", "latest": {"status": "assertion_failed"}},
        {**base, "oracle_family": "another family", "semantic_fingerprint": "known"},
        {**base, "status": "error", "semantic_fingerprint": "failed"},
        {**base, "oracle_family": "", "primary_oracle": "different equality"},
        {"status": "error"},
        {},
        assets[0],
    ]
    for reverse in (False, True):
        ordered = list(reversed(assets)) if reverse else assets
        for length in range(len(ordered) + 1):
            rows = [{"assets": [asset]} for asset in ordered[:length]]
            original = copy.deepcopy(rows)
            for limit in (-1, 0, 1, 2, 18):
                assert prior_attempt_ledger(rows, max_items=limit, evaluation_mode=mode) == expected(
                    rows, max_items=limit, evaluation_mode=mode
                )
                assert rows == original


@pytest.mark.parametrize(
    "strategy",
    ["target_probe_ldh", "target_probe_contract_agnostic"],
)
def test_strategy_context_and_repair_policy_match_formal(strategy):
    from probe.python.run.options import strategy_profile

    expected = formal_module("tracks").strategy_profile(strategy)
    actual = strategy_profile(strategy)
    assert actual.allow_context == expected.allow_plan_context
    assert actual.allow_context == expected.include_contract_context
    assert actual.repair_mode == expected.repair_mode
    assert actual.repair_key == expected.repair_key
    assert (actual.repair_mode == "harness") == (expected.guidance == "ldh")


def test_repair_attempt_records_preserve_history_and_current_state():
    from probe.python.run.repair import record_repair_attempt

    formal = formal_module("repair")
    attempts, expected_attempts = [], []
    records = [
        {
            "decision": "repair",
            "proposal_path": "first/proposal.json",
        },
        {"error": {"message": "invalid reply"}},
        {"decision": "repair", "proposal_path": "third/proposal.json"},
        {"decision": "retain_original"},
    ]
    for index, record in enumerate(records):
        original = copy.deepcopy(record)
        state = SimpleNamespace(asset=f"asset-{index}") if index in {0, 2} else None
        result = record_repair_attempt(record, attempts, state)
        expected_attempts.append(copy.deepcopy(record))
        grouped = formal.grouped_attempt_record(record, expected_attempts)
        assert result["record"] == {
            "called": True,
            "attempts": grouped.get("attempts", [original]),
        }
        assert grouped["attempt_count"] == len(result["record"]["attempts"])
        assert attempts == expected_attempts
        assert attempts[-1] is record
        assert record == original
        if state is None:
            assert "state" not in result
        else:
            assert result["state"] is state
        assert result["record"]["attempts"] is attempts


@pytest.mark.parametrize("encoded", [False, True])
@pytest.mark.parametrize("max_requests", [-1, 0, 1, 2])
def test_plan_records_preserve_serialization_and_error_priority(encoded, max_requests):
    from probe.python.prompt import proposal

    formal = formal_module("proposal", "prompt")
    boundary = {
        "boundary_id": "boundary-001",
        "target_unit_ids": ["u1"],
        "route": {"entrypoint_id": "entrypoint-001"},
        "probe": {"test_intent": "advance by two", "activation_conditions": ["zero"]},
        "invariant": {
            "independent_oracle": "public arithmetic contract",
            "supporting_evidence": "advance adds two",
            "expected_observation": "two",
            "oracle_mode": "assertion",
        },
        "bug_hypothesis": "advance adds one",
        "oracle_family": "addition",
        "novelty_from_prior": "first input",
    }
    base = {
        "boundary_plan": [boundary],
        "context_requests": [
            {"kind": "module_context", "filepath": "arithmetic.py", "reason": "setup"}
        ],
        "plan_notes": ["planning note"],
    }
    variants = [base]
    for key, values in {
        "boundary_plan": [None, [], {}, "invalid", [None], [boundary, boundary]],
        "context_requests": [None, [], {}, "invalid", [None], [{"kind": "unknown"}]],
        "plan_notes": [None, [], [" "], "invalid", [1], ["first", " second "]],
    }.items():
        missing = copy.deepcopy(base)
        del missing[key]
        variants.append(missing)
        variants.extend({**base, key: value} for value in values)
    for reason in [None, "", " complete ", 1]:
        for requests in [[], base["context_requests"]]:
            variants.append(
                {
                    "boundary_plan": [],
                    "exhausted_reason": reason,
                    "context_requests": requests,
                }
            )
    fields = [
        ("boundary_id",),
        ("target_unit_ids",),
        ("route",),
        ("probe",),
        ("invariant",),
        ("probe", "activation_conditions"),
        ("invariant", "independent_oracle"),
        ("invariant", "oracle_mode"),
        ("route", "entrypoint_id"),
        ("probe", "test_intent"),
        ("invariant", "supporting_evidence"),
        ("invariant", "expected_observation"),
        ("bug_hypothesis",),
        ("oracle_family",),
        ("novelty_from_prior",),
    ]
    for field in fields:
        for value in [None, "", " ", 0, False, [], {}, ["u1", "u1"], [1, {"k": 2}]]:
            data = copy.deepcopy(base)
            target = data["boundary_plan"][0]
            for key in field[:-1]:
                target = target[key]
            target[field[-1]] = value
            variants.append(data)
    # Competing invalid fields verify which error the workflow reports first.
    required_strings = fields[6:13]
    for start in range(len(required_strings)):
        data = copy.deepcopy(base)
        for field in required_strings[start:]:
            target = data["boundary_plan"][0]
            for key in field[:-1]:
                target = target[key]
            del target[field[-1]]
        variants.append(data)

    def observe(module, data):
        supplied = copy.deepcopy(data)
        content = f"```json\n{json.dumps(supplied)}\n```" if encoded else supplied
        try:
            plan, errors = module.parse_probe_plan(
                content, max_context_requests=max_requests
            )
            if module is formal:
                plan = plan.to_dict()
            result = {"plan": plan, "errors": errors}
        except (Exception, SystemExit) as error:
            result = {"error": [type(error).__name__, str(error)]}
        assert supplied == data
        return json.dumps(result)

    for data in variants:
        assert observe(proposal, data) == observe(formal, data), data


@pytest.mark.parametrize("label", ["asset_id", "boundary_id"])
def test_identifier_validation_preserves_limits_and_error_labels(label):
    from probe.python.prompt.proposal import validate_id

    expected = getattr(formal_module("proposal", "prompt"), f"validate_{label}")

    def observe(validate, value):
        try:
            return {"value": validate(value)}
        except (Exception, SystemExit) as exc:
            return {"error": (type(exc).__name__, str(exc))}

    values = [
        "a",
        "1",
        "A-_.0123",
        "a" * 81,
        "a" * 82,
        "",
        "a\n",
        "a\r\n",
        " a",
        "a ",
        ".a",
        "_a",
        "-a",
        "a/b",
        "a\\b",
        "a\0b",
        "\u00e9",
        1,
        None,
    ]
    for value in values:
        assert observe(lambda item: validate_id(item, label), value) == observe(
            expected, value
        )


@pytest.mark.parametrize("canonical", [False, True])
@pytest.mark.parametrize("notes", [None, [], [" note "]])
def test_proposal_boundary_records_match_formal(canonical, notes):
    from probe.python.prompt import proposal

    formal = formal_module("proposal", "prompt")
    boundary = {
        "boundary_id": "b1",
        "target_unit_ids": ["u1"],
        "route": {"entrypoint_id": "e1"},
        "probe": {"test_intent": "increment", "activation_conditions": "zero"},
        "invariant": {
            "independent_oracle": "arithmetic",
            "supporting_evidence": "addition",
            "expected_observation": "two",
            "oracle_mode": "assertion",
        },
        "bug_hypothesis": "incorrect increment",
    }
    data = {
        "boundary_plan": [boundary],
        "plan_notes": notes,
        "assets": [
            {
                "asset_id": "a1",
                "boundary_id": "b1",
                "test_file": "tests/generated/benchmarkbr/test_counter.py",
                "append_code": "def test_increment():\n    assert 1 + 1 == 2\n",
                "input_construction": "zero",
                "observable_oracle": "two",
                "primary_oracle": "addition",
            }
        ],
    }
    canonical_plan = formal.parse_probe_plan({"boundary_plan": [boundary]})[0].to_dict()
    if canonical:
        canonical_plan["boundary_plan"][0]["probe"]["test_intent"] = "canonical intent"
    original = copy.deepcopy(data)
    options = {
        "canonical_plan": canonical_plan if canonical else None,
        "public_entrypoints": [{"entrypoint_id": "e1"}],
    }
    actual, errors = proposal.parse_proposal_partial(data, **options)
    expected, expected_errors = formal.parse_proposal_partial(data, **options)
    assert json.dumps(actual.to_dict()) == json.dumps(expected.to_dict())
    assert errors == expected_errors
    assert data == original
    assert actual.assets[0].boundary.test_intent == (
        "canonical intent" if canonical else "increment"
    )

    asset = data["assets"][0]
    mixed = [
        asset,
        None,
        asset,
        {**asset, "asset_id": "bad", "append_code": "def ("},
        {**asset, "asset_id": "a2"},
    ]

    def capture(module, payload, **limits):
        try:
            result, errors = module.parse_proposal_partial(payload, **options, **limits)
            return json.dumps((result.to_dict(), errors))
        except (Exception, SystemExit) as exc:
            return type(exc).__name__, str(exc)

    for assets in ([], mixed, list(reversed(mixed))):
        payload = {**data, "assets": assets}
        before = copy.deepcopy(payload)
        for maximum, allow_empty in product((-1, 0, 1, 3, 20), (False, True)):
            limits = {"max_assets": maximum, "allow_empty_assets": allow_empty}
            assert capture(proposal, payload, **limits) == capture(
                formal, payload, **limits
            )
            assert payload == before


def test_result_aggregation_priority_matches_formal(tmp_path):
    from probe.python.run.reporting import aggregate_asset_rows

    formal = formal_module("reporting")
    statuses = ("revealed", "fixed_failed", "buggy_passed", "error", "unknown", None)
    base = {"sample_id": "s1", "status": "stale", "marker": "retained"}
    original = copy.deepcopy(base)
    for size in range(4):
        for combination in product(statuses, repeat=size):
            rows = [
                {"asset_id": f"a{index}", "status": status}
                for index, status in enumerate(combination)
            ]
            args = (base, tmp_path / "proposal.json", rows)
            actual = aggregate_asset_rows(*args)
            expected = formal.aggregate_asset_rows(*args)
            assert expected.pop("asset_count") == len(rows)
            if "revealed_asset_ids" in expected:
                assert expected.pop("revealed_asset_ids") == [
                    row["asset_id"] for row in rows if row["status"] == "revealed"
                ]
            assert json.dumps(actual) == json.dumps(expected)
            assert base == original
            assert actual["assets"] is rows


@pytest.mark.parametrize(
    "kind", ["timeout", "http_connection", "url", "retryable_http", "fatal_http"]
)
@pytest.mark.parametrize("failures", [1, 3])
def test_model_transport_retry_behavior_matches_formal(monkeypatch, kind, failures):
    from probe.python.run import client

    observed = []
    for module in (client, formal_module("client")):
        calls, sleeps, limits = [], [], []

        def open_request(request, timeout):
            calls.append((request.full_url, request.data, request.headers, timeout))
            if len(calls) <= failures:
                error = {
                    "timeout": TimeoutError("fixture timeout"),
                    "http_connection": module.http.client.HTTPException(
                        "fixture connection"
                    ),
                    "url": module.urllib.error.URLError("fixture url"),
                    "retryable_http": module.urllib.error.HTTPError(
                        "fixture",
                        429,
                        "retry",
                        {"Retry-After": "0.5"},
                        io.BytesIO(b"retry"),
                    ),
                    "fatal_http": module.urllib.error.HTTPError(
                        "fixture", 400, "invalid", {}, io.BytesIO(b"invalid")
                    ),
                }[kind]
                raise error
            return io.BytesIO(b'{"choices": []}')

        def limit(seconds=float("inf")):
            limits.append(seconds)
            return seconds

        with monkeypatch.context() as patch:
            patch.setattr(module.urllib.request, "urlopen", open_request)
            patch.setattr(module.time, "sleep", sleeps.append)
            patch.setattr(module, "limit_timeout", limit)
            try:
                result = module.chat_completion(
                    prompt="fixture",
                    model="fixture",
                    env={"OPENAI_API_KEY": "fixture"},
                    provider="openai",
                    retries=2,
                )
            except Exception as exc:
                result = {"error": (type(exc).__name__, str(exc))}
        observed.append((result, calls, sleeps, limits))
    assert observed[0] == observed[1]
    assert len(observed[0][1]) == (1 if kind == "fatal_http" else min(failures + 1, 3))


@pytest.mark.parametrize("count", [None, 0, 3, "4", -1])
def test_diagnostic_counts_and_truncation_match_formal(count):
    from probe.python.runtime.validate import structured_diagnostics

    formal = formal_module("validate", "runtime")
    for truncated in (None, False, True, 1):
        report = {"internal_errors": ["fixture"]}
        for key, records in (
            ("collected_count", "collected_nodeids"),
            ("test_report_count", "test_reports"),
            ("collection_report_count", "collection_reports"),
        ):
            report[key] = count
            report[records] = [{"outcome": "failed"}, {"outcome": "passed"}]
            report[f"{records}_truncated"] = truncated
        assert json.dumps(structured_diagnostics(report)) == json.dumps(
            formal.structured_diagnostics(report)
        )


@pytest.mark.parametrize("phase", ["plan", "repair"])
@pytest.mark.parametrize("limit", [0, 1, 2, 20])
def test_context_request_parsing_matches_formal(phase, limit):
    from probe.python.prompt import context_requests, proposal

    variants = [None, False, 0, "", "invalid", {}, []]
    items = [None, False, 1, "request", [], {}, {"kind": "unknown"}]
    for kind in (
        "module_context",
        "class_definition",
        "function_definition",
        "symbol_definition",
    ):
        for filepath in (None, "", "src/counter.py", "../outside.py", "/tmp/x.py"):
            items.append({"kind": kind, "filepath": filepath})
        items.extend(
            [
                {"kind": kind, "filepath": " src/counter.py ", "qualname": " Counter "},
                {"kind": kind, "filepath": 12, "qualname": 3, "reason": True},
            ]
        )
    variants.extend([item] for item in items)
    variants.extend([items, list(reversed(items))])

    def capture(parse, value):
        try:
            return {"result": parse(value)}
        except (Exception, SystemExit) as exc:
            return {"error": (type(exc).__name__, str(exc))}

    if phase == "plan":
        formal = formal_module("proposal", "prompt")
        actual = lambda value: proposal.parse_request_list(
            value, max_requests=limit, planning=True
        )
        expected = lambda value: formal.parse_plan_context_requests(
            value, max_context_requests=limit
        )
        for value in variants:
            assert capture(actual, value) == capture(expected, value)
    else:
        formal = formal_module("context_requests", "prompt")
        for value in variants:
            payload = {"requests": value}
            for wire in (
                payload,
                json.dumps(payload),
                f"```json\n{json.dumps(payload)}\n```",
            ):
                assert capture(
                    lambda data: context_requests.parse_context_requests(
                        data, max_requests=limit
                    ),
                    wire,
                ) == capture(
                    lambda data: formal.parse_context_requests(
                        data, max_requests=limit
                    ),
                    wire,
                )
            payload["action"] = "request_context"
            assert capture(
                lambda data: context_requests.parse_harness_repair_decision(
                    data, max_requests=limit
                ),
                payload,
            ) == capture(
                lambda data: formal.parse_harness_repair_decision(
                    data, max_requests=limit
                ),
                payload,
            )


def test_default_sandbox_profile_matches_formal(tmp_path, monkeypatch):
    from probe.python.runtime import validate

    formal = formal_module("validate", "runtime")
    monkeypatch.setattr(validate, "STUDY_SRC_ROOT", formal.STUDY_ROOT / "src")
    command = [sys.executable, "-m", "pytest"]
    kwargs = {"copy_root": tmp_path, "test_file": "tests/generated/probe.py"}
    assert validate.sandboxed_pytest_command(
        command, **kwargs
    ) == formal.sandboxed_pytest_command(command, **kwargs)


@pytest.mark.parametrize(
    "strategy",
    ["target_probe_ldh", "target_probe_contract_agnostic"],
)
@pytest.mark.parametrize("with_context", [False, True])
def test_all_rendered_prompts_match_formal(monkeypatch, strategy, with_context):
    from probe.python.prompt import prompts

    formal = formal_prompts_without_test_command(monkeypatch)
    packet = {
        "project": "fixture",
        "strategy": strategy,
        "target_units": [{"unit_id": "u1", "code": "value = '$max_assets'"}],
        "generated_test_roots": ["tests/generated/custom/"],
        "module_imports": [{"text": "import arithmetic"}],
        "focus_target_unit_id": "u1",
        "focus_sample_index": 1,
        "focus_total_target_units": 2,
        "whole_target_pass": True,
        "soft_sample_index": 1,
        "lane": "direct_probe",
        "fixed_source": "PRIVATE_FIXED_SOURCE",
        "retrieved_context": {"requests": [{"status": "found", "code": "x = 1"}]}
        if with_context
        else {"requests": []},
    }
    prior = [{"buggy_outcomes": ["needs_repair"], "semantic_fingerprint": "internal"}]
    for direct in (False, True):
        for stage in ("plan", "implementation"):
            name = f"render_target_probe_{stage}_prompt"
            formal_name = (
                f"render_target_probe_{'direct_' if direct else ''}{stage}_prompt"
            )
            kwargs = {"prior_attempts": prior}
            if stage == "implementation":
                kwargs.update(plan={"boundary_plan": []}, max_assets=0)
            actual = getattr(prompts, name)(packet, direct=direct, **kwargs)
            assert actual == getattr(formal, formal_name)(packet, **kwargs)
            assert "PRIVATE_FIXED_SOURCE" not in actual
            if strategy == "target_probe_ldh":
                default_packet = {
                    key: value for key, value in packet.items() if key != "strategy"
                }
                assert (
                    getattr(prompts, name)(default_packet, direct=direct, **kwargs)
                    == actual
                )
    common = {
        "asset": {"append_code": "assert value"},
        "buggy_summary": {"status": "needs_repair"},
    }
    calls = {
        "render_target_probe_minimize_prompt": {
            **common,
            "retry_context": {"previous_buggy_status": "buggy_passed"}
            if with_context
            else None,
        },
        "render_target_harness_repair_context_request_prompt": {
            **common,
            "plan": {},
            "traceback_context": [],
            "max_context_requests": 2 if with_context else 0,
        },
        "render_target_harness_repair_prompt": {
            **common,
            "plan": {},
            "traceback_context": [],
            "repair_context": {},
        },
        "render_target_contract_agnostic_repair_prompt": {**common, "plan": {}},
    }
    for name, kwargs in calls.items():
        assert getattr(prompts, name)(packet, **kwargs) == getattr(formal, name)(
            packet, **kwargs
        )


@pytest.mark.parametrize("budgets", [(2, 2, 2), (0, 2, 1), (0, 0, 2), (0, 0, 0)])
@pytest.mark.parametrize("scenario", ["exhausted", "revealed", "mixed", "error"])
@pytest.mark.parametrize("limit", [1, 2, 3])
@pytest.mark.parametrize("unit_count", [1, 2])
@pytest.mark.parametrize(
    "strategy", ["target_probe_ldh", "target_probe_contract_agnostic"]
)
@pytest.mark.parametrize("mode", ["paired_reveal", "single_revision_discovery"])
def test_scheduler_matches_formal(
    tmp_path, monkeypatch, budgets, scenario, limit, unit_count, strategy, mode
):
    formal = formal_module("workflow")
    configured = TargetProbeRunOptions(
        model="fixture",
        env_file=None,
        strategy=strategy,
        evaluation_mode=mode,
        direct_samples=budgets[0],
        samples=budgets[1],
        soft_samples=budgets[2],
        max_reveal_candidates=limit,
    )
    packet = {
        "strategy": configured.strategy,
        "evaluation_mode": mode,
        "target_units": [
            {
                "unit_id": name,
                "filepath": "arithmetic.py",
                "qualname": name,
                "kind": "function",
            }
            for name in ("u1", "u2")[:unit_count]
        ],
    }
    observed = []
    for module in (workflow, formal):
        options = (
            formal_run_options(configured, out_root=tmp_path, resume=False, min_free_gib=0)
            if module is formal
            else configured
        )
        calls = []

        def sample(**kwargs):
            if module is workflow:
                assert callable(kwargs.pop("on_progress"))
            calls.append(
                {
                    key: copy.deepcopy(value)
                    for key, value in kwargs.items()
                    if key != "runtime"
                }
            )
            if scenario == "error":
                raise ValueError("fixture error")
            revealed = scenario == "revealed" or (
                scenario == "mixed" and kwargs["sample_id"].endswith("001")
            )
            return {
                "sample_id": kwargs["sample_id"],
                "status": scenario,
                "assets": [{"asset_id": "a", ("stable_failure_candidate" if mode == "single_revision_discovery" else "bug_revealed"): revealed}],
            }

        monkeypatch.setattr(module, "run_target_sample", sample)
        rows = module.run_guided_case_samples(
            runtime=SimpleNamespace(options=options, manifest={"case_id": "fixture"}),
            packet=copy.deepcopy(packet),
            run_dir=tmp_path / "run",
        )
        checkpoints = {
            row["sample_id"]: json.loads(
                (
                    tmp_path / "run/samples" / row["sample_id"] / "result.json"
                ).read_text()
            )
            for row in rows
        }
        progress = (
            json.loads((tmp_path / "run/progress.json").read_text()) if rows else None
        )
        if module is formal and progress is not None:
            progress = {
                "samples": [
                    {key: sample[key] for key in ("sample_id", "result_path")}
                    for sample in progress["samples"]
                ]
            }
        observed.append((rows, calls, checkpoints, progress))
    assert observed[0] == observed[1]


def test_prompt_templates_match_formal():
    root = os.environ.get("PROBE_FORMAL_ROOT")
    if not root:
        pytest.skip("set PROBE_FORMAL_ROOT to compare prompt templates")
    artifact = Path(__file__).resolve().parents[1]
    for language, formal_language in (("python", "python"), ("typescript", "TS")):
        templates = list((artifact / language / "prompt/templates").glob("*.md"))
        assert len(templates) == 8
        for template in templates:
            formal = (
                Path(root)
                / "src/common/test_augment"
                / formal_language
                / "prompt/templates"
                / template.name
            )
            assert template.read_bytes() == formal.read_bytes(), template.name


@pytest.mark.parametrize("readable", [False, True])
@pytest.mark.parametrize("mode", ["paired_reveal", "single_revision_discovery"])
def test_preflight_records_match_formal(tmp_path, monkeypatch, readable, mode):
    from itertools import product
    from probe.python.run.preflight import preflight_target_run

    formal = formal_module("preflight").preflight_target_run
    (tmp_path / "source").mkdir()
    (tmp_path / "source/counter.py").write_text("value = 2\n")
    monkeypatch.setattr(os, "access", lambda *_: readable)
    variants = product(
        [str(tmp_path), str(tmp_path / "absent"), ""],
        [[], ["source/counter.py"], ["missing.py"], ["../outside.py"]],
        [[], ["tests/generated"], ["tests"], ["."], ["../outside"]],
        [False, True],
    )
    for checkout, files, roots, routed in variants:
        manifest = {
            "evaluation_mode": mode,
            f"{'latest' if mode == 'single_revision_discovery' else 'buggy'}_checkout": {"path": checkout},
            "source_roots": ["source", "missing", "../outside"],
        }
        packet = {
            "target_units": [{"unit_id": "u1", "filepath": file} for file in files],
            "public_target_routes": {
                "available": routed,
                "targets": [
                    {"target_unit_id": "u1", "entrypoints": [{"entrypoint_id": "e1"}]}
                ]
                if routed
                else [],
            },
            "generated_test_roots": roots,
        }
        expected = formal(
            manifest=manifest, packet={**packet, "test_command": ["pytest"]}
        )
        expected["checks"] = [
            check
            for check in expected["checks"]
            if check["name"] != "test_command_present"
        ]
        assert preflight_target_run(manifest=manifest, packet=packet) == expected


@pytest.mark.parametrize("root", ["", "tests/generated/preflight/"])
@pytest.mark.parametrize("modules", [[], ["first", "first", "second"]])
@pytest.mark.parametrize(
    "failures",
    [
        [],
        [("preflight-target-import", "buggy")],
        [("preflight-target-import", "fixed")],
        [("preflight-target-import", "buggy"), ("preflight-runner", "fixed")],
    ],
)
def test_preflight_execution_matches_formal(tmp_path, root, modules, failures):
    from probe.python.run import preflight

    packet = {
        "generated_test_roots": [root],
        "module_contracts": [{"suggested_imports": [name]} for name in modules],
        "target_units": [{"unit_id": "u1"}],
        "public_target_routes": {
            "targets": [{"entrypoints": [{"entrypoint_id": "entry"}]}]
        },
    }
    observed = []
    for module in (preflight, formal_module("preflight")):
        calls = []

        def validate(revision_kind, proposal, proposal_path, sample_dir):
            source = {
                key: getattr(proposal, key)
                for key in ("asset_id", "test_file", "append_code")
            }
            saved = json.loads(proposal_path.read_text())
            assert {key: saved[key] for key in source} == source
            if module is preflight:
                assert saved == source
            calls.append((revision_kind, source, proposal_path, sample_dir))
            passed = (proposal.asset_id, revision_kind) not in failures
            return {
                "summary": {
                    "passed": passed,
                    "status": "passed" if passed else "needs_repair",
                    "failed_nodeids": [] if passed else [f"{proposal.test_file}::case"],
                }
            }

        result = module.run_revision_validation_preflight(
            runtime=SimpleNamespace(
                options=SimpleNamespace(evaluation_mode="paired_reveal"),
                validation=SimpleNamespace(run=validate),
            ),
            packet=packet,
            run_dir=tmp_path,
        )
        assert (
            json.loads((tmp_path / "preflight-validation.json").read_text()) == result
        )
        observed.append((result, calls))
    assert observed[0] == observed[1]


def test_minimization_canonicalization_matches_formal():
    from probe.python.prompt.proposal import (
        asset_intent_structure,
        validate_minimized_code_is_subset,
    )

    formal = formal_module("proposal", "prompt")
    source = '''import pytest
from math import sqrt

def helper(value):
    return value + 1

@pytest.mark.parametrize("value", [1])
async def test_counter(value: int) -> None:
    """An explicit oracle with nested statements."""
    unused = "counter"
    result: int = helper(value)
    for expected in [2]:
        assert result == expected
    with pytest.raises(ValueError):
        int("counter")
'''
    variants = [
        source,
        source.replace('    unused = "counter"\n', ""),
        source.replace("from math import sqrt\n", ""),
        source.replace("helper(value)\n", "helper(2)\n"),
        source.replace("result == expected", "result != expected"),
        source.replace(
            "    for expected in [2]:\n        assert result == expected\n", ""
        ),
        source.replace("pytest.raises(ValueError)", "pytest.raises(TypeError)"),
        source.replace("return value + 1", "return value + 2"),
        source.replace("test_counter(value: int)", "test_counter(value: str)"),
        source.replace(
            'pytest.mark.parametrize("value", [1])',
            'pytest.mark.parametrize("value", [2])',
        ),
        source.replace("test_counter", "test_renamed"),
        source + "\ndef test_extra(): pass\n",
    ]

    def capture(validate, candidate):
        try:
            validate(
                SimpleNamespace(append_code=source),
                SimpleNamespace(append_code=candidate),
            )
        except SystemExit as exc:
            return str(exc)
        return None

    for candidate in variants:
        if candidate != variants[-1]:
            asset = SimpleNamespace(append_code=candidate)
            assert asset_intent_structure(asset) == formal.asset_intent_structure(asset)
        assert capture(validate_minimized_code_is_subset, candidate) == capture(
            formal.validate_minimized_code_is_subset, candidate
        )
    assert capture(validate_minimized_code_is_subset, variants[1]) is None
    assert capture(validate_minimized_code_is_subset, variants[3]) is not None


def test_ordered_statement_subset_matches_formal():
    from probe.python.prompt.proposal import is_ordered_subset

    expected = formal_module("proposal", "prompt").is_ordered_subset
    sequences = [
        list(items)
        for length in range(5)
        for items in product(("", "a", "b"), repeat=length)
    ]
    for original in sequences:
        for candidate in sequences:
            before = original[:], candidate[:]
            assert is_ordered_subset(original, candidate) == expected(
                original, candidate
            )
            assert (original, candidate) == before


@pytest.mark.parametrize(
    "module",
    [
        "os",
        "sys",
        "time",
        "asyncio",
        "importlib",
        "aiohttp",
        "http.client",
        "httpx",
        "requests",
        "socket",
        "urllib.request",
    ],
)
def test_static_runtime_policy_matches_formal(module):
    from probe.python.prompt.proposal import validate_append_code

    formal = formal_module("proposal", "prompt").validate_append_code
    members = (
        "argv chdir environ execv execve fork getcwd getenv getpid getppid kill "
        "popen putenv system modules path sleep import_module ClientSession "
        "request HTTPConnection HTTPSConnection Client AsyncClient delete get "
        "head options patch post put stream create_connection socket urlopen unknown"
    ).split()

    def outcome(validate, code):
        try:
            validate("fixture", code)
        except SystemExit as exc:
            return str(exc)
        return None

    for member in members:
        for alias in (False, True):
            imported = f"import {module}" + (" as subject" if alias else "")
            qualified = f"{'subject' if alias else module}.{member}"
            direct = f"from {module} import {member}" + (" as member" if alias else "")
            local = "member" if alias else member
            for declaration, name in ((imported, qualified), (direct, local)):
                for expression in (name, f"{name}()", f"{name}(0)", f"{name}(2)"):
                    code = f"{declaration}\n{expression}\n"
                    assert outcome(validate_append_code, code) == outcome(formal, code)
