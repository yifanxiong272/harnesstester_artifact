/** Confirm failure candidates on one frozen latest revision. */
import fs from "node:fs";
import path from "node:path";
import { assetResultRow } from "./candidate.mjs";
import { strategyProfile } from "./options.mjs";
import {
  minimizeAsset,
  repairDisposition,
  repairHarnessAsset,
  skippedHarnessRepairRecord,
} from "./repair.mjs";
import {
  compactText,
  validationFailureKind,
  validationStatus,
} from "./reporting.mjs";
import { validateBuggyAsset, validateRevision } from "./session.mjs";
import { ensureDir } from "../support/json.mjs";

export function isDiscoveryFailure(summary = {}) {
  const status = validationStatus(summary);
  if (status === "assertion_failed") return true;
  return (
    status === "needs_repair" &&
    !summary.timed_out &&
    summary.classification_source === "structured_reporter" &&
    summary.classification_reason === "non_assertion_or_incomplete_execution" &&
    (summary.failed_nodeids || []).length > 0 &&
    (summary.failed_hooks || []).length === 0
  );
}

function checkoutRoots(copyRoot) {
  const root = String(copyRoot || "").replace(/[/\\]+$/u, "");
  if (!root) return [];
  const roots = new Set([root, path.resolve(root)]);
  let ancestor = path.resolve(root);
  const tail = [];
  // The checkout is gone; resolve only its surviving ancestors.
  while (true) {
    try {
      roots.add(path.join(fs.realpathSync(ancestor), ...tail));
      break;
    } catch (error) {
      if (!["ENOENT", "ENOTDIR"].includes(error.code)) break;
      const parent = path.dirname(ancestor);
      if (parent === ancestor) break;
      tail.unshift(path.basename(ancestor));
      ancestor = parent;
    }
  }
  return [...roots].sort((a, b) => b.length - a.length);
}

function normalizeCheckout(text, roots) {
  if (!roots.length) return text;
  const escaped = roots
    .map((root) => root.replace(/[.*+?^${}()|[\]\\]/gu, "\\$&"))
    .join("|");
  // Normalize the checkout identities recorded for this validation.
  return text.replace(
    new RegExp(`(?<![\\w./\\\\-])(?:file://)?(?:${escaped})(?=$|[/\\\\\\s:'")\\],}])`, "gu"),
    "<checkout>",
  );
}

export function failureFingerprint(summary = {}, { copyRoot = "" } = {}) {
  const roots = checkoutRoots(copyRoot);
  const nodeids = (summary.failed_nodeids || [])
    .map((nodeid) => {
      const [file, ...identity] = String(nodeid).split(" > ");
      const relative = normalizeCheckout(file, roots).replace(/^<checkout>[/\\]/u, "");
      return [relative, ...identity].join(" > ");
    })
    .sort();
  const excerpt = compactText(
    normalizeCheckout(String(summary.failure_excerpt || ""), roots), 400,
  );
  return JSON.stringify({
    nodeids,
    kind: validationFailureKind(summary),
    excerpt,
  });
}

export function confirmFailure(runtime, state, variant) {
  const summary = state.buggy.summary;
  const fingerprint = failureFingerprint(summary, {
    copyRoot: state.buggy.materialized?.copy_root,
  });
  const count = Math.max(0, runtime.options.revealConfirmationRuns);
  const result = {
    required_runs: count,
    initial_failure_fingerprint: fingerprint,
    runs: [],
    stable: false,
  };
  if (!isDiscoveryFailure(summary)) {
    return {
      ...result,
      skipped_reason: "latest_outcome_not_candidate_eligible",
    };
  }
  for (let attempt = 1; attempt <= count; attempt += 1) {
    const dir = path.join(
      state.sampleDir,
      `${variant}-confirmation-${String(attempt).padStart(3, "0")}`,
    );
    ensureDir(dir);
    const validation = validateRevision({
      runtime,
      revisionKind: "latest",
      asset: state.asset,
      assetDir: dir,
    });
    const latest = validation.summary;
    const observed = failureFingerprint(latest, {
      copyRoot: validation.materialized?.copy_root,
    });
    result.runs.push({
      attempt,
      passed: isDiscoveryFailure(latest) && observed === fingerprint,
      test_asset_sha256: state.asset.test_asset_sha256 || "",
      latest,
      failure_fingerprint: observed,
    });
  }
  result.stable =
    result.runs.length === count && result.runs.every((run) => run.passed);
  return result;
}

export async function runDiscoveryAsset({
  runtime,
  packet,
  plan,
  asset,
  assetDir,
  minimizationAllowed,
  harnessRepairAllowed,
  onResult = null,
}) {
  ensureDir(assetDir);
  let state = validateBuggyAsset(runtime, asset, assetDir);
  const classification = repairDisposition(state.buggy.summary);
  let harnessRepair = {};
  let minimization = {};
  if (validationStatus(state.buggy.summary) === "passed") {
    return {
      ...assetResultRow(state, {
        originalAsset: asset,
        harnessRepair,
        minimization,
        outcomeKey: "latest",
      }),
      status: "latest_passed",
      stable_failure_candidate: false,
    };
  }
  if (classification.needs_repair) {
    harnessRepair = harnessRepairAllowed
      ? await repairHarnessAsset({ runtime, packet, plan, state })
      : skippedHarnessRepairRecord(classification);
    if (harnessRepair.state) state = harnessRepair.state;
  }
  let confirmation = confirmFailure(runtime, state, "base");
  const resultRow = () => {
    const row = assetResultRow(state, {
      originalAsset: asset,
      harnessRepair,
      minimization,
      outcomeKey: "latest",
    });
    if (row.harness_repair) {
      const record = row.harness_repair;
      delete row.harness_repair;
      row[strategyProfile(runtime.options.strategy).repairKey] = record;
    }
    return {
      ...row,
      confirmation,
      stable_failure_candidate: confirmation.stable,
      status: confirmation.stable
        ? "stable_failure_candidate"
        : isDiscoveryFailure(state.buggy.summary)
          ? "unstable_failure"
          : "latest_needs_repair",
    };
  };
  if (confirmation.stable) {
    if (onResult) onResult(resultRow());
    minimization = await minimizeAsset({
      runtime,
      packet,
      state,
      enabled: minimizationAllowed,
    });
    if (minimization.record?.use_minimized && minimization.state) {
      const minimizedConfirmation = confirmFailure(
        runtime,
        minimization.state,
        "minimized",
      );
      if (minimizedConfirmation.stable) {
        state = minimization.state;
        confirmation = minimizedConfirmation;
      }
    }
  }
  return resultRow();
}
