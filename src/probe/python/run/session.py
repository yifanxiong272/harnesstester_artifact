"""Model and validation sessions for one prepared case."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common.utils.python.json_io import write_json
from common.utils.python.paths import safe_project_path

from ..runtime.validate import pytest_evidence, run_pytest_command
from .client import chat_completion
from .deadline import limit_timeout
from .options import TargetProbeRunOptions, primary_revision_kind

COPY_IGNORE = shutil.ignore_patterns(
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".coverage*",
    ".test-augment-*",
)


@dataclass(frozen=True)
class ModelSession:
    model: str
    provider: str
    env: dict[str, str]
    timeout: int
    retries: int

    def complete(self, prompt: str) -> dict[str, Any]:
        limit_timeout()
        response = chat_completion(
            prompt=prompt,
            model=self.model,
            provider=self.provider,
            env=self.env,
            timeout=self.timeout,
            retries=self.retries,
        )
        limit_timeout()
        return response

    def raw_payload(self, response: dict[str, Any]) -> dict[str, Any]:
        return {"provider": self.provider, "model": self.model, "response": response}


@dataclass(frozen=True)
class ValidationSession:
    case: dict[str, Any]
    roots: dict[str, Path]
    interpreters: dict[str, str]
    timeout: int

    def run(
        self, revision_kind: str, proposal: Any, proposal_path: Path, sample_dir: Path
    ) -> dict[str, Any]:
        limit_timeout()
        sample_dir.mkdir(parents=True, exist_ok=True)
        revision = str(self.case["revisions"][revision_kind])
        temporary = tempfile.TemporaryDirectory(prefix="validation-", dir=sample_dir)
        checkout = Path(temporary.name) / "checkout"
        record = {
            "revision": revision,
            "copy_root": str(checkout),
            "proposal_path": str(proposal_path),
            "test_file": proposal.test_file,
        }
        try:
            shutil.copytree(
                self.roots[revision_kind],
                checkout,
                symlinks=True,
                ignore=COPY_IGNORE,
            )
            target = safe_project_path(checkout, proposal.test_file)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8") as stream:
                stream.write(proposal.append_code)
            result = run_pytest_command(
                checkout,
                self.interpreters[revision_kind],
                proposal.test_file,
                timeout=self.timeout,
                report_path=sample_dir / f"{revision_kind}.pytest-report.json",
            )
            result = {
                **result,
                "phase": "pytest",
                "evidence": pytest_evidence(
                    result.get("output_tail", ""),
                    result.get("exit_code"),
                    result.get("timed_out", False),
                    report=result.get("structured_report"),
                ),
            }
            write_json(sample_dir / f"{revision_kind}.validation.json", result)
        finally:
            temporary.cleanup()
            record["cleanup"] = {"removed": not checkout.exists()}
            write_json(sample_dir / f"{revision_kind}.materialized.json", record)
        summary = {
            "revision": revision,
            **result["evidence"],
            "phase": "pytest",
            "exit_code": result.get("exit_code"),
            "timed_out": result.get("timed_out", False),
            "output_tail": str(result.get("output_tail") or "")[-8000:],
            "setup_policy": "prepared",
        }
        limit_timeout()
        return {"materialized": record, "result": result, "summary": summary}


@dataclass(frozen=True)
class TargetProbeRuntime:
    manifest: dict[str, Any]
    options: TargetProbeRunOptions
    model: ModelSession
    validation: ValidationSession


def complete_and_record(
    runtime: TargetProbeRuntime, prompt: str, raw_path: Path
) -> dict[str, Any]:
    """Persist a completed model response at its phase-specific path."""
    response = runtime.model.complete(prompt)
    write_json(raw_path, runtime.model.raw_payload(response))
    return response


@dataclass(frozen=True)
class AssetValidationState:
    """An asset and its primary-checkout evidence, shared with test-side repair."""

    asset: Any
    proposal_path: Path
    sample_dir: Path
    buggy: dict[str, Any]


def validate_buggy_asset(
    runtime: TargetProbeRuntime,
    asset: Any,
    sample_dir: Path,
    parse_errors: list[dict[str, Any]] | None = None,
) -> AssetValidationState:
    """Save a candidate and validate the active buggy or latest checkout."""
    proposal_path = sample_dir / "proposal.json"
    payload = asset.to_dict()
    if parse_errors:
        payload["parse_errors"] = parse_errors
    write_json(proposal_path, payload)
    buggy = runtime.validation.run(
        revision_kind=primary_revision_kind(runtime.options.evaluation_mode),
        proposal=asset,
        proposal_path=proposal_path,
        sample_dir=sample_dir,
    )
    return AssetValidationState(asset, proposal_path, sample_dir, buggy)
