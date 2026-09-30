import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

import {
  normalizeObservedCoverage,
  targetLineCoverageFromObservation,
} from "../general_coverage.mjs";
import { ensureDir, writeJson } from "../json.mjs";
import { remainingBudgetMs } from "./deadline.mjs";
import { validationRecord } from "./validate.mjs";

export function targetCoverageRecord(coverage) {
  return {
    filepath: coverage.filepath,
    total_line_count: coverage.total_lines.length,
    covered_lines: coverage.covered_lines,
    uncovered_lines: coverage.uncovered_lines,
  };
}

function materializeSeedTest(context) {
  const sourceFile = context.objective.seed_test.test_file;
  const testFile = context.generatedTestFile({
    attemptId: `${context.sampleId}-seed-coverage`,
    objective: context.objective,
    unit: { label: "seed-baseline" },
    unitIndex: 0,
  });
  if (testFile === sourceFile) {
    throw new Error("seed coverage copy must not replace the source test");
  }
  const source = path.join(context.currentRoot, sourceFile);
  const target = path.join(context.currentRoot, testFile);
  ensureDir(path.dirname(target));
  fs.copyFileSync(source, target);
  return testFile;
}

function cachedSeedObservation(context) {
  const seed = context.objective.seed_test;
  if (!context.seedCoverageCache || !seed.sha256) return null;
  const seedKey = `${seed.test_file}\0${seed.sha256}`;
  const targetKey = `${seedKey}\0${context.objective.filepath}`;
  const cached =
    context.seedCoverageCache.get(seedKey) ??
    context.seedCoverageCache.get(targetKey);
  if (cached) return cached;

  const test = context.seedCoverage?.get(seed.test_file);
  const target = test?.targets.get(context.objective.filepath);
  if (!target || test.sha256 !== seed.sha256) return null;
  const source = path.join(context.currentRoot, context.objective.filepath);
  if (!fs.existsSync(source)) return null;
  const sourceHash = crypto
    .createHash("sha256")
    .update(fs.readFileSync(source))
    .digest("hex");
  if (sourceHash !== target.sha256) return null;

  const observation = {
    source: "static_input",
    observed: {
      files: {
        [context.objective.filepath]: {
          executed_lines: target.covered_lines,
        },
      },
    },
  };
  context.seedCoverageCache.set(targetKey, observation);
  return observation;
}

function seedCoverageResult(context, observed, validation) {
  const coverage = targetLineCoverageFromObservation(
    context.generalCoverage,
    observed,
    context.objective.filepath,
  );
  const coverageRecord = targetCoverageRecord(coverage);
  writeJson(path.join(context.sampleDir, "seed-validation.json"), validation);
  writeJson(
    path.join(context.sampleDir, "seed-target-coverage.json"),
    coverageRecord,
  );
  return {
    status: "passed",
    validation,
    coverage,
    coverage_record: coverageRecord,
  };
}

/** Measure the selected seed, reusing observations only for matching inputs. */
export function measureSeedCoverage(context) {
  const cached = cachedSeedObservation(context);
  if (cached) {
    return seedCoverageResult(context, cached.observed, {
      status: "passed",
      cache_hit: true,
      source_test_file: context.objective.seed_test.test_file,
      ...(cached.iteration ? { source_iteration: cached.iteration } : {}),
      ...(cached.source ? { source: cached.source } : {}),
    });
  }

  const runDir = path.join(context.sampleDir, "seed-coverage-run");
  let testFile = "";
  let validation;
  try {
    const remaining = remainingBudgetMs(context);
    if (remaining <= 0) {
      return { status: "time_budget", error: "run time budget exhausted" };
    }
    testFile = materializeSeedTest(context);
    validation = context.measureTestFileCoverage({
      projectRoot: context.currentRoot,
      sourceProjectRoot: context.sourceProjectRoot,
      testFile,
      objective: context.objective,
      outDir: runDir,
      timeoutSeconds: Math.max(
        0.001,
        Math.min(context.timeoutSeconds, remaining / 1000),
      ),
      env: context.validationEnv,
    });
    const record = validationRecord(validation);
    if (validation.status !== "passed") {
      writeJson(path.join(context.sampleDir, "seed-validation.json"), record);
      return {
        status: "seed_validation_failed",
        error: `selected seed test did not pass: ${validation.status}`,
        validation: record,
      };
    }
    if (!validation.coverage_json) {
      writeJson(path.join(context.sampleDir, "seed-validation.json"), record);
      return {
        status: "seed_coverage_failed",
        error: "selected seed test produced no coverage data",
        validation: record,
      };
    }
    const observed = normalizeObservedCoverage({
      coverageJson: validation.coverage_json,
      projectRoot: context.currentRoot,
    });
    const seed = context.objective.seed_test;
    if (context.seedCoverageCache && seed.sha256) {
      context.seedCoverageCache.set(`${seed.test_file}\0${seed.sha256}`, {
        iteration: context.iteration,
        observed,
      });
    }
    return seedCoverageResult(context, observed, record);
  } catch (error) {
    return {
      status: "seed_coverage_failed",
      error: error.message,
      validation: validation ? validationRecord(validation) : null,
    };
  } finally {
    if (testFile) {
      fs.rmSync(path.join(context.currentRoot, testFile), { force: true });
    }
    fs.rmSync(runDir, { recursive: true, force: true });
  }
}
