"""Public routes must belong to a target selected by the boundary plan."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from probe.python.run import generation
from test_python_probe import FixedModel, fixture, options


@pytest.mark.parametrize("focus", ["", "u1"])
def test_plan_rejects_route_owned_only_by_another_target(tmp_path, focus):
    _, _, packet, plan, _ = fixture(tmp_path, second_target=True)
    packet["focus_target_unit_id"] = focus
    plan["boundary_plan"][0]["route"]["entrypoint_id"] = (
        packet["public_target_routes"]["targets"][1]["entrypoints"][0]["entrypoint_id"]
    )
    with pytest.raises(SystemExit, match="public entrypoint does not reach a selected target unit"):
        generation.validate_boundary_plan(packet, plan)


@pytest.mark.parametrize("joint", [False, True])
@pytest.mark.parametrize("owner", [0, 1])
def test_plan_accepts_selected_route_owner_without_mutation(tmp_path, joint, owner):
    _, _, packet, plan, _ = fixture(tmp_path, second_target=True)
    boundary = plan["boundary_plan"][0]
    boundary["target_unit_ids"] = ["u1", "u2"] if joint else [f"u{owner + 1}"]
    packet["focus_target_unit_id"] = "u1" if joint else f"u{owner + 1}"
    boundary["route"]["entrypoint_id"] = (
        packet["public_target_routes"]["targets"][owner]["entrypoints"][0]["entrypoint_id"]
    )
    before = deepcopy((packet, plan))
    generation.validate_boundary_plan(packet, plan)
    assert (packet, plan) == before


def test_cross_target_plan_fails_before_context_resolution(tmp_path, monkeypatch):
    _, _, packet, plan, _ = fixture(tmp_path, second_target=True)
    plan["boundary_plan"][0]["route"]["entrypoint_id"] = (
        packet["public_target_routes"]["targets"][1]["entrypoints"][0]["entrypoint_id"]
    )
    model = FixedModel([plan])
    monkeypatch.setattr(
        generation, "complete_and_record",
        lambda runtime, prompt, path: model.complete(prompt),
    )
    monkeypatch.setattr(
        generation, "resolve_context_for_manifest",
        lambda **kwargs: pytest.fail("invalid ownership reached context resolution"),
    )
    with pytest.raises(generation.InvalidModelOutputError, match="public entrypoint does not reach a selected target unit"):
        generation.generate_target_plan_and_context(
            runtime=SimpleNamespace(options=options(), manifest={}),
            packet=packet, sample_dir=tmp_path, prior_attempts=[],
            prompt_style=generation.DIRECT_PROMPT_STYLE,
        )
    assert len(model.prompts) == 1
    assert not (tmp_path / "plan.json").exists()
    assert "retrieved_context" not in packet


def test_route_ownership_comes_from_packet_target_not_entrypoint_field(tmp_path):
    _, _, packet, plan, _ = fixture(tmp_path, second_target=True)
    other = packet["public_target_routes"]["targets"][1]["entrypoints"][0]
    other["target_unit_id"] = "u1"
    plan["boundary_plan"][0]["route"]["entrypoint_id"] = other["entrypoint_id"]
    with pytest.raises(SystemExit, match="public entrypoint does not reach a selected target unit"):
        generation.validate_boundary_plan(packet, plan)
