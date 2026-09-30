import fs from "node:fs";
import path from "node:path";

import { isCandidateAtomic } from "../acceptance.mjs";
import { assertSafeTargetAccess } from "../prompt/context.mjs";
import {
  acceptedCoverageGainForFile,
  applyAcceptedCoverageToGeneralCoverage,
  applyObservedCoverageToTargetLineCoverage,
  normalizeObservedCoverage,
  targetLineCoverageGain,
} from "../general_coverage.mjs";
import { ensureDir, readJson, writeJson, writeText } from "../json.mjs";
import {
  cleanupStaging,
  createStagingWorkspace,
  materializeProposal,
} from "../materialize.mjs";
import { parseProposalBatch } from "../prompt/proposal.mjs";
import { targetBinding, targetLoader } from "../test_seed.mjs";
import { loadTypeScript } from "../typescript_ast.mjs";
import {
  emptyAttempt,
  emptyCoverageDelta,
  mergeCoverageDelta,
  resultRow,
} from "./attempt.mjs";
import { remainingBudgetMs } from "./deadline.mjs";

function stripAnsi(text) {
  return String(text ?? "").replace(/\u001b\[[0-9;]*m/gu, "");
}

function readJsonIfPresent(file) {
  if (!file) {
    return null;
  }
  try {
    return fs.existsSync(file) ? readJson(file) : null;
  } catch {
    return null;
  }
}

function failureSnippets(validation) {
  const reporter = readJsonIfPresent(validation?.reporter_json);
  const snippets = [];
  for (const file of reporter?.testResults ?? []) {
    if (file?.message) {
      snippets.push(file.message);
    }
    for (const assertion of file?.assertionResults ?? []) {
      snippets.push(...(assertion?.failureMessages ?? []));
    }
  }
  return snippets
    .map((message) => stripAnsi(message).slice(-12000))
    .filter((message, index, items) =>
      message && items.indexOf(message) === index
    )
    .slice(0, 6);
}

export function validationRecord(validation, error = "") {
  return {
    status: validation?.status ?? "failed",
    cmd: validation?.cmd ?? [],
    cwd: validation?.cwd ?? "",
    exit_code: validation?.exit_code ?? null,
    timed_out: Boolean(validation?.timed_out),
    test_file: validation?.test_file ?? "",
    test_files: validation?.test_files ?? [],
    test_counts: validation?.test_counts ?? {},
    coverage_available: Boolean(validation?.coverage_json),
    error,
    failure_snippets: failureSnippets(validation),
    output_tail: stripAnsi(validation?.output_tail).slice(-8000),
  };
}

function invalidProposal({ error, proposalData, context }) {
  writeJson(path.join(context.sampleDir, "proposal-error.json"), {
    error: error.message,
    raw_proposal: proposalData,
  });
  return emptyAttempt(context, "proposal_invalid", error.message);
}

function rejectedStatus(rejected, budgetExhausted) {
  if (budgetExhausted) {
    return "time_budget";
  }
  if (
    rejected.length > 0 &&
    rejected.every((unit) => unit.status === "proposal_invalid")
  ) {
    return "proposal_invalid";
  }
  if (rejected.some((unit) => unit.status === "coverage_failed")) {
    return "coverage_failed";
  }
  return "validation_failed";
}

/**
 * Validate every independent test unit from one model proposal.
 *
 * Each unit runs in an isolated staging workspace. The default policy retains
 * every passing unit; candidate-atomic validation stops at the first rejection
 * and commits no unit unless the complete proposal passes with target progress.
 * Returned coverage states are tentative until the caller persists the files.
 */
export function validateProposal(proposalData, context) {
  ensureDir(context.sampleDir);
  const typescript = context.typescript ?? loadTypeScript(context.currentRoot);
  const candidateAtomic = isCandidateAtomic(context.acceptancePolicy);
  let proposal;
  try {
    proposal = parseProposalBatch(proposalData, {
      typescript,
      expectedNameSuffix: context.testNameSuffix,
    });
    writeJson(path.join(context.sampleDir, "proposal.json"), proposal);
  } catch (error) {
    return invalidProposal({ error, proposalData, context });
  }

  const candidateGeneralCoverage = structuredClone(
    context.generalCoverage ?? { files: {} },
  );
  const candidateTargetCoverage = structuredClone(context.targetCoverage);
  const accepted = [];
  const rejected = [];
  const acceptedTargetLines = new Set();
  let acceptedTargetBranchOutcomes = 0;
  const aggregateGeneral = emptyCoverageDelta();
  for (const [index, unit] of proposal.test_units.entries()) {
    if (remainingBudgetMs(context) <= 0) {
      break;
    }
    const unitId = `unit-${String(index + 1).padStart(3, "0")}`;
    const unitDir = path.join(context.sampleDir, "units", unitId);
    const testFile = context.generatedTestFile({
      attemptId: context.sampleId,
      objective: context.objective,
      unit,
      unitIndex: index,
    });
    const seedTestFile = context.objective.seed_test.test_file;
    const unitProposal = {
      ...unit,
      suite_id: proposal.suite_id,
      test_file: testFile,
    };
    ensureDir(unitDir);
    writeJson(path.join(unitDir, "proposal.json"), unitProposal);

    try {
      assertSafeTargetAccess({
        code: unit.append_code,
        targetBinding: targetBinding(
          context.objective.seed_test,
          context.targetImport,
        ),
        targetImport: context.targetImport,
        targetLoader: targetLoader(
          context.objective.seed_test,
          context.targetImport,
        ),
        typescript,
      });
    } catch (error) {
      rejected.push({
        unit_id: unitId,
        status: "proposal_invalid",
        test_file: testFile,
        error: error.message,
      });
      writeJson(path.join(unitDir, "proposal-error.json"), {
        error: error.message,
      });
      if (candidateAtomic) break;
      continue;
    }

    const stagingRoot = createStagingWorkspace({
      currentRoot: context.currentRoot,
      runDir: context.runDir,
      sampleId: `${context.sampleId}-${unitId}`,
    });
    try {
      const materialized = materializeProposal({
        projectRoot: stagingRoot,
        proposal: unitProposal,
        seedTestFile,
        seedTestSha256: context.objective.seed_test.sha256,
        targetModuleImport: context.targetImport,
        typescript,
      });
      const generatedPath = path.join(unitDir, "generated-test-file.ts");
      writeText(
        generatedPath,
        fs.readFileSync(materialized.materialized_path, "utf8"),
      );

      const remaining = remainingBudgetMs(context);
      if (remaining <= 0) {
        break;
      }
      const validation = context.validateGeneratedTest({
        projectRoot: stagingRoot,
        sourceProjectRoot: context.sourceProjectRoot,
        testFile,
        testName: unit.test_name,
        objective: context.objective,
        outDir: path.join(unitDir, "validation-run"),
        timeoutSeconds: Math.max(
          0.001,
          Math.min(context.timeoutSeconds, remaining / 1000),
        ),
        env: context.validationEnv,
      });
      const validationPath = path.join(unitDir, "validation.json");
      if (validation.status !== "passed") {
        const record = validationRecord(validation);
        writeJson(validationPath, record);
        rejected.push({
          unit_id: unitId,
          status: "validation_failed",
          test_file: testFile,
          validation_path: validationPath,
          error: validation.status,
          failure_snippets: record.failure_snippets,
          output_tail: record.output_tail,
        });
        if (candidateAtomic) break;
        continue;
      }
      if (!validation.coverage_json) {
        writeJson(
          validationPath,
          validationRecord(validation, "missing_coverage"),
        );
        rejected.push({
          unit_id: unitId,
          status: "coverage_failed",
          test_file: testFile,
          validation_path: validationPath,
          error: "missing_coverage",
        });
        if (candidateAtomic) break;
        continue;
      }

      const covered = normalizeObservedCoverage({
        coverageJson: validation.coverage_json,
        projectRoot: stagingRoot,
      });
      const newTargetLines = targetLineCoverageGain(
        candidateTargetCoverage,
        covered,
      );
      const targetGain = acceptedCoverageGainForFile(
        candidateGeneralCoverage,
        covered,
        context.objective.filepath,
      );
      const newTargetBranchOutcomes = targetGain.branch_updates.reduce(
        (sum, branch) => sum + branch.new_covered_outcomes,
        0,
      );
      const unitTargetGain = {
        covered_lines: newTargetLines,
        covered_branch_outcomes: newTargetBranchOutcomes,
      };
      // Global coverage remains the reporting state; local target coverage is
      // the progress state for this source/seed pair. Under passing_subset,
      // retain passing units even without target coverage gain.
      const generalUpdate = applyAcceptedCoverageToGeneralCoverage(
        candidateGeneralCoverage,
        covered,
      );
      applyObservedCoverageToTargetLineCoverage(
        candidateTargetCoverage,
        covered,
      );
      for (const line of newTargetLines) acceptedTargetLines.add(line);
      acceptedTargetBranchOutcomes += newTargetBranchOutcomes;
      const generalUpdatePath = path.join(
        unitDir,
        "general-coverage-update.json",
      );
      writeJson(generalUpdatePath, generalUpdate);
      mergeCoverageDelta(aggregateGeneral, generalUpdate);
      accepted.push({
        unit_id: unitId,
        status: "accepted",
        suite_id: proposal.suite_id,
        seed_test_file: seedTestFile,
        seed_test_sha256: context.objective.seed_test.sha256,
        removed_seed_test_count: materialized.removed_seed_test_count,
        removed_seed_suite_call_count:
          materialized.removed_seed_suite_call_count,
        test_name: unit.test_name,
        test_file: testFile,
        generated_test_file_path: generatedPath,
        validation_path: validationPath,
        general_coverage_update_path: generalUpdatePath,
        general_coverage_delta: generalUpdate,
        target_coverage_delta: unitTargetGain,
        target_coverage_progress:
          newTargetLines.length > 0 || newTargetBranchOutcomes > 0,
      });
      writeJson(validationPath, validationRecord(validation));
    } catch (error) {
      rejected.push({
        unit_id: unitId,
        status: "validation_failed",
        test_file: testFile,
        error: error.message,
      });
      writeJson(path.join(unitDir, "phase-error.json"), {
        error: error.message,
        stack: error.stack ?? "",
      });
      if (candidateAtomic) break;
    } finally {
      fs.rmSync(path.join(unitDir, "validation-run"), {
        recursive: true,
        force: true,
      });
      cleanupStaging(stagingRoot);
    }
  }

  const budgetExhausted = remainingBudgetMs(context) <= 0;
  const targetCoverageProgress =
    acceptedTargetLines.size > 0 || acceptedTargetBranchOutcomes > 0;
  if (
    candidateAtomic &&
    (accepted.length !== proposal.test_units.length || !targetCoverageProgress)
  ) {
    writeJson(
      path.join(context.sampleDir, "tentative-general-coverage-update.json"),
      aggregateGeneral,
    );
    const emptyUpdate = emptyCoverageDelta();
    writeJson(
      path.join(context.sampleDir, "general-coverage-update.json"),
      emptyUpdate,
    );
    const status = budgetExhausted
      ? "time_budget"
      : accepted.length !== proposal.test_units.length
        ? rejectedStatus(rejected, false)
        : "no_target_coverage";
    return {
      row: {
        ...resultRow(
          context,
          status,
          status === "no_target_coverage"
            ? "atomic candidate covered none of the target gaps"
            : (rejected[0]?.error ?? "atomic candidate did not fully pass"),
        ),
        proposal_path: path.join(context.sampleDir, "proposal.json"),
        accepted_units: [],
        rejected_units: rejected,
        withheld_passing_units: accepted,
        unvalidated_unit_count:
          proposal.test_units.length - accepted.length - rejected.length,
        time_budget_exhausted: budgetExhausted,
        general_coverage_delta: emptyUpdate,
        target_coverage_delta: {
          covered_lines: [],
          covered_branch_outcomes: 0,
        },
        target_coverage_progress: false,
      },
      generalCoverage: context.generalCoverage,
      targetCoverage: context.targetCoverage,
    };
  }

  writeJson(
    path.join(context.sampleDir, "general-coverage-update.json"),
    aggregateGeneral,
  );
  const status =
    accepted.length > 0
      ? "accepted"
      : rejectedStatus(rejected, budgetExhausted);
  const error =
    accepted.length > 0
      ? ""
      : status === "time_budget"
        ? "run time budget exhausted"
        : (rejected[0]?.error ?? "no accepted generated test units");
  return {
    row: {
      ...resultRow(context, status, error),
      proposal_path: path.join(context.sampleDir, "proposal.json"),
      accepted_units: accepted,
      rejected_units: rejected,
      unvalidated_unit_count:
        proposal.test_units.length - accepted.length - rejected.length,
      time_budget_exhausted: budgetExhausted,
      general_coverage_delta: aggregateGeneral,
      target_coverage_delta: {
        covered_lines: [...acceptedTargetLines].sort(
          (left, right) => left - right,
        ),
        covered_branch_outcomes: acceptedTargetBranchOutcomes,
      },
      target_coverage_progress:
        targetCoverageProgress,
    },
    generalCoverage: candidateGeneralCoverage,
    targetCoverage: candidateTargetCoverage,
  };
}
