import path from "node:path";

import { writeJson } from "../json.mjs";
import { persistAcceptedGeneratedFileFromPath } from "../materialize.mjs";
import { siblingGeneratedTest } from "../test_seed.mjs";

export function resultRow(context, status, error = "") {
  return {
    iteration: context.iteration,
    sample_id: context.sampleId,
    objective_id: context.objective.objective_id,
    unit_id: context.objective.unit_id,
    filepath: context.objective.filepath,
    seed_test_file: context.objective.seed_test.test_file,
    acceptance_policy: context.acceptancePolicy,
    status,
    sample_dir: context.sampleDir,
    error,
  };
}

export function writeResult(sampleDir, row) {
  writeJson(path.join(sampleDir, "sample-result.json"), row);
}

function slug(value, fallback = "unit") {
  return (
    String(value ?? fallback)
      .toLowerCase()
      .replace(/[^a-z0-9]+/gu, "-")
      .replace(/^-|-$/gu, "")
      .slice(0, 36) || fallback
  );
}

export function generatedTestFile({ attemptId, objective, unit, unitIndex }) {
  const objectiveLabel = String(
    objective.unit_id ?? objective.objective_id ?? "objective",
  )
    .replace(/[^a-zA-Z0-9]+/gu, "")
    .slice(-12)
    .toLowerCase();
  const name = `test-augment-${attemptId}-u${String(unitIndex + 1).padStart(3, "0")}-${objectiveLabel}-${slug(unit.label)}`;
  return siblingGeneratedTest(objective.seed_test.test_file, name);
}

export function targetImport(testFile, objective) {
  const source = String(objective.filepath).replace(/\.tsx?$/u, ".js");
  const relative = path.posix.relative(path.posix.dirname(testFile), source);
  return relative.startsWith(".") ? relative : `./${relative}`;
}

export function validationContext(context, id, outputDir, targetModuleImport) {
  return {
    sampleId: id,
    sampleDir: outputDir,
    iteration: context.iteration,
    objective: context.objective,
    generalCoverage: context.generalCoverage,
    targetCoverage: context.targetCoverage,
    runDir: context.runDir,
    currentRoot: context.currentRoot,
    sourceProjectRoot: context.sourceProjectRoot,
    targetImport: targetModuleImport,
    validateGeneratedTest: context.validateGeneratedTest,
    acceptancePolicy: context.acceptancePolicy,
    timeoutSeconds: context.timeoutSeconds,
    remainingTimeMs: context.remainingTimeMs,
    validationEnv: context.validationEnv,
    generatedTestFile: context.generatedTestFile,
    typescript: context.typescript,
    testNameSuffix: context.testNameSuffix,
  };
}

export function persistAccepted(context, attempt) {
  if (attempt.row.status !== "accepted") return attempt;

  const units = attempt.row.accepted_units.map((unit) => ({
    ...unit,
    ...persistAcceptedGeneratedFileFromPath({
      runDir: context.runDir,
      currentRoot: context.currentRoot,
      sourceFile: unit.generated_test_file_path,
      sampleId: `${attempt.row.sample_id}-${unit.unit_id}`,
      testFile: unit.test_file,
    }),
  }));
  attempt.row = {
    ...attempt.row,
    accepted_units: units,
  };
  return attempt;
}

/** Return an unsuccessful attempt with the incoming coverage state unchanged. */
export function emptyAttempt(context, status, error) {
  return {
    row: resultRow(context, status, error),
    generalCoverage: context.generalCoverage,
    targetCoverage: context.targetCoverage,
  };
}

export function emptyCoverageDelta() {
  return {
    new_covered_lines: 0,
    new_covered_branch_outcomes: 0,
    files: [],
  };
}

export function mergeCoverageDelta(target, update) {
  target.new_covered_lines += Number(update?.new_covered_lines ?? 0);
  target.new_covered_branch_outcomes += Number(
    update?.new_covered_branch_outcomes ?? 0,
  );
  target.files.push(...(update?.files ?? []));
}
