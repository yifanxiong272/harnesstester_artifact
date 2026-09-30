#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from augment.python.acceptance import DEFAULT_ACCEPTANCE_POLICY
from augment.python.strategy import DEFAULT_STRATEGY, is_contract_directed
from augment.python.run.client import (
    chat_completion,
    message_content,
    provider_access,
)
from augment.python.run.validate import (
    collect_nodeids,
    filter_passing_nodeids,
    run_coverage_for_nodeids,
)
from common.utils.python.json_io import write_json


@dataclass(frozen=True)
class RunOptions:
    """Project, model, and execution settings for one augmentation run."""

    project: str
    project_root: Path
    out_root: Path
    model: str
    provider: str
    env: dict[str, str]
    python: str
    coverage_source: str
    test_pythonpath: list[str] = field(default_factory=list)
    rounds: int = 1
    time_budget_seconds: float = 0.0
    run_id: str | None = None
    timeout: int = 90
    repair_context_requests: int = 0
    constraints: list[str] = field(default_factory=list)
    strategy: str = DEFAULT_STRATEGY
    acceptance_policy: str = DEFAULT_ACCEPTANCE_POLICY

    @property
    def effective_repair_context_requests(self) -> int:
        return (
            self.repair_context_requests if is_contract_directed(self.strategy) else 0
        )


@dataclass(frozen=True)
class ModelSession:
    """Model access and response recording for generation and repair."""

    model: str
    provider: str
    env: dict[str, str]

    def validate(self) -> None:
        """Validate the configured model access."""

        if not self.model:
            raise SystemExit("model is required for test augmentation")
        provider_access(self.provider, self.env)

    def complete_messages(
        self, messages: list[dict[str, str]], *, raw_path: Path
    ) -> str:
        """Complete one persisted JSON conversation used by segment generation."""

        response = chat_completion(
            messages=messages,
            model=self.model,
            provider=self.provider,
            env=self.env,
        )
        self._write_response(raw_path, response)
        return message_content(response)

    def _write_response(self, raw_path: Path, response: dict[str, Any]) -> None:
        write_json(
            raw_path,
            {"provider": self.provider, "model": self.model, "response": response},
        )


@dataclass(frozen=True)
class ValidationSession:
    """Collect, run, and measure generated pytest nodeids in one project copy."""

    python: str
    timeout: int
    coverage_source: str
    test_pythonpath: list[str] = field(default_factory=list)

    def collect(
        self, project_root: Path, test_file: str, *, keyword: str
    ) -> tuple[list[str], dict[str, Any]]:
        return collect_nodeids(
            project_root,
            test_file,
            keyword=keyword,
            python=self.python,
            timeout=self.timeout,
            pythonpath=self.test_pythonpath,
        )

    def filter_passing(self, project_root: Path, nodeids: list[str]) -> dict[str, Any]:
        return filter_passing_nodeids(
            project_root,
            nodeids,
            python=self.python,
            timeout=self.timeout,
            pythonpath=self.test_pythonpath,
        )

    def coverage(
        self,
        project_root: Path,
        selectors: list[str],
        out_path: Path,
        *,
        fail_fast: bool = False,
    ) -> dict[str, Any]:
        return run_coverage_for_nodeids(
            project_root,
            selectors,
            out_path,
            source=self.coverage_source,
            python=self.python,
            timeout=max(120, self.timeout * 2),
            pythonpath=self.test_pythonpath,
            fail_fast=fail_fast,
        )


@dataclass(frozen=True)
class RunContext:
    """Runtime bundle shared by workflow phases."""

    options: RunOptions
    run_dir: Path
    current_root: Path
    model: ModelSession
    validation: ValidationSession


@dataclass(frozen=True)
class SampleContext:
    """Identity and paths for one selected objective in one round."""

    round_index: int
    sample_dir: Path
    objective: dict[str, Any]
    snapshot: dict[str, Any] = field(default_factory=dict)

    @property
    def sample_id(self) -> str:
        parts = self.sample_dir.parts[-3:]
        return "_".join([*parts, "attempt_000"])

    def repair_sample_id(self) -> str:
        parts = self.sample_dir.parts[-3:]
        return "_".join([*parts, "attempt_001"])
