#!/usr/bin/env python3
"""Dataclass models shared across target-probing modules."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TargetUnit:
    unit_id: str
    filepath: str
    qualname: str
    kind: str
    start_line: int
    end_line: int
    selection_source: str
    code: str = ""


@dataclass(frozen=True)
class ProbeBoundary:
    """Canonical intent and oracle metadata inherited from the validated plan."""

    boundary_id: str
    target_unit_ids: list[str]
    public_entrypoint_id: str
    test_intent: str
    activation_conditions: list[str]
    independent_oracle: str
    supporting_evidence: str
    expected_observation: str
    oracle_family: str
    novelty_from_prior: str
    bug_hypothesis: str
    oracle_mode: str


@dataclass(frozen=True)
class ProbeAsset:
    """A test implementation bound to its canonical behavioral boundary."""

    asset_id: str
    boundary: ProbeBoundary
    input_construction: str
    observable_oracle: str
    primary_oracle: str
    test_file: str
    append_code: str
    mocking_plan: str = ""

    def to_dict(self) -> dict[str, Any]:
        # Preserve the flat field order used by prompts and saved proposals.
        boundary = asdict(self.boundary)
        oracle_mode = boundary.pop("oracle_mode")
        return {
            "asset_id": self.asset_id,
            **boundary,
            "input_construction": self.input_construction,
            "observable_oracle": self.observable_oracle,
            "primary_oracle": self.primary_oracle,
            "oracle_mode": oracle_mode,
            "test_file": self.test_file,
            "append_code": self.append_code,
            "test_asset_sha256": hashlib.sha256(
                f"{self.test_file}\0{self.append_code}".encode("utf-8")
            ).hexdigest(),
            "mocking_plan": self.mocking_plan,
        }


@dataclass(frozen=True)
class ProbeProposal:
    assets: list[ProbeAsset]
    boundary_plan: list[dict[str, Any]] = field(default_factory=list)
    plan_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"assets": [asset.to_dict() for asset in self.assets]}
        if self.boundary_plan:
            payload["boundary_plan"] = self.boundary_plan
        if self.plan_notes:
            payload["plan_notes"] = self.plan_notes
        return payload
