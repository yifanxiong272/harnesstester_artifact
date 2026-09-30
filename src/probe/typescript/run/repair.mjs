import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { messageContent } from "./client.mjs";
import { CaseBudgetExceeded } from "./deadline.mjs";
import {
  failureTextFromSummary,
  parseHarnessRepairDecision,
  projectTracebackContext,
} from "../prompt/context.mjs";
import { ensureDir, writeJson, writeText } from "../support/json.mjs";
import {
  renderTargetHarnessRepairContextRequestPrompt,
  renderTargetHarnessRepairPrompt,
  renderTargetContractAgnosticRepairPrompt,
  renderTargetProbeMinimizePrompt,
} from "../prompt/prompts.mjs";
import {
  parseProposalPartial,
  validateMinimizedCodeIsSubset,
} from "../prompt/proposal.mjs";
import { primaryCheckout, strategyProfile } from "./options.mjs";
import {
  compactText,
  validationFailureKind,
  validationStatus,
} from "./reporting.mjs";
import {
  resolveContextForManifest,
  proposalParseOptions,
} from "./generation.mjs";
import {
  completeAndRecord,
  rawPayload,
  validateBuggyAsset,
} from "./session.mjs";

export function repairDisposition(summary = {}) {
  const outcome = validationStatus(summary);
  return {
    outcome,
    needs_repair: outcome === "needs_repair",
    reason:
      summary.classification_reason ||
      (outcome === "needs_repair" ? "non_assertion_failure" : ""),
  };
}

export async function repairHarnessAsset({
  runtime,
  packet,
  plan,
  state,
}) {
  const profile = strategyProfile(runtime.options.strategy);
  let classification = repairDisposition(state.buggy.summary);
  if (runtime.options.harnessRepairAttempts <= 0) {
    return {
      record: {
        called: false,
        enabled: false,
        classification,
      },
    };
  }
  const assetDir = state.sampleDir;
  let last = { record: { called: false, classification } };
  const attempts = [];
  for (
    let attempt = 1;
    attempt <= runtime.options.harnessRepairAttempts;
    attempt += 1
  ) {
    const repairDir = path.join(
      assetDir,
      `${profile.repairKey.replaceAll("_", "-")}-${String(attempt).padStart(3, "0")}`,
    );
    ensureDir(repairDir);
    const tracebackContext =
      profile.repairMode === "harness"
        ? repairTracebackContext(runtime.manifest, state.buggy.summary)
        : [];
    if (profile.repairMode === "harness") {
      writeJson(
        path.join(repairDir, "traceback-context.json"),
        tracebackContext,
      );
    }
    const failureSummary = buggyFailureSummary(state.buggy.summary, 8000);
    writeJson(path.join(repairDir, "failure-packet.json"), {
      summary: failureSummary,
      failure_evidence: failureTextFromSummary(state.buggy.summary),
      project_frames: tracebackContext,
    });
    const decisionResult = await generateHarnessRepairDecision({
      runtime,
      packet,
      plan,
      asset: state.asset,
      buggySummary: failureSummary,
      tracebackContext,
      repairDir,
    });
    const { decision } = decisionResult;
    const attemptRecord = {
      attempt,
      classification,
      ...decisionResult.record,
    };
    if (decision.action === "retain_original") {
      const record = { ...attemptRecord, decision: "retain_original" };
      return recordRepairAttempt(record, attempts);
    }

    let promptPath = decisionResult.record.prompt_path;
    let rawPath = decisionResult.record.raw_path;
    let proposalContent = decision.proposal || {};
    if (decision.action === "request_context") {
      const prompt = renderTargetHarnessRepairPrompt(packet, {
        plan,
        asset: state.asset,
        buggySummary: failureSummary,
        tracebackContext,
        repairContext: decisionResult.retrieved_context,
      });
      promptPath = path.join(repairDir, "repair.prompt.md");
      writeText(promptPath, prompt);
      rawPath = path.join(repairDir, "repair.raw.json");
      const response = await completeAndRecord(runtime, prompt, rawPath);
      proposalContent = messageContent(response);
    }
    const baseRecord = {
      ...attemptRecord,
      prompt_path: promptPath,
      traceback_context_path:
        profile.repairMode === "harness"
          ? path.join(repairDir, "traceback-context.json")
          : "",
    };
    try {
      const { proposal, errors } = parseProposalPartial(proposalContent, {
        ...proposalParseOptions(runtime, packet, 1, plan),
        allowEmptyAssets: true,
      });
      if (proposal.assets.length === 0) {
        if (errors.length > 0) {
          throw new Error(
            `repair proposal has no valid assets: ${errors.map((error) => error.message).join("; ")}`,
          );
        }
        const record = {
          ...baseRecord,
          raw_path: rawPath,
          decision: "retain_original",
        };
        return recordRepairAttempt(record, attempts);
      }
      validateHarnessRepairPreservesIntent(state.asset, proposal.assets[0]);
      const repaired = normalizeHarnessRepairedAsset(
        state.asset,
        proposal.assets[0],
      );
      const repairedState = validateBuggyAsset(runtime, repaired, repairDir, errors);
      const record = {
        ...baseRecord,
        raw_path: rawPath,
        proposal_path: repairedState.proposalPath,
        sample_dir: repairDir,
        decision: "repair",
      };
      last = recordRepairAttempt(record, attempts, repairedState);
      classification = repairDisposition(repairedState.buggy.summary);
      if (!classification.needs_repair) {
        return last;
      }
      state = repairedState;
    } catch (error) {
      if (error instanceof CaseBudgetExceeded) throw error;
      const record = {
        ...baseRecord,
        error: { type: error.name, message: error.message },
      };
      last = recordRepairAttempt(record, attempts);
    }
  }
  return last;
}

export function skippedHarnessRepairRecord(classification) {
  return {
    record: {
      called: false,
      enabled: false,
      classification,
      skipped_reason: "sample_harness_repair_budget_exhausted",
    },
  };
}

export async function generateHarnessRepairDecision({
  runtime,
  packet,
  plan,
  asset,
  buggySummary,
  tracebackContext,
  repairDir,
}) {
  const generic =
    strategyProfile(runtime.options.strategy).repairMode === "generic";
  const maxRequests = generic
    ? 0
    : Math.max(0, runtime.options.harnessContextRequests);
  const render = generic
    ? renderTargetContractAgnosticRepairPrompt
    : renderTargetHarnessRepairContextRequestPrompt;
  const prompt = render(packet, {
    plan,
    asset,
    buggySummary,
    tracebackContext,
    maxContextRequests: maxRequests,
  });
  const promptPath = path.join(repairDir, "repair-decision.prompt.md");
  writeText(promptPath, prompt);
  const rawPath = path.join(repairDir, "repair-decision.raw.json");
  let decision;
  let errors;
  let decisionError = null;
  try {
    const response = await completeAndRecord(runtime, prompt, rawPath);
    ({ decision, errors } = parseHarnessRepairDecision(
      messageContent(response),
      { maxRequests },
    ));
  } catch (error) {
    decisionError = { type: error.name, message: error.message };
    if (!fs.existsSync(rawPath)) {
      writeJson(rawPath, rawPayload(runtime, { error: decisionError }));
    }
    if (error instanceof CaseBudgetExceeded) throw error;
    // Failed calls and rejected replies still consume the repair budget.
    decision = {
      action: "retain_original",
      diagnosis: "repair decision unavailable",
    };
    errors = [decisionError];
  }
  writeJson(path.join(repairDir, "repair-decision.json"), {
    action: decision.action,
    diagnosis: decision.diagnosis || "",
    request_count: decision.requests?.length || 0,
    ...(errors.length ? { parse_errors: errors } : {}),
  });
  let requestedContext = { requests: [] };
  if (decision.action === "request_context") {
    requestedContext = resolveContextForManifest({
      manifest: runtime.manifest,
      requests: decision.requests,
      maxRequests,
      outPath: path.join(repairDir, "requested-context.json"),
    });
  }
  const retrieved = {
    traceback_context: tracebackContext,
    requested_context: requestedContext,
    module_contracts: generic ? [] : packet.module_contracts || [],
  };
  writeJson(path.join(repairDir, "retrieved-context.json"), retrieved);
  return {
    record: {
      prompt_path: promptPath,
      raw_path: rawPath,
      ...(decisionError ? { error: decisionError } : {}),
      context_request_path: path.join(repairDir, "repair-decision.json"),
      retrieved_context_path: path.join(repairDir, "retrieved-context.json"),
    },
    decision,
    retrieved_context: retrieved,
  };
}

export function repairTracebackContext(manifest, summary) {
  const checkout = primaryCheckout(manifest)?.path;
  const sourceRoots = Array.isArray(manifest.source_roots)
    ? manifest.source_roots
    : [];
  if (!checkout || sourceRoots.length === 0) {
    return [];
  }
  return projectTracebackContext({
    projectRoot: checkout,
    sourceRoots,
    failureText: failureTextFromSummary(summary),
  });
}

export function normalizeHarnessRepairedAsset(original, repaired) {
  return {
    ...original,
    asset_id: repaired.asset_id || original.asset_id,
    append_code: repaired.append_code,
    test_asset_sha256: crypto
      .createHash("sha256")
      .update(`${original.test_file}\0${repaired.append_code}`)
      .digest("hex"),
    input_construction:
      repaired.input_construction || original.input_construction,
    mocking_plan: repaired.mocking_plan,
  };
}

export function validateHarnessRepairPreservesIntent(original, repaired) {
  for (const field of [
    "test_file",
    "boundary_id",
    "public_entrypoint_id",
    "oracle_mode",
  ]) {
    if (repaired[field] !== original[field]) {
      throw new Error(`harness repair changed canonical ${field}`);
    }
  }
  if (
    JSON.stringify(repaired.target_unit_ids) !==
    JSON.stringify(original.target_unit_ids)
  ) {
    throw new Error("harness repair changed canonical target_unit_ids");
  }
}

export async function minimizeAsset({
  runtime,
  packet,
  state,
  enabled,
}) {
  if (!enabled || validationStatus(state.buggy.summary) !== "assertion_failed") {
    return {};
  }
  const buggySummary = buggyFailureSummary(
    state.buggy.summary,
    runtime.options.minimizationFailureExcerptChars,
  );
  const attempt = (directory, retryContext = null) =>
    runMinimizationAttempt({
      runtime,
      packet,
      asset: state.asset,
      buggySummary,
      directory,
      retryContext,
    });
  const first = await attempt(state.sampleDir);
  if (
    first.record?.use_minimized ||
    first.record?.minimized_buggy_status !== "buggy_passed" ||
    runtime.options.minimizationPreserveAttempts <= 0
  ) {
    return first;
  }
  const retry = await attempt(
    path.join(state.sampleDir, "minimization-preserve-001"),
    minimizationRetryContext(first),
  );
  const attempts = [first.record || {}, retry.record || {}];
  const target = retry.record?.use_minimized ? retry : first;
  target.record = {
    ...(target.record || {}),
    attempts,
  };
  return target;
}

export async function runMinimizationAttempt({
  runtime,
  packet,
  asset,
  buggySummary,
  directory,
  retryContext = null,
}) {
  const promptPath = path.join(directory, "minimization.prompt.md");
  const rawPath = path.join(directory, "minimization.raw.json");
  const outputDir = path.join(directory, "minimized");
  const prompt = renderTargetProbeMinimizePrompt(packet, {
    asset,
    buggySummary,
    retryContext,
  });
  writeText(promptPath, prompt);
  const baseRecord = {
    called: true,
    prompt_path: promptPath,
    use_minimized: false,
  };
  try {
    const response = await completeAndRecord(runtime, prompt, rawPath);
    const { proposal, errors } = parseProposalPartial(
      messageContent(response),
      proposalParseOptions(runtime, packet, 1, {
        boundary_plan: packet.boundary_plan || [],
      }),
    );
    const minimized = proposal.assets[0];
    validateMinimizedMetadata(asset, minimized);
    validateMinimizedCodeIsSubset(asset, minimized, {
      projectRoot: primaryCheckout(runtime.manifest)?.path || "",
    });
    const state = validateBuggyAsset(runtime, minimized, outputDir, errors);
    const status = minimizedBuggyStatus(state.buggy);
    return {
      record: {
        ...baseRecord,
        raw_path: rawPath,
        proposal_path: state.proposalPath,
        sample_dir: outputDir,
        minimized_buggy_status: status,
        use_minimized: status === "buggy_failed_candidate",
      },
      state,
    };
  } catch (error) {
    if (error instanceof CaseBudgetExceeded) throw error;
    return {
      record: {
        ...baseRecord,
        error: { type: error.name, message: error.message },
      },
    };
  }
}

export function validateMinimizedMetadata(original, minimized) {
  for (const field of [
    "boundary_id",
    "public_entrypoint_id",
    "test_intent",
    "independent_oracle",
    "supporting_evidence",
    "expected_observation",
    "oracle_family",
    "novelty_from_prior",
    "bug_hypothesis",
    "input_construction",
    "observable_oracle",
    "primary_oracle",
    "oracle_mode",
    "test_file",
  ]) {
    if (minimized[field] !== original[field]) {
      throw new Error(`minimization changed ${field}`);
    }
  }
  const originalUnits = [...(original.target_unit_ids || [])].sort();
  const minimizedUnits = [...(minimized.target_unit_ids || [])].sort();
  if (JSON.stringify(originalUnits) !== JSON.stringify(minimizedUnits)) {
    throw new Error("minimization changed target_unit_ids");
  }
}

export function minimizedBuggyStatus(validation) {
  const status = validationStatus(validation.summary);
  if (status === "assertion_failed") {
    return "buggy_failed_candidate";
  }
  return status === "passed" ? "buggy_passed" : "buggy_needs_repair";
}

export function minimizationRetryContext(result) {
  return {
    previous_asset: result.state?.asset || {},
    previous_buggy_status: result.record?.minimized_buggy_status || "",
    previous_buggy_summary: buggyFailureSummary(
      result.state?.buggy.summary || {},
      800,
    ),
  };
}

/** Retain ordered attempt evidence and the current validated state. */
export function recordRepairAttempt(record, attempts, state) {
  attempts.push(record);
  return {
    record: { called: true, attempts },
    ...(state === undefined ? {} : { state }),
  };
}

export function buggyFailureSummary(summary, failureExcerptChars) {
  return {
    phase: summary.phase || "",
    exit_code: summary.exit_code,
    timed_out: Boolean(summary.timed_out),
    status: validationStatus(summary),
    classification_source: summary.classification_source || "",
    classification_reason: summary.classification_reason || "",
    failed_nodeids: summary.failed_nodeids || [],
    failure_kind: validationFailureKind(summary),
    failure_excerpt: compactText(
      summary.failure_excerpt || "",
      failureExcerptChars,
    ),
    diagnostics: compactText(
      JSON.stringify(summary.diagnostics || {}),
      failureExcerptChars,
    ),
    output_tail: compactText(summary.output_tail || "", failureExcerptChars),
  };
}
