import path from "node:path";
import { performance } from "node:perf_hooks";

import { generalCoverageForFile } from "../general_coverage.mjs";
import { ensureDir, writeJson, writeText } from "../json.mjs";
import {
  buildCoverageTargetPacket,
  coverageContinuationMessage,
  renderCoverageTargetPrompt,
} from "../prompt/prompts.mjs";
import { isContractDirected } from "../strategy.mjs";
import {
  emptyCoverageDelta,
  mergeCoverageDelta,
  persistAccepted,
  resultRow,
  targetImport,
  writeResult,
} from "./attempt.mjs";
import { remainingBudgetMs } from "./deadline.mjs";
import { runGenerationPass } from "./generation.mjs";
import { measureSeedCoverage, targetCoverageRecord } from "./seed_coverage.mjs";

const MAX_TARGET_PASSES = 3;

function passLabel(pass) {
  return String(pass).padStart(2, "0");
}

function passTestNameSuffix(iteration, pass) {
  const round = `_round_${String(iteration).padStart(3, "0")}`;
  return pass === 1 ? round : `${round}_pass_${passLabel(pass)}`;
}

function passUnits(units, pass) {
  const prefix = `pass-${passLabel(pass)}`;
  return (units ?? []).map((unit) => ({
    ...unit,
    generation_pass: pass,
    unit_id: `${prefix}-${unit.unit_id}`,
  }));
}

function passRecord(pass, attempt, startedAt, firstCallIndex, lastCallIndex) {
  return {
    pass,
    duration_ms:
      Math.round((performance.now() - startedAt) * 1000) / 1000,
    model_call_indexes:
      lastCallIndex >= firstCallIndex
        ? Array.from(
            { length: lastCallIndex - firstCallIndex + 1 },
            (_, index) => firstCallIndex + index,
          )
        : [],
    status: attempt.row.status,
    error: attempt.row.error ?? "",
    proposal_path: attempt.row.proposal_path ?? "",
    accepted_unit_count: attempt.row.accepted_units?.length ?? 0,
    rejected_unit_count: attempt.row.rejected_units?.length ?? 0,
    unvalidated_unit_count: Number(attempt.row.unvalidated_unit_count ?? 0),
    target_coverage_delta: attempt.row.target_coverage_delta ?? {
      covered_lines: [],
      covered_branch_outcomes: 0,
    },
    general_coverage_delta:
      attempt.row.general_coverage_delta ?? emptyCoverageDelta(),
    repair_status: attempt.row.repair_status ?? "",
    repair_input_rejected_unit_count: Number(
      attempt.row.repair_input_rejected_unit_count ?? 0,
    ),
    repair_proposal_path: attempt.row.repair_proposal_path ?? "",
  };
}

/**
 * Run one immutable source-file target through bounded residual-coverage passes,
 * one deterministic context request, and at most one repair across all passes.
 */
export async function runCoverageTarget(context) {
  const contractDirected = isContractDirected(context.strategy);
  if (!contractDirected) context = { ...context, repairContextRequests: 0 };
  ensureDir(context.sampleDir);
  const seed = measureSeedCoverage(context);
  if (seed.status !== "passed") {
    const row = {
      ...resultRow(context, seed.status, seed.error),
      seed_coverage: seed,
    };
    writeResult(context.sampleDir, row);
    return {
      row,
      generalCoverage: context.generalCoverage,
    };
  }
  let branchGaps = generalCoverageForFile(
    context.generalCoverage,
    context.objective.filepath,
  ).branch_gaps;
  if (seed.coverage.uncovered_lines.length === 0 && branchGaps.length === 0) {
    const row = {
      ...resultRow(context, "target_already_covered"),
      seed_coverage: seed.coverage_record,
      target_line_coverage: {
        initial: seed.coverage_record,
        final: seed.coverage_record,
        new_covered_lines: [],
      },
    };
    writeResult(context.sampleDir, row);
    return {
      row,
      generalCoverage: context.generalCoverage,
    };
  }
  const messages = [];
  const callState = { count: 0 };
  const acceptedNames = [];
  const acceptedUnits = [];
  const rejectedUnits = [];
  const passes = [];
  const aggregateCoverage = emptyCoverageDelta();
  const targetLines = new Set();
  let contextRequestAvailable = contractDirected;
  let repairAvailable = true;
  let generalCoverage = context.generalCoverage;
  let targetCoverage = seed.coverage;
  let targetBranchOutcomes = 0;
  let lastAttempt = null;
  let lastAcceptedProposalPath = "";

  for (let pass = 1; pass <= MAX_TARGET_PASSES; pass += 1) {
    if (
      (targetCoverage.uncovered_lines.length === 0 &&
        branchGaps.length === 0) ||
      remainingBudgetMs(context) <= 0
    ) {
      break;
    }
    if (pass > 1) {
      contextRequestAvailable = false;
    }
    const objective = context.objective;
    const label = passLabel(pass);
    const passSampleId =
      pass === 1 ? context.sampleId : `${context.sampleId}-pass-${label}`;
    const passDir =
      pass === 1
        ? context.sampleDir
        : path.join(context.sampleDir, "continuations", `pass-${label}`);
    ensureDir(passDir);
    const testNameSuffix = passTestNameSuffix(context.iteration, pass);
    const preview = context.generatedTestFile({
      attemptId: passSampleId,
      objective,
      unit: { label: "generated" },
      unitIndex: 0,
    });
    const passContext = {
      ...context,
      sampleId: passSampleId,
      sampleDir: passDir,
      objective,
      generalCoverage,
      targetCoverage,
      targetBranchGaps: branchGaps,
      generatedTestPreview: preview,
      targetModuleImport: targetImport(preview, objective),
      testNameSuffix,
    };
    const packet = buildCoverageTargetPacket(passContext);
    writeJson(path.join(passDir, "packet.json"), packet);
    writeJson(path.join(passDir, "retrieved-context.json"), []);
    if (pass === 1) {
      const prompt = renderCoverageTargetPrompt(packet, context.strategy);
      writeText(path.join(passDir, "prompt.md"), prompt);
      messages.push({ role: "user", content: prompt });
    } else {
      const continuation = coverageContinuationMessage({
        strategy: context.strategy,
        acceptedTestNames: acceptedNames,
        contextRequestAvailable,
        pass,
        targetCoverage,
        targetBranchGaps: branchGaps,
        testNameSuffix,
      });
      writeText(path.join(passDir, "continuation.md"), continuation);
      messages.push({ role: "user", content: continuation });
    }

    const passStartedAt = performance.now();
    const firstCallIndex = callState.count + 1;
    const result = await runGenerationPass({
      callState,
      context: passContext,
      contextRequestAvailable,
      messages,
      packet,
      repairAvailable,
    });
    lastAttempt = result.attempt;
    contextRequestAvailable = result.contextRequestAvailable;
    repairAvailable = result.repairAvailable;
    const passAccepted = passUnits(lastAttempt.row.accepted_units, pass);
    const passRejected = passUnits(lastAttempt.row.rejected_units, pass);
    if (passAccepted.length > 0) {
      lastAcceptedProposalPath = lastAttempt.row.proposal_path ?? "";
    }
    acceptedUnits.push(...passAccepted);
    rejectedUnits.push(...passRejected);
    acceptedNames.push(...passAccepted.map((unit) => unit.test_name));
    for (const line of lastAttempt.row.target_coverage_delta?.covered_lines ??
      []) {
      targetLines.add(Number(line));
    }
    targetBranchOutcomes += Number(
      lastAttempt.row.target_coverage_delta?.covered_branch_outcomes ?? 0,
    );
    mergeCoverageDelta(
      aggregateCoverage,
      lastAttempt.row.general_coverage_delta,
    );
    passes.push(
      passRecord(
        pass,
        lastAttempt,
        passStartedAt,
        firstCallIndex,
        callState.count,
      ),
    );

    if (lastAttempt.row.status !== "accepted") {
      break;
    }
    generalCoverage = lastAttempt.generalCoverage;
    targetCoverage = lastAttempt.targetCoverage;
    if (!lastAttempt.row.target_coverage_progress) {
      break;
    }
    branchGaps = generalCoverageForFile(
      generalCoverage,
      context.objective.filepath,
    ).branch_gaps;
  }

  const accepted = acceptedUnits.length > 0;
  const budgetExhausted = remainingBudgetMs(context) <= 0;
  const status = accepted
    ? "accepted"
    : (lastAttempt?.row.status ??
      (budgetExhausted ? "time_budget" : "no_target_coverage"));
  let attempt = {
    row: {
      ...resultRow(context, status, accepted ? "" : lastAttempt?.row.error),
      proposal_path: accepted
        ? lastAcceptedProposalPath
        : (lastAttempt?.row.proposal_path ?? ""),
      accepted_units: acceptedUnits,
      rejected_units: rejectedUnits,
      unvalidated_unit_count: passes.reduce(
        (sum, item) => sum + item.unvalidated_unit_count,
        0,
      ),
      time_budget_exhausted: budgetExhausted,
      general_coverage_delta: aggregateCoverage,
      target_coverage_delta: {
        covered_lines: [...targetLines].sort((left, right) => left - right),
        covered_branch_outcomes: targetBranchOutcomes,
      },
      target_coverage_progress:
        targetLines.size > 0 || targetBranchOutcomes > 0,
      seed_coverage: seed.coverage_record,
      target_line_coverage: {
        initial: seed.coverage_record,
        final: targetCoverageRecord(targetCoverage),
        new_covered_lines: [...targetLines].sort(
          (left, right) => left - right,
        ),
      },
      generation_pass_limit: MAX_TARGET_PASSES,
      passes,
    },
    generalCoverage: accepted ? generalCoverage : context.generalCoverage,
    targetCoverage,
  };
  if (accepted) {
    attempt = persistAccepted(context, attempt);
  }
  writeResult(context.sampleDir, attempt.row);
  return attempt;
}
