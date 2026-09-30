#!/usr/bin/env python3
"""Deterministic checks that must pass before Python model calls."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from common.utils.python.json_io import write_json
from common.utils.python.paths import safe_project_path, safe_relative_path
from probe.python.run.options import (
    is_discovery,
    primary_checkout,
    primary_revision_kind,
    revision_kinds,
)

if TYPE_CHECKING:
    from probe.python.run.session import TargetProbeRuntime


@dataclass(frozen=True)
class PreflightAsset:
    asset_id: str
    test_file: str
    append_code: str


def preflight_target_run(
    *,
    manifest: dict[str, Any],
    packet: dict[str, Any],
) -> dict[str, Any]:
    checks = []
    errors = []
    warnings = []

    def check(name: str, passed: bool, *, warning: str = "", **details: Any) -> None:
        record = {"name": name, "passed": bool(passed)}
        if warning:
            record["advisory"] = True
        checks.append({**record, **details})
        if not passed:
            if warning:
                warnings.append({"check": name, "warning": warning, **details})
            else:
                errors.append({"check": name, **details})

    checkout_value = str(primary_checkout(manifest).get("path") or "")
    checkout = Path(checkout_value)

    checkout_exists = bool(checkout_value) and checkout.is_dir()
    check(
        f"{primary_revision_kind(manifest.get('evaluation_mode'))}_checkout_exists",
        checkout_exists,
        path=str(checkout),
    )

    target_files = sorted(
        {
            str(unit.get("filepath") or "")
            for unit in packet.get("target_units", [])
            if unit.get("filepath")
        }
    )
    if not target_files:
        check(
            "target_source_files_present",
            False,
            error="missing_target_source_files",
        )
    for filepath in target_files:
        details = {"filepath": filepath}
        try:
            path = safe_project_path(checkout, filepath)
            passed = checkout_exists and path.is_file() and os.access(path, os.R_OK)
        except SystemExit as exc:
            passed = False
            details["error"] = str(exc)
        check("target_source_file_readable", passed, **details)

    routed = {
        str(target.get("target_unit_id") or "")
        for target in (packet.get("public_target_routes") or {}).get("targets", [])
        if target.get("entrypoints")
    }
    missing_routes = [
        str(unit.get("unit_id") or "")
        for unit in packet.get("target_units", [])
        if str(unit.get("unit_id") or "") not in routed
    ]
    routes_available = (packet.get("public_target_routes") or {}).get(
        "available"
    ) is True and not missing_routes
    check(
        "public_target_routes_available",
        routes_available,
        warning="curation_review_required",
        missing_target_unit_ids=missing_routes,
    )

    generated_roots = packet.get("generated_test_roots") or []
    if not generated_roots:
        check(
            "generated_test_root_safe",
            False,
            error="missing_generated_test_roots",
        )
    for root in generated_roots:
        details = {"root": str(root)}
        try:
            safe_relative_path(details["root"])
            normalized = Path(details["root"]).as_posix().rstrip("/")
            details["root"] = normalized
            passed = bool(normalized) and normalized not in {".", "tests", "test"}
        except SystemExit as exc:
            passed = False
            details["error"] = str(exc)
        check("generated_test_root_safe", passed, **details)

    for root in manifest.get("source_roots", []):
        try:
            source_root = safe_project_path(checkout, str(root))
            if checkout_exists and not source_root.exists():
                warnings.append({"kind": "missing_source_root", "root": str(root)})
        except SystemExit as exc:
            warnings.append(
                {"kind": "invalid_source_root", "root": str(root), "error": str(exc)}
            )

    return {
        "schema": "test-augment-python-bug-discovery-preflight"
        if is_discovery(manifest.get("evaluation_mode"))
        else "test-augment-python-br-preflight",
        "passed": not errors,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }


def run_revision_validation_preflight(
    *,
    runtime: TargetProbeRuntime,
    packet: dict[str, Any],
    run_dir: Path,
) -> dict[str, Any]:
    """Verify the selected revisions can collect a generated pytest before model calls."""

    root = str((packet.get("generated_test_roots") or [""])[0]).rstrip("/")
    out_path = run_dir / "preflight-validation.json"
    if not root:
        record = {
            "passed": False,
            "path": str(out_path),
            "error": "missing_generated_test_root",
        }
        write_json(out_path, record)
        return record

    modules = [
        str(contract.get("suggested_imports", [""])[0])
        for contract in packet.get("module_contracts", [])
        if contract.get("suggested_imports")
    ]
    modules = list(dict.fromkeys(module for module in modules if module))
    preflight_dir = run_dir / "preflight-validation"
    target_import: dict[str, Any] = {
        "attempted": False,
        "passed": None,
        "reason": "missing_target_import",
    }
    if modules:
        imports = "\n".join(
            f"import {module} as target_module_{index}"
            for index, module in enumerate(modules)
        )
        names = ", ".join(f"target_module_{index}" for index in range(len(modules)))
        target_import = validate_preflight_asset(
            runtime=runtime,
            sample_dir=preflight_dir / "target-import",
            asset=PreflightAsset(
                asset_id="preflight-target-import",
                test_file=f"{root}/test_benchmarkbr_preflight_target_import.py",
                append_code=(
                    f"{imports}\n\n"
                    "def test_benchmarkbr_preflight_target_import():\n"
                    f"    assert len([{names}]) == {len(modules)}\n"
                ),
            ),
        )

    if target_import.get("passed"):
        runner = {
            "attempted": False,
            "passed": True,
            "reason": "confirmed_by_target_import",
        }
    else:
        runner = validate_preflight_asset(
            runtime=runtime,
            sample_dir=preflight_dir / "runner",
            asset=PreflightAsset(
                asset_id="preflight-runner",
                test_file=f"{root}/test_benchmarkbr_preflight_runner.py",
                append_code="def test_benchmarkbr_preflight_runner():\n    assert True\n",
            ),
        )

    record = {
        "passed": bool(runner.get("passed")),
        "path": str(out_path),
        "runner": runner,
        "target_import": target_import,
    }
    write_json(out_path, record)
    return record


def validate_preflight_asset(
    *,
    runtime: TargetProbeRuntime,
    sample_dir: Path,
    asset: PreflightAsset,
) -> dict[str, Any]:
    proposal_path = sample_dir / "proposal.json"
    sample_dir.mkdir(parents=True, exist_ok=True)
    write_json(proposal_path, asdict(asset))
    outcomes = {
        kind: runtime.validation.run(
            revision_kind=kind,
            proposal=asset,
            proposal_path=proposal_path,
            sample_dir=sample_dir / kind,
        )["summary"]
        for kind in revision_kinds(runtime.options.evaluation_mode)
    }
    return {
        "attempted": True,
        "passed": all(bool(summary.get("passed")) for summary in outcomes.values()),
        "asset": {"test_file": asset.test_file},
        **outcomes,
    }
