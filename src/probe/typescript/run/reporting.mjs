import { isDiscovery } from "./options.mjs";

export function compactText(value, limit) {
  const text = String(value || "")
    .replace(/\s+/gu, " ")
    .trim();
  return text.length <= limit
    ? text
    : `${text.slice(0, limit - 3).trimEnd()}...`;
}

export function iterAssets(rows) {
  return rows.flatMap((row) =>
    (row.assets || []).filter((asset) => asset && typeof asset === "object"),
  );
}

export function validationStatus(summary = {}) {
  if (["passed", "assertion_failed", "needs_repair"].includes(summary.status)) {
    return summary.status;
  }
  if (summary.passed) {
    return "passed";
  }
  return "needs_repair";
}

export function validationFailureKind(summary = {}) {
  if (!summary || summary.passed) {
    return "";
  }
  return validationStatus(summary);
}

export function aggregateAssetRows(
  base,
  proposalPath,
  assetRows,
  evaluationMode,
) {
  if (isDiscovery(evaluationMode)) {
    const stable = assetRows.some(
      (asset) => asset.status === "stable_failure_candidate",
    );
    let status = "mixed_non_revealing";
    if (stable) status = "stable_failure_candidate";
    else if (
      assetRows.length &&
      assetRows.every((asset) => asset.status === "latest_passed")
    )
      status = "latest_passed";
    else if (
      assetRows.length &&
      assetRows.every((asset) => asset.status === "error")
    )
      status = "error";
    return {
      ...base,
      proposal_path: proposalPath,
      assets: assetRows,
      status,
      bug_revealed: false,
      ...(stable ? { stable_failure_candidate: true } : {}),
    };
  }
  const revealed = assetRows.some((asset) => asset.status === "revealed");
  let status = "mixed_non_revealing";
  if (revealed) {
    status = "revealed";
  } else if (assetRows.some((asset) => asset.status === "fixed_failed")) {
    status = "fixed_failed";
  } else if (
    assetRows.length > 0 &&
    assetRows.every((asset) => asset.status === "buggy_passed")
  ) {
    status = "buggy_passed";
  } else if (
    assetRows.length > 0 &&
    assetRows.every((asset) => asset.status === "error")
  ) {
    status = "error";
  }
  return {
    ...base,
    proposal_path: proposalPath,
    assets: assetRows,
    status,
    bug_revealed: revealed,
  };
}

export function targetOutcomeCategory(asset, discovery = false) {
  const prefix = discovery ? "latest" : "buggy";
  const target = asset[prefix];
  if (target?.passed || target?.status === "passed") {
    return `${prefix}_passed`;
  }
  if (target?.status === "assertion_failed") {
    return `${prefix}_failed_candidate`;
  }
  if (target?.status === "needs_repair") {
    return `${prefix}_needs_repair`;
  }
  if (asset.status === "error") {
    return "proposal_error";
  }
  return "unknown";
}
