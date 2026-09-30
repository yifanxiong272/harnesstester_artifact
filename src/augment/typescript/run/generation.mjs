import path from "node:path";

import { failureEvidence } from "../../../common/failure_context/typescript.mjs";
import { isCandidateAtomic } from "../acceptance.mjs";
import { chatCompletion, messageContent } from "./client.mjs";
import { resolveContextRequests, tracebackContextFromFailure } from "../prompt/context.mjs";
import { generalCoverageForFile } from "../general_coverage.mjs";
import { ensureDir, writeJson, writeText } from "../json.mjs";
import { contextReply, repairMessage } from "../prompt/prompts.mjs";
import { parseModelResponse } from "../prompt/proposal.mjs";
import { isContractDirected } from "../strategy.mjs";
import {
  emptyAttempt,
  emptyCoverageDelta,
  mergeCoverageDelta,
  validationContext,
  writeResult,
} from "./attempt.mjs";
import {
  TimeBudgetExceeded,
  remainingBudgetMs,
  requireBudget,
  withinBudget,
} from "./deadline.mjs";
import { validateProposal } from "./validate.mjs";

class ModelCallError extends Error {
  constructor(error) {
    super(error.message, { cause: error });
    this.retryable = error.retryable !== false;
  }
}

async function completeConversation(context, messages, callIndex, outputDir) {
  let response;
  try {
    const complete = context.completeModel ?? chatCompletion;
    response = await withinBudget(context, (totalTimeoutMs) =>
      complete({
        messages,
        provider: context.provider,
        model: context.model,
        env: context.modelEnv,
        totalTimeoutMs,
      }),
    );
  } catch (error) {
    if (
      error instanceof TimeBudgetExceeded ||
      remainingBudgetMs(context) <= 0
    ) {
      throw new TimeBudgetExceeded();
    }
    throw new ModelCallError(error);
  }
  writeJson(path.join(outputDir, `response-${callIndex}.raw.json`), {
    provider: context.provider,
    model: context.model,
    response,
  });
  const content = messageContent(response);
  messages.push({ role: "assistant", content });
  writeJson(path.join(context.sampleDir, "conversation.json"), { messages });
  return parseModelResponse(content);
}

function failureForRepair(row) {
  const rejected = row.rejected_units ?? [];
  const failure = {
    status: row.status,
    error: row.error ?? "",
    failure_snippets: rejected
      .flatMap((unit) => unit.failure_snippets ?? [])
      .slice(0, 6),
    output_tail: rejected
      .flatMap((unit) => [unit.error ?? "", unit.output_tail ?? ""])
      .filter(Boolean)
      .join("\n"),
  };
  return {
    ...failure,
    failure_evidence: failureEvidence(
      [failure.error, ...failure.failure_snippets, failure.output_tail],
      { maxChars: 20000 },
    ),
  };
}

function validateResponse(context, response, outputDir, attemptId) {
  if (response.action !== "propose_test") {
    throw new Error("only one context request batch is allowed");
  }
  const attempt = validateProposal(
    response.proposal,
    validationContext(
      context,
      attemptId,
      outputDir,
      context.targetModuleImport,
    ),
  );
  writeResult(outputDir, attempt.row);
  return attempt;
}

function repairUnits(units) {
  return (units ?? []).map((unit) => ({
    ...unit,
    unit_id: `repair-001-${unit.unit_id}`,
  }));
}

function mergeRepairedAttempt(initial, repaired) {
  const acceptedUnits = [
    ...(initial.row.accepted_units ?? []),
    ...repairUnits(repaired.row.accepted_units),
  ];
  const coveredLines = new Set([
    ...(initial.row.target_coverage_delta?.covered_lines ?? []),
    ...(repaired.row.target_coverage_delta?.covered_lines ?? []),
  ]);
  const generalCoverageDelta = emptyCoverageDelta();
  mergeCoverageDelta(
    generalCoverageDelta,
    initial.row.general_coverage_delta,
  );
  mergeCoverageDelta(
    generalCoverageDelta,
    repaired.row.general_coverage_delta,
  );

  return {
    row: {
      ...initial.row,
      status: "accepted",
      error: "",
      accepted_units: acceptedUnits,
      rejected_units: repairUnits(repaired.row.rejected_units),
      unvalidated_unit_count: Number(
        repaired.row.unvalidated_unit_count ?? 0,
      ),
      time_budget_exhausted: Boolean(repaired.row.time_budget_exhausted),
      general_coverage_delta: generalCoverageDelta,
      target_coverage_delta: {
        covered_lines: [...coveredLines].sort((left, right) => left - right),
        covered_branch_outcomes:
          Number(
            initial.row.target_coverage_delta?.covered_branch_outcomes ?? 0,
          ) +
          Number(
            repaired.row.target_coverage_delta?.covered_branch_outcomes ?? 0,
          ),
      },
      target_coverage_progress:
        Boolean(initial.row.target_coverage_progress) ||
        Boolean(repaired.row.target_coverage_progress),
      repair_input_rejected_unit_count: initial.row.rejected_units?.length ?? 0,
      repair_proposal_path: repaired.row.proposal_path ?? "",
      repair_status: repaired.row.status,
    },
    generalCoverage: repaired.generalCoverage,
    targetCoverage: repaired.targetCoverage,
  };
}

/** Generate and validate one pass, consuming at most one target-wide repair. */
export async function runGenerationPass({
  callState,
  context,
  contextRequestAvailable,
  messages,
  packet,
  repairAvailable,
}) {
  let attempt;
  let repairAttempted = false;
  try {
    let response = await completeConversation(
      context,
      messages,
      ++callState.count,
      context.sampleDir,
    );
    if (response.action === "request_context") {
      if (!contextRequestAvailable) {
        throw new Error("only one context request batch is allowed");
      }
      contextRequestAvailable = false;
      requireBudget(context);
      const records = resolveContextRequests({
        projectRoot: context.currentRoot,
        objective: context.objective,
        requests: response.requests,
        visibleContext: [...packet.source_context, packet.seed_test],
        typescript: context.typescript,
      });
      writeJson(
        path.join(context.sampleDir, "retrieved-context.json"),
        records,
      );
      messages.push({ role: "user", content: contextReply(records) });
      response = await completeConversation(
        context,
        messages,
        ++callState.count,
        context.sampleDir,
      );
    }
    attempt = validateResponse(
      context,
      response,
      context.sampleDir,
      context.sampleId,
    );
  } catch (error) {
    if (error instanceof TimeBudgetExceeded) {
      attempt = emptyAttempt(context, "time_budget", error.message);
    } else {
      if (error instanceof ModelCallError && !error.retryable) {
        throw error.cause ?? error;
      }
      const status =
        error instanceof ModelCallError ? "model_failed" : "generation_failed";
      attempt = emptyAttempt(context, status, error.message);
    }
    writeJson(path.join(context.sampleDir, "phase-error.json"), {
      error: error.message,
      stack: error.stack ?? "",
    });
  }

  const hasRejectedUnits = (attempt.row.rejected_units?.length ?? 0) > 0;
  const hasCoverageRedundantUnits =
    !isCandidateAtomic(context.acceptancePolicy) &&
    (attempt.row.accepted_units ?? []).some(
      (unit) => !unit.target_coverage_progress,
    );
  if (
    !["model_failed", "time_budget"].includes(attempt.row.status) &&
    (attempt.row.status !== "accepted" ||
      hasRejectedUnits ||
      hasCoverageRedundantUnits) &&
    repairAvailable &&
    remainingBudgetMs(context) > 0
  ) {
    repairAttempted = true;
    const initialAttempt = attempt;
    const repairDir = path.join(context.sampleDir, "repair");
    ensureDir(repairDir);
    const failure = failureForRepair(initialAttempt.row);
    const traceback = isContractDirected(context.strategy)
      ? tracebackContextFromFailure({
          projectRoot: context.currentRoot,
          failure,
          sourceRoots: context.sourceRoots ?? ["."],
          typescript: context.typescript,
        })
      : [];
    const repairContext = {
      ...context,
      generalCoverage: initialAttempt.generalCoverage,
      targetCoverage: initialAttempt.targetCoverage,
      targetBranchGaps: generalCoverageForFile(
        initialAttempt.generalCoverage,
        context.objective.filepath,
      ).branch_gaps,
    };
    const feedback = repairMessage(
      repairContext,
      initialAttempt.row,
      failure,
      traceback,
      Number(context.repairContextRequests ?? 0),
    );
    writeJson(path.join(repairDir, "failure-packet.json"), {
      failure,
      project_frames: traceback,
    });
    writeJson(path.join(repairDir, "traceback-context.json"), traceback);
    writeJson(path.join(repairDir, "retrieved-context.json"), []);
    writeText(path.join(repairDir, "feedback.md"), feedback);
    messages.push({ role: "user", content: feedback });
    try {
      let response = await completeConversation(
        context,
        messages,
        ++callState.count,
        repairDir,
      );
      writeJson(path.join(repairDir, "decision.json"), {
        action: response.action,
        diagnosis: response.diagnosis ?? "",
        request_count: response.requests?.length ?? 0,
      });
      if (response.action === "request_context") {
        const requestLimit = Number(context.repairContextRequests ?? 0);
        if (requestLimit <= 0) {
          throw new Error("repair-time context requests are disabled");
        }
        requireBudget(context);
        const records = resolveContextRequests({
          projectRoot: context.currentRoot,
          objective: context.objective,
          requests: response.requests.slice(0, requestLimit),
          visibleContext: [
            ...packet.source_context,
            packet.seed_test,
            ...traceback,
          ],
          typescript: context.typescript,
        });
        writeJson(path.join(repairDir, "retrieved-context.json"), records);
        messages.push({ role: "user", content: contextReply(records) });
        response = await completeConversation(
          context,
          messages,
          ++callState.count,
          repairDir,
        );
      }
      const repairedAttempt = validateResponse(
        repairContext,
        response,
        repairDir,
        `${context.sampleId}-repair-001`,
      );
      attempt =
        initialAttempt.row.status === "accepted"
          ? mergeRepairedAttempt(initialAttempt, repairedAttempt)
          : repairedAttempt;
    } catch (error) {
      writeJson(path.join(repairDir, "phase-error.json"), {
        error: error.message,
        stack: error.stack ?? "",
      });
      if (error instanceof TimeBudgetExceeded) {
        attempt = initialAttempt;
        attempt.row.repair_status = "time_budget";
        attempt.row.time_budget_exhausted = true;
      } else if (error instanceof ModelCallError) {
        if (!error.retryable) {
          throw error.cause ?? error;
        }
        if (initialAttempt.row.status === "accepted") {
          attempt = initialAttempt;
          attempt.row.repair_status = "model_failed";
          attempt.row.repair_error = error.message;
        } else {
          attempt = emptyAttempt(context, "model_failed", error.message);
        }
      } else {
        attempt = initialAttempt;
        attempt.row.repair_status = "repair_generation_failed";
        attempt.row.repair_error = error.message;
      }
    }
  }

  return {
    attempt,
    contextRequestAvailable,
    repairAvailable: repairAvailable && !repairAttempted,
  };
}
