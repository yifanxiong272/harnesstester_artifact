"""Outcome classification and prior-attempt data used by target probing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .options import is_discovery


def validation_status(summary: dict[str, Any]) -> str:
    """Normalize validation status; incomplete evidence requires repair."""

    status = str(summary.get("status") or "")
    if status in {"passed", "assertion_failed", "needs_repair"}:
        return status
    if summary.get("passed"):
        return "passed"
    return "needs_repair"


def compact_text(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def buggy_outcome_category(asset: dict[str, Any]) -> str:
    buggy = asset.get("buggy", {})
    if buggy.get("passed") is True or buggy.get("status") == "passed":
        return "buggy_passed"
    if buggy.get("status") == "assertion_failed":
        return "buggy_failed_candidate"
    if buggy.get("status") == "needs_repair":
        return "buggy_needs_repair"
    if asset.get("status") == "error":
        return "proposal_error"
    return "unknown"


def latest_outcome_category(asset: dict[str, Any]) -> str:
    latest = asset.get("latest", {})
    if latest.get("passed") is True or latest.get("status") == "passed":
        return "latest_passed"
    if asset.get("stable_failure_candidate"):
        return "stable_failure_candidate"
    if asset.get("status") == "unstable_failure":
        return "unstable_failure"
    if (
        latest.get("status") == "needs_repair"
        or asset.get("status") == "latest_needs_repair"
    ):
        return "latest_needs_repair"
    return "proposal_error" if asset.get("status") == "error" else "unknown"


def validation_failure_kind(summary: dict[str, Any]) -> str:
    if not summary:
        return ""
    if summary.get("passed"):
        return ""
    return validation_status(summary)


def aggregate_asset_rows(
    base: dict[str, Any],
    proposal_path: Path,
    asset_rows: list[dict[str, Any]],
    *,
    evaluation_mode: str | None = None,
) -> dict[str, Any]:
    if is_discovery(evaluation_mode):
        stable = any(
            asset.get("status") == "stable_failure_candidate" for asset in asset_rows
        )
        if stable:
            status = "stable_failure_candidate"
        elif asset_rows and all(
            asset.get("status") == "latest_passed" for asset in asset_rows
        ):
            status = "latest_passed"
        elif any(asset.get("status") == "unstable_failure" for asset in asset_rows):
            status = "unstable_failure"
        elif asset_rows and all(asset.get("status") == "error" for asset in asset_rows):
            status = "error"
        else:
            status = "mixed_non_candidate"
        return {
            **base,
            "proposal_path": str(proposal_path),
            "assets": asset_rows,
            "status": status,
            "stable_failure_candidate": stable,
        }
    revealed = any(asset.get("status") == "revealed" for asset in asset_rows)
    if revealed:
        status = "revealed"
    elif any(asset.get("status") == "fixed_failed" for asset in asset_rows):
        status = "fixed_failed"
    elif asset_rows and all(
        asset.get("status") == "buggy_passed" for asset in asset_rows
    ):
        status = "buggy_passed"
    elif asset_rows and all(asset.get("status") == "error" for asset in asset_rows):
        status = "error"
    else:
        status = "mixed_non_revealing"
    return {
        **base,
        "proposal_path": str(proposal_path),
        "assets": asset_rows,
        "status": status,
        "bug_revealed": revealed,
    }


def iter_assets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        asset
        for row in rows
        for asset in row.get("assets", [])
        if isinstance(asset, dict)
    ]
