import fs from "node:fs";
import path from "node:path";
import { performance } from "node:perf_hooks";

import { DEFAULT_ACCEPTANCE_POLICY, isCandidateAtomic } from "../acceptance.mjs";
import { loadModelEnv, providerAccess, sanitizeEnvForSubprocess } from "./client.mjs";
import { writeJson } from "../json.mjs";
import { createCurrentWorkspace, resolveOutputRoot } from "../materialize.mjs";
import { rankCoverageFiles } from "../general_coverage.mjs";
import { buildCoverageTargetManifest } from "../input/coverage_targets.mjs";
import { loadInputs } from "../input/snapshot.mjs";
import { generatedTestFile } from "./attempt.mjs";
import { runCoverageTarget } from "./coverage_target.mjs";
import { finishTimer, startTimer, writeProgress } from "./report.mjs";
import { loadTypeScript } from "../typescript_ast.mjs";
import { DEFAULT_STRATEGY, isContractDirected } from "../strategy.mjs";

/** Execute one prepared project's fixed file queue within the active budget. */
export async function runCoverageModelBacked({
  baseInputFile,
  projectRoot = null,
  outRoot,
  measureTestFileCoverage,
  validateGeneratedTest,
  testPackages,
  runId = null,
  rounds = 1,
  provider = "openai",
  model = "",
  envFile = null,
  timeoutSeconds = 600,
  repairContextRequests = 0,
  strategy = DEFAULT_STRATEGY,
  acceptancePolicy = DEFAULT_ACCEPTANCE_POLICY,
  timeBudgetSeconds = 0,
  completeModel = null,
}) {
  if (
    typeof validateGeneratedTest !== "function" ||
    typeof measureTestFileCoverage !== "function"
  ) {
    throw new Error("validation and coverage adapters are required");
  }
  if (!Array.isArray(testPackages) || testPackages.length === 0) {
    throw new Error("testPackages must describe the project's Vitest packages");
  }
  if (
    !Number.isInteger(rounds) ||
    rounds < 1 ||
    !Number.isFinite(timeoutSeconds) ||
    timeoutSeconds <= 0
  ) {
    throw new Error("rounds and timeout must be positive");
  }
  if (
    !Number.isFinite(timeBudgetSeconds) ||
    timeBudgetSeconds < 0 ||
    !Number.isInteger(repairContextRequests) ||
    repairContextRequests < 0
  ) {
    throw new Error("time budget and context request limit must be non-negative");
  }
  isCandidateAtomic(acceptancePolicy);
  if (!isContractDirected(strategy)) repairContextRequests = 0;
  const initial = loadInputs(baseInputFile);
  const { baseInput } = initial;
  if (projectRoot) baseInput.project_root = path.resolve(projectRoot);
  if (!fs.statSync(baseInput.project_root).isDirectory()) {
    throw new Error("project_root must name a prepared checkout");
  }
  const modelEnv = loadModelEnv(envFile);
  const effectiveModel =
    model || modelEnv.LLM_MODEL || modelEnv.OPENAI_MODEL || "gpt-5-mini";
  providerAccess(provider, modelEnv);
  const id = runId ?? new Date().toISOString().replace(/[:.]/gu, "-");
  if (
    typeof id !== "string" ||
    !id ||
    id === "." ||
    id === ".." ||
    /[\\/\0]/u.test(id)
  ) {
    throw new Error("runId must be a single directory name");
  }
  const outputRoot = resolveOutputRoot(outRoot);
  const relative = path.relative(fs.realpathSync(baseInput.project_root), outputRoot);
  if (
    !relative ||
    (relative !== ".." &&
      !relative.startsWith(".." + path.sep) &&
      !path.isAbsolute(relative))
  ) {
    throw new Error("outRoot must be outside projectRoot");
  }
  const runDir = path.join(outputRoot, "runs", id);
  fs.mkdirSync(path.dirname(runDir), { recursive: true });
  fs.mkdirSync(runDir);
  const rows = [];
  const checkpoints = [];
  let generalCoverage = initial.generalCoverage;
  let started = null;
  let stopReason = "interrupted";
  const config = {
    project: baseInput.project,
    provider,
    model: effectiveModel,
    strategy,
    acceptance_policy: acceptancePolicy,
    time_budget_seconds: timeBudgetSeconds,
  };
  const persist = (reason) =>
    writeProgress({
      runDir,
      config,
      rows,
      checkpoints,
      generalCoverage,
      stopReason: reason,
      elapsedMs: started === null ? 0 : performance.now() - started,
    });
  try {
    const manifest = buildCoverageTargetManifest({
      projectRoot: baseInput.project_root,
      generalTestScores: initial.generalTestScores,
      testPackages,
      fileRanking: rankCoverageFiles(generalCoverage, initial.ldhFiles),
    });
    writeJson(path.join(runDir, "targets.json"), manifest);
    const currentRoot = createCurrentWorkspace({
      frozenRoot: baseInput.project_root,
      runDir,
    });
    const validationEnv = sanitizeEnvForSubprocess(process.env);
    const seedCoverageCache = new Map();
    let typescript = null;
    let cursor = 0;
    started = performance.now();
    const remainingTimeMs = () =>
      timeBudgetSeconds <= 0
        ? Number.POSITIVE_INFINITY
        : Math.max(0, timeBudgetSeconds * 1000 - (performance.now() - started));
    persist("running");

    for (let iteration = 1; iteration <= rounds; iteration += 1) {
      if (remainingTimeMs() <= 0) {
        stopReason = "time_budget";
        break;
      }
      const objective = manifest.targets[cursor];
      if (!objective) {
        stopReason = "target_queue_exhausted";
        break;
      }
      const timer = startTimer();
      const sampleId = `iteration-${String(iteration).padStart(3, "0")}`;
      const sampleDir = path.join(runDir, "records", sampleId, "sample");
      typescript ??= loadTypeScript(currentRoot);
      const result = await runCoverageTarget({
        project: baseInput.project,
        iteration,
        sampleId,
        sampleDir,
        objective,
        runDir,
        currentRoot,
        sourceProjectRoot: baseInput.project_root,
        provider,
        model: effectiveModel,
        modelEnv,
        validationEnv,
        measureTestFileCoverage,
        validateGeneratedTest,
        timeoutSeconds,
        repairContextRequests,
        strategy,
        acceptancePolicy,
        generatedTestFile,
        generalCoverage,
        completeModel,
        typescript,
        remainingTimeMs,
        seedCoverageCache,
        seedCoverage: initial.seedCoverage?.observations ?? null,
      });
      result.row.timing = finishTimer(timer);
      rows.push(result.row);
      if (result.row.status !== "model_failed") cursor += 1;
      if (result.row.status === "accepted") generalCoverage = result.generalCoverage;
      persist("running");
      if (result.row.status === "time_budget" || remainingTimeMs() <= 0) {
        stopReason = "time_budget";
        break;
      }
      stopReason = "round_limit";
    }
    return { runDir, rows };
  } catch (error) {
    stopReason = "interrupted";
    throw error;
  } finally {
    try {
      persist(stopReason);
    } finally {
      fs.rmSync(path.join(runDir, "workspaces"), { recursive: true, force: true });
    }
  }
}
