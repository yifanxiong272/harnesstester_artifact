import path from "node:path";
import { CaseBudgetExceeded } from "./deadline.mjs";
import { ensureDir, writeJson } from "../support/json.mjs";
import { isDiscovery, strategyProfile } from "./options.mjs";
import { validationStatus } from "./reporting.mjs";
import { semanticFingerprint } from "./generation.mjs";
import {
  repairDisposition,
  repairHarnessAsset,
  skippedHarnessRepairRecord,
  minimizeAsset,
} from "./repair.mjs";
import { validateBuggyAsset, validateRevision } from "./session.mjs";

export async function runSampleAssets({
  runtime,
  packet,
  plan,
  sampleDir,
  assets,
  minimizationBudget,
  harnessRepairBudget,
  onProgress = null,
}) {
  const rows = [];
  let minimizationsUsed = 0;
  let harnessRepairsUsed = 0;
  for (const asset of assets) {
    const assetDir = path.join(sampleDir, "assets", asset.asset_id);
    try {
      const row = await runTargetAsset({
        runtime,
        packet,
        plan,
        asset,
        assetDir,
        minimizationAllowed: minimizationsUsed < minimizationBudget,
        harnessRepairAllowed: harnessRepairsUsed < harnessRepairBudget,
        onResult: onProgress ? (row) => onProgress([...rows, row]) : null,
      });
      if (row.minimization?.called) {
        minimizationsUsed += 1;
      }
      if (row[strategyProfile(runtime.options.strategy).repairKey]?.called) {
        harnessRepairsUsed += 1;
      }
      rows.push(row);
    } catch (error) {
      if (error instanceof CaseBudgetExceeded) throw error;
      rows.push(assetError(assetDir, error, asset.asset_id));
    }
    if (onProgress) onProgress(rows);
  }
  return rows;
}

export async function runTargetAsset({
  runtime,
  packet,
  plan,
  asset,
  assetDir,
  minimizationAllowed,
  harnessRepairAllowed,
  onResult = null,
}) {
  if (isDiscovery(runtime.options.evaluationMode)) {
    const { runDiscoveryAsset } = await import("./discovery.mjs");
    return runDiscoveryAsset({
      runtime,
      packet,
      plan,
      asset,
      assetDir,
      minimizationAllowed,
      harnessRepairAllowed,
      onResult,
    });
  }
  ensureDir(assetDir);
  // Parsed assets carry the validated plan's canonical boundary metadata.
  const baseState = validateBuggyAsset(runtime, asset, assetDir);
  const baseClassification = repairDisposition(baseState.buggy.summary);
  if (validationStatus(baseState.buggy.summary) === "passed") {
    return {
      ...assetResultRow(baseState, {
        originalAsset: asset,
        harnessRepair: {},
        minimization: {},
      }),
      status: "buggy_passed",
      bug_revealed: false,
    };
  }

  const variants = [
    validateFixedState({ runtime, state: baseState, variant: "base" }),
  ];
  const baseRevealed = variants[0].record.bug_revealed;
  let harnessRepair = {};
  if (!baseRevealed && baseClassification.needs_repair) {
    harnessRepair = harnessRepairAllowed
      ? await repairHarnessAsset({
          runtime,
          packet,
          plan,
          state: baseState,
        })
      : skippedHarnessRepairRecord(baseClassification);
    if (harnessRepair.state) {
      const repairedState = harnessRepair.state;
      if (isBuggyNonPass(repairedState.buggy.summary)) {
        variants.push(
          validateFixedState({
            runtime,
            state: repairedState,
            variant: "repaired",
          }),
        );
      }
    }
  }

  let chosen =
    variants.find((candidate) => candidate.record.bug_revealed) ||
    variants.find((candidate) => candidate.record.raw_reveal) ||
    variants[0];
  let minimization = {};

  const resultRow = () => {
    const row = assetResultRow(chosen.state, {
      originalAsset: asset,
      harnessRepair,
      minimization,
    });
    row.fixed = chosen.record.fixed;
    row.fixed_variants = variants.map((candidate) => candidate.record);
    row.status = chosen.record.status;
    row.bug_revealed = chosen.record.bug_revealed;
    row.raw_reveal = variants.some((candidate) => candidate.record.raw_reveal);
    if (row.harness_repair) {
      const repair = row.harness_repair;
      delete row.harness_repair;
      row[strategyProfile(runtime.options.strategy).repairKey] = repair;
    }
    return row;
  };

  if (chosen.record.bug_revealed) {
    // Persist confirmed evidence before optional work can exhaust the budget.
    if (onResult) onResult(resultRow());
    minimization = await minimizeAsset({
      runtime,
      packet,
      state: chosen.state,
      enabled: minimizationAllowed,
    });
    if (minimization.record?.use_minimized && minimization.state) {
      const minimized = validateFixedState({
        runtime,
        state: minimization.state,
        variant: "minimized",
      });
      variants.push(minimized);
      if (minimized.record.bug_revealed) {
        chosen = minimized;
      }
    }
  }

  return resultRow();
}

export function validateFixedState({ runtime, state, variant }) {
  const fixed = validateRevision({
    runtime,
    revisionKind: "fixed",
    asset: state.asset,
    assetDir: state.sampleDir,
  });
  const record = fixedVariantRecord(variant, state, fixed);
  if (record.raw_reveal) {
    const confirmation = confirmRevealCandidate({ runtime, state, variant });
    record.confirmation = confirmation;
    record.bug_revealed = confirmation.stable;
    record.status = confirmation.stable ? "revealed" : "unstable_reveal";
  }
  return { state, record };
}

export function isBuggyNonPass(summary = {}) {
  return validationStatus(summary) !== "passed";
}

export function confirmRevealCandidate({ runtime, state, variant }) {
  const runs = [];
  const count = Math.max(0, runtime.options.revealConfirmationRuns);
  for (let attempt = 1; attempt <= count; attempt += 1) {
    const confirmationDir = path.join(
      state.sampleDir,
      `${variant}-confirmation-${String(attempt).padStart(3, "0")}`,
    );
    ensureDir(confirmationDir);
    const [buggy, fixed] = ["buggy", "fixed"].map((revisionKind) =>
      validateRevision({
        runtime,
        revisionKind,
        asset: state.asset,
        assetDir: confirmationDir,
      }),
    );
    runs.push({
      attempt,
      passed:
        isBuggyNonPass(buggy.summary) &&
        validationStatus(fixed.summary) === "passed",
      test_asset_sha256: state.asset.test_asset_sha256 || "",
      buggy: buggy.summary,
      fixed: fixed.summary,
    });
  }
  return {
    required_runs: count,
    runs,
    stable: runs.length === count && runs.every((run) => run.passed),
  };
}

export function fixedVariantRecord(variant, state, fixed) {
  const rawReveal =
    isBuggyNonPass(state.buggy.summary) &&
    validationStatus(fixed.summary) === "passed";
  return {
    variant,
    variant_id: `${variant}:${state.asset.asset_id}`,
    asset_id: state.asset.asset_id,
    proposal_path: state.proposalPath,
    test_file: state.asset.test_file,
    test_asset_sha256: state.asset.test_asset_sha256 || "",
    buggy: state.buggy.summary,
    fixed: fixed.summary,
    status: rawReveal ? "reveal_candidate" : "fixed_failed",
    raw_reveal: rawReveal,
    bug_revealed: false,
  };
}

export function assetResultRow(
  state,
  { originalAsset, harnessRepair, minimization, outcomeKey = "buggy" },
) {
  const asset = state.asset;
  // Keep execution and ledger fields; candidate explanations stay in proposal.json.
  const row = {
    ...asset,
    proposal_path: state.proposalPath,
    semantic_fingerprint:
      asset.semantic_fingerprint || semanticFingerprint(asset),
    [outcomeKey]: state.buggy.summary,
  };
  for (const key of [
    "append_code",
    "mocking_plan",
    "supporting_evidence",
    "expected_observation",
    "novelty_from_prior",
    "bug_hypothesis",
  ])
    delete row[key];
  if (harnessRepair?.record) {
    row.harness_repair = harnessRepair.record;
  }
  if (minimization?.record) {
    row.minimization = minimization.record;
  }
  if (originalAsset?.asset_id && asset.asset_id !== originalAsset.asset_id) {
    row.original_asset_id = originalAsset.asset_id;
  }
  return row;
}

export function assetError(assetDir, error, assetId) {
  ensureDir(assetDir);
  const payload = { type: error.name, message: error.message };
  writeJson(path.join(assetDir, "error.json"), payload);
  return {
    asset_id: assetId,
    status: "error",
    bug_revealed: false,
    error: payload,
  };
}
