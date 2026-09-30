/** Configuration and strategy policy for paired probing or latest-revision discovery. */

import { DEFAULT_CASE_TIME_BUDGET_SECONDS } from "./deadline.mjs";

export const PAIRED_REVEAL_EVALUATION = "paired_reveal";
export const SINGLE_REVISION_DISCOVERY_EVALUATION = "single_revision_discovery";
export const TARGET_PROBING_TRACK = "target-probing";
export const TARGET_PROBE_LDH_STRATEGY = "target_probe_ldh";
export const TARGET_PROBE_CONTRACT_AGNOSTIC_STRATEGY =
  "target_probe_contract_agnostic";

function profile(allowContext, repairMode) {
  return Object.freeze({
    allowContext,
    repairMode,
    repairKey:
      repairMode === "generic" ? "contract_agnostic_repair" : "harness_repair",
  });
}

const PROFILES = new Map([
  [TARGET_PROBE_LDH_STRATEGY, profile(true, "harness")],
  [TARGET_PROBE_CONTRACT_AGNOSTIC_STRATEGY, profile(false, "generic")],
]);
export const TARGET_PROBE_STRATEGIES = [...PROFILES.keys()];

export function primaryCheckout(manifest = {}) {
  return manifest[`${primaryRevisionKind(manifest.evaluation_mode)}_checkout`];
}

export function isDiscovery(mode) {
  return mode === SINGLE_REVISION_DISCOVERY_EVALUATION;
}

export function primaryRevisionKind(mode) {
  return isDiscovery(mode) ? "latest" : "buggy";
}

export function revisionKinds(mode) {
  return isDiscovery(mode) ? ["latest"] : ["buggy", "fixed"];
}

export function normalizeTargetStrategy(strategy) {
  const value = String(strategy || "").trim();
  if (!PROFILES.has(value)) {
    throw new Error(`unsupported target-probing strategy: ${strategy}`);
  }
  return value;
}

export function strategyProfile(strategy) {
  return PROFILES.get(normalizeTargetStrategy(strategy));
}

export function runOptions(options) {
  const strategy = normalizeTargetStrategy(options.strategy);
  const profile = strategyProfile(strategy);
  const number = (
    key,
    fallback,
    alias = key.replace(/[A-Z]/gu, (c) => `_${c.toLowerCase()}`),
  ) => Number(options[key] ?? options[alias] ?? fallback);
  return {
    ...Object.fromEntries(
      ["model", "provider", "envFile", "modelClient", "validationRunner"]
        .filter((key) => options[key] !== undefined)
        .map((key) => [key, options[key]]),
    ),
    strategy,
    evaluationMode:
      options.evaluationMode ??
      options.evaluation_mode ??
      PAIRED_REVEAL_EVALUATION,
    directSamples: number("directSamples", 10),
    samples: number("samples", 10),
    softSamples: number("softSamples", 2),
    assetsPerSample: number("assetsPerSample", 5),
    contextRequests: profile.allowContext ? number("contextRequests", 1) : 0,
    minimizeBuggyFailuresPerSample: number("minimizeBuggyFailuresPerSample", 1),
    minimizationPreserveAttempts: number("minimizationPreserveAttempts", 1),
    minimizationFailureExcerptChars: number(
      "minimizationFailureExcerptChars",
      1000,
    ),
    harnessRepairAttempts: number("harnessRepairAttempts", 1),
    harnessRepairsPerSample: number("harnessRepairsPerSample", 1),
    harnessContextRequests:
      profile.repairMode === "harness"
        ? number("harnessContextRequests", 1)
        : 0,
    maxWorkflowErrors: number("maxWorkflowErrors", 2),
    maxRevealCandidates: number("maxRevealCandidates", 1),
    revealConfirmationRuns: number("revealConfirmationRuns", 2),
    timeoutSeconds: number("timeoutSeconds", 240, "timeout"),
    caseTimeBudgetSeconds: number(
      "caseTimeBudgetSeconds",
      DEFAULT_CASE_TIME_BUDGET_SECONDS,
    ),
    modelTimeoutMs: Number(options.modelTimeoutMs ?? 120_000),
    modelRetries: number("modelRetries", 5),
  };
}

export function validateRunOptions(options) {
  if (
    ![PAIRED_REVEAL_EVALUATION, SINGLE_REVISION_DISCOVERY_EVALUATION].includes(
      options.evaluationMode,
    )
  ) {
    throw new Error(`unsupported evaluation mode: ${options.evaluationMode}`);
  }
  if (
    !Number.isFinite(options.caseTimeBudgetSeconds) ||
    options.caseTimeBudgetSeconds < 0
  ) {
    throw new Error(
      "caseTimeBudgetSeconds must be a finite nonnegative number",
    );
  }
  const nonnegative = [
    "directSamples",
    "samples",
    "softSamples",
    "contextRequests",
    "minimizeBuggyFailuresPerSample",
    "minimizationPreserveAttempts",
    "harnessRepairAttempts",
    "harnessRepairsPerSample",
    "harnessContextRequests",
    "maxWorkflowErrors",
    "modelRetries",
  ];
  const positive = [
    "assetsPerSample",
    "maxRevealCandidates",
    "revealConfirmationRuns",
    "minimizationFailureExcerptChars",
  ];
  for (const key of [...nonnegative, ...positive]) {
    if (
      !Number.isInteger(options[key]) ||
      options[key] < (positive.includes(key) ? 1 : 0)
    ) {
      throw new Error(
        `${key} must be ${positive.includes(key) ? "a positive" : "a nonnegative"} integer`,
      );
    }
  }
  for (const key of ["timeoutSeconds", "modelTimeoutMs"]) {
    if (!Number.isFinite(options[key]) || options[key] <= 0) {
      throw new Error(`${key} must be greater than zero`);
    }
  }
}

export function validateRunPathPart(value, label) {
  if (!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,160}$/u.test(value)) {
    throw new Error(`unsafe ${label}: ${value}`);
  }
}
