import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

import { rankCoverageFiles } from "../typescript/general_coverage.mjs";
import { buildCoverageTargetManifest } from "../typescript/input/coverage_targets.mjs";
import { loadInputs } from "../typescript/input/snapshot.mjs";
import { generatedTestFile } from "../typescript/run/attempt.mjs";
import { runCoverageTarget } from "../typescript/run/coverage_target.mjs";
import { TimeBudgetExceeded } from "../typescript/run/deadline.mjs";
import { loadTypeScript } from "../typescript/typescript_ast.mjs";
import { normalizeFormalRepairSchema, projectFixture, scriptedModel, writeJson } from "./typescript_fixture.mjs";

const formalRoot = process.env.AUGMENT_FORMAL_ROOT ?? process.env.PROBE_FORMAL_ROOT;
const nodeModules = process.env.ARTIFACT_TEST_NODE_MODULES
  ?? process.env.PROBE_TEST_NODE_MODULES
  ?? fileURLToPath(new URL("../../../../node_modules", import.meta.url));
const formal = formalRoot
  ? await import(pathToFileURL(path.join(formalRoot, "src/common/test_augmentF/TS/run/coverage_target.mjs")))
  : null;
const formalDeadline = formalRoot
  ? await import(pathToFileURL(path.join(formalRoot, "src/common/test_augmentF/TS/run/deadline.mjs")))
  : null;

function normalizeRepairDirectory(value) {
  return value.replace(/(^|\/)repair-001(?=\/|$)/gu, "$1repair");
}

function normalize(value, root, formalOutput = false) {
  if (typeof value === "string") {
    const text = value.replaceAll(root, "<root>");
    return formalOutput
      ? normalizeFormalRepairSchema(normalizeRepairDirectory(text))
      : text;
  }
  if (Array.isArray(value)) return value.map(item => normalize(item, root, formalOutput));
  if (value && typeof value === "object") {
    const record = { ...value };
    if (record.row && Object.hasOwn(record, "generalCoverage")) delete record.proposal;
    for (const [items, count] of [
      ["accepted_units", "accepted_unit_count"],
      ["rejected_units", "rejected_unit_count"],
      ["withheld_passing_units", "withheld_passing_unit_count"],
      ["passes", "generation_pass_count"],
    ]) {
      if (Array.isArray(record[items]) && Object.hasOwn(record, count)) {
        assert.equal(record[count], record[items].length);
        delete record[count];
      }
    }
    if (Array.isArray(record.accepted_units) && Object.hasOwn(record, "test_files")) {
      assert.deepEqual(record.test_files, record.accepted_units.map(unit => unit.test_file));
      delete record.test_files;
    }
    return Object.fromEntries(Object.entries(record)
      // Accepted file bytes are compared directly; the artifact omits this
      // redundant archival digest. Timing and implementation frames vary.
      .filter(([key]) => !["duration_ms", "stack", "accepted_file_sha256"].includes(key))
      .map(([key, item]) => [
        formalOutput ? normalizeRepairDirectory(key) : key,
        normalize(item, root, formalOutput),
      ]));
  }
  return value;
}

function savedEvidence(root) {
  const output = {};
  function visit(dir) {
    if (!fs.existsSync(dir)) return;
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const file = path.join(dir, entry.name);
      if (entry.isDirectory()) visit(file);
      else if (entry.isFile()) {
        const text = fs.readFileSync(file, "utf8");
        output[path.relative(root, file)] = file.endsWith(".json") ? JSON.parse(text) : text;
      }
    }
  }
  visit(path.join(root, "run"));
  visit(path.join(root, "project/test"));
  return output;
}

function observedCoverage(args, lines, branches, helperCovered = false) {
  const file = path.join(args.projectRoot, "src/target.ts");
  const location = line => ({ start: { line, column: 0 }, end: { line, column: 10 } });
  const coverage = path.join(args.outDir, "coverage.json");
  const measured = { [file]: {
    path: file,
    statementMap: Object.fromEntries([1, 2, 3].map(line => [line, location(line)])),
    s: Object.fromEntries([1, 2, 3].map(line => [line, Number(lines.includes(line))])),
    branchMap: { 7: { type: "if", loc: location(2), locations: [location(2), {
      start: { line: 2, column: 11 }, end: { line: 2, column: 20 },
    }] } },
    b: { 7: branches },
  } };
  if (helperCovered) {
    const helper = path.join(args.projectRoot, "src/helper.ts");
    measured[helper] = {
      path: helper, statementMap: { 0: location(1) }, s: { 0: 1 },
      branchMap: {}, b: {},
    };
  }
  writeJson(coverage, measured);
  return { status: "passed", test_file: args.testFile, exit_code: 0, coverage_json: coverage };
}

async function runScenario(root, scenario, strategy, acceptancePolicy, runner, BudgetError) {
  const { project, input } = projectFixture(root, nodeModules);
  const initial = loadInputs(input);
  const crossFile = scenario.endsWith("cross_file_gain");
  if (crossFile) {
    initial.generalCoverage.files["src/helper.ts"] = {
      total_lines: [1], covered_lines: [], branches: [],
    };
  }
  const objective = buildCoverageTargetManifest({
    projectRoot: project,
    generalTestScores: initial.generalTestScores,
    fileRanking: rankCoverageFiles(initial.generalCoverage, initial.ldhFiles),
    testPackages: [{ name: "root", cwd: "." }],
  }).targets[0];
  const calls = [];
  const conversations = [];
  let exhausted = scenario === "seed_budget";
  let modelCalls = 0;
  let validations = 0;
  const repairScenario = scenario.replace(/^partial_/u, "");
  const modelScenario = scenario.startsWith("partial_repair_") ? "partial"
    : scenario.startsWith("repair_") ? "repair" : scenario;
  const model = scriptedModel(modelScenario, conversations);
  const request = { action: "request_context", requests: [{
    kind: "module_context", filepath: "src/helper.ts", reason: "Return contract.",
  }] };
  const context = {
    project: "fixture", iteration: 1, sampleId: "iteration-001",
    runDir: path.join(root, "run"), sampleDir: path.join(root, "run/sample"),
    currentRoot: project, sourceProjectRoot: project, objective,
    generalCoverage: initial.generalCoverage, strategy, acceptancePolicy,
    provider: "openai", model: "scripted", modelEnv: {}, sourceRoots: ["src"],
    timeoutSeconds: 10, validationEnv: {}, typescript: loadTypeScript(project),
    generatedTestFile, repairContextRequests: scenario === "repair_disabled" ? 0 : 1,
    seedCoverageCache: new Map(), remainingTimeMs: () => exhausted ? 0 : Infinity,
    completeModel: async args => {
      modelCalls += 1;
      const repair = repairScenario.startsWith("repair_") && modelCalls === 2;
      if (scenario === "model_fatal" || (repair && repairScenario === "repair_fatal")) {
        throw Object.assign(new Error("fatal model error"), { retryable: false });
      }
      if (repair && repairScenario === "repair_transport") throw new Error("repair transport error");
      if (scenario === "model_budget" || (repair && repairScenario === "repair_budget")) {
        throw new BudgetError();
      }
      if (scenario === "repeated_context" ||
          (repair && ["repair_context", "repair_disabled"].includes(repairScenario))) {
        conversations.push(structuredClone(args.messages));
        return { choices: [{ message: { content: JSON.stringify(request) } }] };
      }
      if (scenario === "invalid" || (repair && repairScenario === "repair_invalid")) {
        conversations.push(structuredClone(args.messages));
        return { choices: [{ message: { content: "not JSON" } }] };
      }
      return model(args);
    },
    measureTestFileCoverage: args => {
      calls.push({ phase: "seed", ...args });
      if (scenario === "seed_error") throw new Error("seed measurement error");
      if (scenario === "seed_failed") return { status: "failed" };
      if (scenario === "seed_missing") return { status: "passed" };
      if (scenario === "after_seed_budget") exhausted = true;
      return observedCoverage(args, scenario === "already_covered" ? [1, 2, 3] : [1], [0, 0]);
    },
    validateGeneratedTest: args => {
      validations += 1;
      const source = fs.readFileSync(path.join(args.projectRoot, args.testFile), "utf8");
      calls.push({ phase: "candidate", ...args, source });
      if (scenario === "validation_error") throw new Error("validation threw");
      if (source.includes('"wrong"') || args.testName.startsWith("bad")) {
        return { status: "failed", output_tail: `AssertionError\n at choose (${project}/src/target.ts:2:1)` };
      }
      if (scenario === "validation_missing") return { status: "passed" };
      if (scenario === "validation_budget") exhausted = true;
      if (crossFile) {
        const afterProgress = scenario === "continuation_cross_file_gain";
        return observedCoverage(args, afterProgress ? [1, 2] : [1],
          afterProgress ? [1, 0] : [0, 0], !afterProgress || validations > 1);
      }
      if (scenario === "no_gain") return observedCoverage(args, [1], [0, 0]);
      if (scenario === "continuation" && validations === 1) {
        return observedCoverage(args, [1, 2], [1, 0]);
      }
      return observedCoverage(args, [1, 2, 3], [1, 1]);
    },
  };
  if (scenario === "already_covered") {
    context.generalCoverage.files[objective.filepath].branches[0].baseline_covered = 2;
  }
  if (scenario === "seed_cached") {
    context.seedCoverageCache.set(`${objective.seed_test.test_file}\0${objective.seed_test.sha256}`, {
      iteration: 1, observed: { files: { [objective.filepath]: { executed_lines: [1] } } },
    });
  }
  if (scenario === "seed_static" || scenario === "seed_stale") {
    const sha256 = crypto.createHash("sha256")
      .update(fs.readFileSync(path.join(project, objective.filepath))).digest("hex");
    context.seedCoverage = new Map([[objective.seed_test.test_file, {
      sha256: objective.seed_test.sha256,
      targets: new Map([[objective.filepath, {
        sha256: scenario === "seed_stale" ? "stale" : sha256, covered_lines: [1],
      }]]),
    }]]);
  }
  let result;
  try {
    result = await runner(context);
  } catch (error) {
    result = { thrown: error.message };
  }
  const evidence = savedEvidence(root);
  if (runner === runCoverageTarget) {
    const files = Object.keys(evidence);
    assert.ok(files.every(file => !file.split(path.sep).includes("repair-001")));
    assert.ok(files.filter(file => file.endsWith("/repair/feedback.md")).length <= 1);
    assert.equal(Object.hasOwn(result, "proposal"), false);
    for (const row of [result.row, ...Object.entries(evidence)
      .filter(([file]) => file.endsWith("sample-result.json"))
      .map(([, record]) => record)].filter(Boolean)) {
      for (const key of ["accepted_unit_count", "rejected_unit_count",
        "withheld_passing_unit_count", "generation_pass_count", "test_files"])
        assert.equal(Object.hasOwn(row, key), false, key);
    }
  }
  return normalize({ result, calls, conversations, modelCalls,
    cache: [...context.seedCoverageCache], evidence }, root, runner !== runCoverageTarget);
}

for (const strategy of ["contract_directed", "contract_agnostic"]) {
  for (const policy of ["passing_subset", "candidate_atomic"]) {
    for (const scenario of ["cross_file_gain", "continuation_cross_file_gain"]) {
      test(`accepted coverage state: ${strategy}/${policy}/${scenario}`, async t => {
        const root = fs.mkdtempSync(path.join(os.tmpdir(), "augment-cross-file-"));
        t.after(() => fs.rmSync(root, { recursive: true, force: true }));
        const actual = await runScenario(root, scenario, strategy, policy,
          runCoverageTarget, TimeBudgetExceeded);
        const { row, generalCoverage } = actual.result;
        const afterProgress = scenario === "continuation_cross_file_gain";
        const retained = policy === "passing_subset";
        assert.equal(row.passes.length, afterProgress ? 2 : 1);
        assert.equal(row.passes.at(-1).target_coverage_delta.covered_lines.length, 0);
        assert.equal(row.status, retained || afterProgress ? "accepted" : "no_target_coverage");
        assert.deepEqual(generalCoverage.files["src/helper.ts"].covered_lines,
          retained ? [1] : []);
        assert.deepEqual(generalCoverage.files["src/target.ts"].covered_lines,
          afterProgress ? [1, 2] : [1]);
        assert.equal(row.general_coverage_delta.new_covered_lines,
          Number(retained) + Number(afterProgress));
        assert.equal(row.passes.at(-1).status, retained ? "accepted" : "no_target_coverage");
      });
    }
  }
}

const scenarios = [
  "direct", "initial_context", "repeated_context", "repair", "repair_context",
  "repair_disabled", "repair_transport", "repair_fatal", "repair_budget", "repair_invalid",
  "partial_repair_transport", "partial_repair_budget", "partial_repair_invalid", "partial_repair_context",
  "partial", "continuation", "no_gain", "invalid", "transport_retry", "model_fatal",
  "model_budget", "seed_budget", "after_seed_budget", "validation_budget",
  "seed_error", "seed_failed", "seed_missing", "seed_cached", "seed_static", "seed_stale",
  "already_covered", "validation_error", "validation_missing",
];
for (const [strategy, policy] of [
  ["contract_directed", "passing_subset"], ["contract_agnostic", "candidate_atomic"],
  ["contract_directed", "candidate_atomic"], ["contract_agnostic", "passing_subset"],
]) {
  for (const scenario of scenarios) {
    test(`target reference: ${strategy}/${policy}/${scenario}`, { skip: !formal }, async t => {
      const root = fs.mkdtempSync(path.join(os.tmpdir(), "augment-target-reference-"));
      t.after(() => fs.rmSync(root, { recursive: true, force: true }));
      const actual = await runScenario(path.join(root, "artifact"), scenario, strategy, policy,
        runCoverageTarget, TimeBudgetExceeded);
      const expected = await runScenario(path.join(root, "formal"), scenario, strategy, policy,
        formal.runCoverageTarget, formalDeadline.TimeBudgetExceeded);
      assert.deepEqual(actual, expected);
      if (scenario === "direct" || scenario === "continuation") {
        assert.equal(actual.result.row.status, "accepted");
        assert.equal(actual.result.row.passes.length, scenario === "continuation" ? 2 : 1);
      }
      if (scenario === "seed_cached" || scenario === "seed_static") {
        assert.ok(actual.calls.every(call => call.phase !== "seed"));
      }
      if (scenario === "repair_context" && strategy === "contract_directed") {
        assert.equal(actual.modelCalls, 3);
        assert.ok(JSON.stringify(actual.conversations).includes("export const expected"));
      }
    });
  }
}
