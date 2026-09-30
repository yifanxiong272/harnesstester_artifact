"""Run configuration and policies for paired probing and latest-revision discovery."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .deadline import DEFAULT_CASE_TIME_BUDGET_SECONDS

PAIRED_REVEAL_EVALUATION = "paired_reveal"
SINGLE_REVISION_DISCOVERY_EVALUATION = "single_revision_discovery"
TARGET_PROBING_TRACK = "target-probing"
TARGET_PROBE_LDH_STRATEGY = "target_probe_ldh"
TARGET_PROBE_CONTRACT_AGNOSTIC_STRATEGY = "target_probe_contract_agnostic"
RUN_PATH_PART_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,160}")


@dataclass(frozen=True)
class StrategyProfile:
    allow_context: bool
    repair_mode: str

    @property
    def repair_key(self) -> str:
        return (
            "contract_agnostic_repair"
            if self.repair_mode == "generic"
            else "harness_repair"
        )


_PROFILES = {
    TARGET_PROBE_LDH_STRATEGY: StrategyProfile(True, "harness"),
    TARGET_PROBE_CONTRACT_AGNOSTIC_STRATEGY: StrategyProfile(False, "generic"),
}
TARGET_PROBE_STRATEGIES = set(_PROFILES)


@dataclass(frozen=True)
class TargetProbeRunOptions:
    model: str
    env_file: Path
    evaluation_mode: str = PAIRED_REVEAL_EVALUATION
    strategy: str = TARGET_PROBE_LDH_STRATEGY
    provider: str = "openrouter"
    direct_samples: int = 10
    samples: int = 10
    soft_samples: int = 2
    assets_per_sample: int = 5
    timeout: int = 240
    case_time_budget_seconds: float = DEFAULT_CASE_TIME_BUDGET_SECONDS
    context_requests: int = 1
    minimize_buggy_failures_per_sample: int = 1
    minimization_preserve_attempts: int = 1
    minimization_failure_excerpt_chars: int = 1000
    harness_repair_attempts: int = 1
    harness_repairs_per_sample: int = 1
    harness_context_requests: int = 1
    max_workflow_errors: int = 2
    max_reveal_candidates: int = 1
    reveal_confirmation_runs: int = 2
    model_timeout: int = 120
    model_retries: int = 5


def primary_checkout(manifest: dict[str, Any]) -> dict[str, Any]:
    checkout = manifest.get(
        f"{primary_revision_kind(manifest.get('evaluation_mode'))}_checkout"
    )
    return checkout if isinstance(checkout, dict) else {}


def is_discovery(mode: str | None) -> bool:
    return mode == SINGLE_REVISION_DISCOVERY_EVALUATION


def primary_revision_kind(mode: str | None) -> str:
    return "latest" if is_discovery(mode) else "buggy"


def revision_kinds(mode: str | None) -> tuple[str, ...]:
    return ("latest",) if is_discovery(mode) else ("buggy", "fixed")


def normalize_target_strategy(strategy: str) -> str:
    """Validate and return a target-probing strategy name."""
    if strategy not in TARGET_PROBE_STRATEGIES:
        raise SystemExit(f"unsupported target-probing strategy: {strategy}")
    return strategy


def strategy_profile(strategy: str) -> StrategyProfile:
    return _PROFILES[normalize_target_strategy(strategy)]


def validate_run_path_part(value: str, label: str) -> None:
    if not RUN_PATH_PART_RE.fullmatch(value):
        raise ValueError(f"unsafe {label}: {value}")


def validate_run_options(options: Any) -> None:
    if options.evaluation_mode not in {
        PAIRED_REVEAL_EVALUATION,
        SINGLE_REVISION_DISCOVERY_EVALUATION,
    }:
        raise ValueError(f"unsupported evaluation mode: {options.evaluation_mode}")
    value = options.case_time_budget_seconds
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not 0 <= value < float("inf")
    ):
        raise ValueError("case_time_budget_seconds must be a finite nonnegative number")
    nonnegative = (
        "direct_samples",
        "samples",
        "soft_samples",
        "context_requests",
        "minimize_buggy_failures_per_sample",
        "minimization_preserve_attempts",
        "harness_repair_attempts",
        "harness_repairs_per_sample",
        "harness_context_requests",
        "max_workflow_errors",
        "model_retries",
    )
    positive = (
        "assets_per_sample",
        "max_reveal_candidates",
        "reveal_confirmation_runs",
        "minimization_failure_excerpt_chars",
    )
    for field in nonnegative + positive:
        value = getattr(options, field)
        minimum = 1 if field in positive else 0
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            qualifier = "positive" if minimum else "nonnegative"
            raise ValueError(f"{field} must be a {qualifier} integer")
    for field in ("timeout", "model_timeout"):
        value = getattr(options, field)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not 0 < value < float("inf")
        ):
            raise ValueError(f"{field} must be a finite positive number")
