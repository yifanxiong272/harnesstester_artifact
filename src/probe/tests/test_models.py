"""Asset storage keeps formal serialization, deduplication, and repair semantics."""

from dataclasses import fields, replace

import pytest

from test_compaction import formal_module
from test_python_probe import fixture

from probe.python.models import ProbeAsset, ProbeBoundary
from probe.python.prompt.proposal import parse_probe_plan, parse_proposal_partial
from probe.python.run import generation, repair
from probe.python.run.generation import packet_public_entrypoints


@pytest.fixture
def asset(tmp_path):
    _, _, packet, plan, raw = fixture(tmp_path)
    parsed_plan, _ = parse_probe_plan(plan)
    proposal, errors = parse_proposal_partial(
        {"assets": [raw]},
        canonical_plan=parsed_plan,
        public_entrypoints=packet_public_entrypoints(packet),
    )
    assert not errors
    return proposal.assets[0]


def formal_asset(asset):
    return formal_module("proposal", "prompt").ProbeAsset(**asset.to_dict())


def test_asset_stores_implementation_and_boundary_without_derived_hash(asset):
    assert {field.name for field in fields(ProbeAsset)} == {
        "asset_id", "boundary", "input_construction", "observable_oracle",
        "primary_oracle", "test_file", "append_code", "mocking_plan",
    }
    original = asset.to_dict()
    exported = asset.to_dict()
    exported["target_unit_ids"].append("other")
    exported["activation_conditions"].clear()
    assert asset.to_dict() == original


def test_repair_reuses_original_boundary_and_derives_current_hash(asset):
    updated = replace(
        asset,
        asset_id="repaired",
        boundary=replace(asset.boundary, independent_oracle="changed intent"),
        input_construction="repaired fixture",
        observable_oracle="changed observation",
        primary_oracle="changed assertion",
        append_code=asset.append_code + "\n# updated fixture\n",
        mocking_plan="repair setup",
    )
    original = asset.to_dict()
    result = repair.normalize_harness_repaired_asset(asset, updated)
    expected = formal_module("repair").normalize_harness_repaired_asset(
        formal_asset(asset), formal_asset(updated)
    )
    assert result.boundary is asset.boundary
    assert result.to_dict() == expected.to_dict()
    assert result.to_dict()["test_asset_sha256"] != original["test_asset_sha256"]
    assert asset.to_dict() == original


@pytest.mark.parametrize(
    "field_name",
    [field.name for field in fields(ProbeBoundary)]
    + [
        "asset_id", "input_construction", "observable_oracle", "primary_oracle",
        "test_file", "append_code", "mocking_plan",
    ],
)
def test_field_changes_preserve_formal_fingerprints_and_validation(asset, field_name):
    boundary_field = field_name in {field.name for field in fields(ProbeBoundary)}
    owner = asset.boundary if boundary_field else asset
    value = getattr(owner, field_name)
    change = {field_name: value + ["other"] if isinstance(value, list) else value + " changed"}
    changed = (
        replace(asset, boundary=replace(asset.boundary, **change))
        if boundary_field
        else replace(asset, **change)
    )
    expected_before, expected_after = formal_asset(asset), formal_asset(changed)
    formal_generation = formal_module("generation")
    assert generation.semantic_fingerprint(changed) == formal_generation.semantic_fingerprint(
        expected_after
    )
    assert generation.semantic_fingerprint(changed.to_dict()) == generation.semantic_fingerprint(
        changed
    )
    kept, dropped = generation.filter_semantic_duplicates([asset, changed], [])
    expected_kept, expected_dropped = formal_generation.filter_semantic_duplicates(
        [expected_before, expected_after], []
    )
    assert [item.to_dict() for item in kept] == [item.to_dict() for item in expected_kept]
    assert dropped == expected_dropped

    def validation_result(validate, before, after):
        try:
            validate(before, after)
        except SystemExit as exc:
            return str(exc)
        return None

    for name in (
        "validate_harness_repair_preserves_intent", "validate_minimized_metadata",
    ):
        assert validation_result(getattr(repair, name), asset, changed) == validation_result(
            getattr(formal_module("repair"), name), expected_before, expected_after
        )
