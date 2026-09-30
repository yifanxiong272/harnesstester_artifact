import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import test from "node:test";
import {
  runOptions,
  strategyProfile,
  TARGET_PROBE_STRATEGIES,
  validateRunOptions,
} from "../typescript/run/options.mjs";
import * as prompts from "../typescript/prompt/prompts.mjs";
import {
  aggregateAssetRows,
} from "../typescript/run/reporting.mjs";
import { preflightTargetRun } from "../typescript/run/preflight.mjs";
import { walkFiles } from "../typescript/support/storage.mjs";
import { loadModelEnv } from "../typescript/run/client.mjs";
import { recordRepairAttempt } from "../typescript/run/repair.mjs";
import { runPreparedCase } from "../typescript/run/case.mjs";
import { completeAndRecord } from "../typescript/run/session.mjs";

import {
  alignFormalNames,
  formalRoot,
  formalPath,
  formalModule,
  sourceModule,
} from "./typescript_support.mjs";

test("formal name adapter preserves prompt prose and local state", () => {
  assert.equal(
    alignFormalNames(`const TARGET_PROBE_LDCR_STRATEGY = "target_probe_ldcr";
const current = state.current;
return { ...current, current: current.summary, status: "current_passed", current_outcomes: {} };
"the current implementation; currently selected; LDCR-only";`),
    `const TARGET_PROBE_LDH_STRATEGY = "target_probe_ldh";
const current = state.latest;
return { ...current, latest: current.summary, status: "latest_passed", latest_outcomes: {} };
"the current implementation; currently selected; LDH-only";`,
  );
});

test("execution limits reject nonfinite numbers and fractional excerpt lengths", () => {
  const options = runOptions({ model: "fixture", strategy: "target_probe_ldh" });
  for (const key of ["timeoutSeconds", "modelTimeoutMs", "minimizationFailureExcerptChars"]) {
    for (const value of [NaN, Infinity, -Infinity, 0, -1, true]) {
      assert.throws(() => validateRunOptions({ ...options, [key]: value }), new RegExp(key));
    }
  }
  assert.throws(
    () => validateRunOptions({ ...options, minimizationFailureExcerptChars: 1.5 }),
    /minimizationFailureExcerptChars/u,
  );
  validateRunOptions({ ...options, timeoutSeconds: 0.5, modelTimeoutMs: 0.25 });
});

test("run options retain canonical workflow controls and injected hooks", () => {
  const modelClient = {};
  const validationRunner = () => {};
  const options = runOptions({
    strategy: "target_probe_ldh",
    model: "fixture", provider: "openai", envFile: "fixture.env",
    modelClient, validationRunner,
    directSamples: 3, direct_samples: 9, soft_samples: 4, timeout: 19,
    project: "fixture", caseJson: "case.json", buggyRoot: "buggy",
    fixedRoot: "fixed", outRoot: "output", runId: "example",
    evaluationMode: "paired_reveal", resume: false,
  });
  assert.equal(options.directSamples, 3);
  assert.equal(options.softSamples, 4);
  assert.equal(options.timeoutSeconds, 19);
  assert.equal(options.modelClient, modelClient);
  assert.equal(options.validationRunner, validationRunner);
  assert.equal(options.envFile, "fixture.env");
  assert.equal(options.evaluationMode, "paired_reveal");
  assert.deepEqual(runOptions(options), options);
  for (const key of [
    "direct_samples", "soft_samples", "timeout", "project", "caseJson",
    "buggyRoot", "fixedRoot", "outRoot", "runId", "resume",
  ]) assert.equal(Object.hasOwn(options, key), false, key);
});

for (const provider of ["openai", "openrouter"]) {
  for (const usageKind of ["missing", "null", "detailed"]) {
    test(`raw model usage is preserved: ${provider}, ${usageKind}`, async (t) => {
      const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-usage-"));
      t.after(() => fs.rmSync(root, { recursive: true, force: true }));
      const response = {
        model: "fixture-model-snapshot",
        choices: [{ message: { content: "fixture" } }],
      };
      if (usageKind !== "missing") {
        response.usage = usageKind === "null" ? null : {
          prompt_tokens: 100,
          completion_tokens: 20,
          total_tokens: 120,
          prompt_tokens_details: { cached_tokens: 40 },
          completion_tokens_details: { reasoning_tokens: 10 },
        };
      }
      const options = runOptions({
        model: "fixture-model",
        provider,
        strategy: "target_probe_ldh",
        modelClient: { async complete() { return response; } },
      });
      validateRunOptions(options);
      const rawPath = path.join(root, "implementation.raw.json");
      assert.deepEqual(await completeAndRecord({ options }, "fixture", rawPath), response);
      assert.deepEqual(JSON.parse(fs.readFileSync(rawPath)), {
        provider, model: options.model, response,
      });
      assert.deepEqual(fs.readdirSync(root), ["implementation.raw.json"]);
    });
  }
}

test("only the two retained strategies can start a run", async (t) => {
  assert.deepEqual(TARGET_PROBE_STRATEGIES, [
    "target_probe_ldh",
    "target_probe_contract_agnostic",
  ]);
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-strategies-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  await assert.rejects(
    runPreparedCase({
      options: { strategy: "target_probe_baseline" },
      runDir: path.join(root, "output"),
    }),
    /unsupported target-probing strategy/u,
  );
  assert.deepEqual(fs.readdirSync(root), []);
});

for (const strategy of [
  "target_probe_ldh",
  "target_probe_contract_agnostic",
]) {
  test(
    `strategy context and repair policy match formal: ${strategy}`,
    { skip: !formalRoot },
    async () => {
      const formal = await formalModule("run/tracks.mjs");
      const expected = formal.strategyProfile(strategy);
      const actual = strategyProfile(strategy);
      assert.equal(actual.allowContext, expected.allowPlanContext);
      assert.equal(actual.allowContext, expected.includeContractContext);
      assert.equal(actual.repairMode, expected.repairMode);
      assert.equal(actual.repairKey, expected.repairKey);
    },
  );
}

test(
  "model environment preserves file precedence without modifying process or file",
  { skip: !formalRoot },
  async (t) => {
    const formal = await formalModule("run/client.mjs");
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-env-"));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const file = path.join(root, ".env");
    const text =
      '# fixture\nexport PATH="fixture/path"\nPROBE_FIXTURE="first"\nPROBE_FIXTURE=second\nEMPTY=\nWITH_EQUALS="a=b"\ninvalid line\n';
    fs.writeFileSync(file, text);
    const environment = { ...process.env };
    for (const value of [
      undefined,
      null,
      "",
      path.join(root, "missing"),
      file,
    ]) {
      const actual = loadModelEnv(value);
      assert.deepEqual(actual, formal.loadModelEnv(value).env);
      assert.notEqual(actual, process.env);
      actual.PROBE_FIXTURE = "modified result";
      assert.deepEqual({ ...process.env }, environment);
      assert.equal(fs.readFileSync(file, "utf8"), text);
    }
  },
);

test("file traversal preserves exclusions, order, and symlink handling", (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-files-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  for (const name of [
    "b.txt",
    "a/first.txt",
    "a/deep/last.txt",
    "excluded/x.txt",
  ]) {
    const full = path.join(root, name);
    fs.mkdirSync(path.dirname(full), { recursive: true });
    fs.writeFileSync(full, "fixture");
  }
  fs.symlinkSync("a", path.join(root, "linked-directory"), "dir");
  fs.symlinkSync("b.txt", path.join(root, "linked-file"));
  fs.symlinkSync("absent", path.join(root, "dangling"));
  const readdir = fs.readdirSync.bind(fs);
  t.mock.method(fs, "readdirSync", (directory) => readdir(directory).reverse());
  const relative = (options) =>
    [...walkFiles(root, options)].map((file) => path.relative(root, file));
  assert.deepEqual(relative({ exclude: ["excluded"], sorted: true }), [
    "a/deep/last.txt",
    "a/first.txt",
    "b.txt",
  ]);
  assert.deepEqual(relative({ exclude: ["excluded"] }), [
    "b.txt",
    "a/first.txt",
    "a/deep/last.txt",
  ]);
  assert.deepEqual(relative({ sorted: true }), [
    "a/deep/last.txt",
    "a/first.txt",
    "b.txt",
    "excluded/x.txt",
  ]);
  assert.deepEqual([...walkFiles(path.join(root, "missing"))], []);
  assert.throws(() => [...walkFiles(path.join(root, "b.txt"))], {
    code: "ENOTDIR",
  });
});

test(
  "result aggregation priority matches formal",
  { skip: !formalRoot },
  () => {
    const { ts, tree } = sourceModule(formalPath("run/workflow.mjs"));
    const declaration = tree.statements.find(
      (node) =>
        ts.isFunctionDeclaration(node) &&
        node.name?.text === "aggregateAssetRows",
    );
    const formal = new Function(
      `${declaration.getText(tree)}; return aggregateAssetRows;`,
    )();
    const base = {
      sample_id: "s1",
      status: "stale",
      marker: "retained",
    };
    const original = structuredClone(base);
    const statuses = [
      "revealed",
      "fixed_failed",
      "buggy_passed",
      "error",
      "unknown",
      null,
    ];
    const check = (rows) => {
      const actual = aggregateAssetRows(base, "proposal.json", rows);
      const expected = formal(base, "proposal.json", rows);
      assert.equal(expected.asset_count, rows.length);
      delete expected.asset_count;
      if (expected.revealed_asset_ids) {
        assert.deepEqual(expected.revealed_asset_ids,
          rows.filter((row) => row.status === "revealed").map((row) => row.asset_id));
        delete expected.revealed_asset_ids;
      }
      assert.equal(
        JSON.stringify(actual),
        JSON.stringify(expected),
      );
      assert.deepEqual(base, original);
      assert.equal(actual.assets, rows);
      if (rows.length < 3) {
        for (const status of statuses)
          check([...rows, { asset_id: `a${rows.length}`, status }]);
      }
    };
    check([]);
  },
);

for (const readable of [false, true]) {
  for (const mode of ["paired_reveal", "single_revision_discovery"]) {
  test(
    `preflight evidence matches formal: ${mode} readable ${readable}`,
    { skip: !formalRoot },
    async (t) => {
      const formal = await formalModule("run/preflight.mjs");
      const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-preflight-"));
      t.after(() => fs.rmSync(root, { recursive: true, force: true }));
      fs.mkdirSync(path.join(root, "src"));
      fs.writeFileSync(
        path.join(root, "src/counter.ts"),
        "export const value = 1;\n",
      );
      t.mock.method(fs, "accessSync", () => {
        if (!readable) throw new Error("fixture unreadable");
      });
      for (const checkout of [root, path.join(root, "missing"), ""]) {
        for (const files of [
          [],
          ["src/counter.ts"],
          ["src"],
          ["missing.ts"],
          ["../outside.ts"],
        ]) {
          for (const roots of [
            [],
            ["test/generated"],
            ["tests"],
            ["."],
            ["../outside"],
          ]) {
            for (const routed of [false, true]) {
              const manifest = {
                evaluation_mode: mode,
                [`${mode === "single_revision_discovery" ? "latest" : "buggy"}_checkout`]: { path: checkout },
                source_roots: ["src", "missing", "../outside"],
              };
              const packet = {
                target_units: files.map((filepath) => ({
                  unit_id: "u1",
                  filepath,
                })),
                public_target_routes: {
                  available: routed,
                  targets: routed
                    ? [
                        {
                          target_unit_id: "u1",
                          entrypoints: [{ entrypoint_id: "e1" }],
                        },
                      ]
                    : [],
                },
                generated_test_roots: roots,
                test_command: routed ? ["vitest", "run"] : [],
              };
              assert.equal(
                JSON.stringify(preflightTargetRun({ manifest, packet })),
                JSON.stringify(formal.preflightTargetRun({ manifest, packet })),
              );
            }
          }
        }
      }
    },
  );
  }
}
test(
  "option aliases, precedence, coercion, and strategy gates match formal",
  { skip: !formalRoot },
  async () => {
    const formal = await formalModule("run/state.mjs");
    const aliases = {
      directSamples: "direct_samples",
      samples: "samples",
      softSamples: "soft_samples",
      assetsPerSample: "assets_per_sample",
      contextRequests: "context_requests",
      minimizeBuggyFailuresPerSample: "minimize_buggy_failures_per_sample",
      minimizationPreserveAttempts: "minimization_preserve_attempts",
      minimizationFailureExcerptChars: "minimization_failure_excerpt_chars",
      harnessRepairAttempts: "harness_repair_attempts",
      harnessRepairsPerSample: "harness_repairs_per_sample",
      harnessContextRequests: "harness_context_requests",
      maxWorkflowErrors: "max_workflow_errors",
      maxRevealCandidates: "max_reveal_candidates",
      revealConfirmationRuns: "reveal_confirmation_runs",
      timeoutSeconds: "timeout",
      caseTimeBudgetSeconds: "case_time_budget_seconds",
      modelTimeoutMs: "modelTimeoutMs",
      modelRetries: "model_retries",
    };
    for (const strategy of [
      "target_probe_ldh",
      "target_probe_contract_agnostic",
    ]) {
      for (const primary of [undefined, null, 0, "2", "invalid", -1]) {
        const input = { strategy };
        for (const [key, alias] of Object.entries(aliases)) {
          input[alias] = "3";
          input[key] = primary;
        }
        const expected = formal.runOptions(input);
        delete expected.keepWorkspaces;
        delete expected.resume;
        delete expected.caseCostBudgetUsd;
        for (const [key, alias] of Object.entries(aliases)) {
          if (key !== alias) delete expected[alias];
        }
        const actual = runOptions(input);
        assert.deepEqual(actual, expected);
        const error = (validate, value) => {
          try {
            validate(value);
            return null;
          } catch (failure) {
            return failure.message;
          }
        };
        assert.equal(
          error(validateRunOptions, actual),
          error(formal.validateRunOptions, { ...expected, caseCostBudgetUsd: 0 }),
        );
      }
    }
  },
);
for (const strategy of [
  "target_probe_ldh",
  "target_probe_contract_agnostic",
]) {
  for (const withContext of [false, true]) {
    test(
      `all rendered prompts: ${strategy} context=${withContext}`,
      { skip: !formalRoot },
      async () => {
        const formal = await formalModule("prompt/prompts.mjs");
        const packet = {
          project: "fixture",
          strategy,
          target_units: [
            { unit_id: "u1", code: "const value = '$max_assets';" },
          ],
          generated_test_roots: ["test/generated/custom/"],
          module_imports: [{ text: 'import { value } from "arithmetic";' }],
          focus_target_unit_id: "u1",
          focus_sample_index: 1,
          focus_total_target_units: 2,
          whole_target_pass: true,
          soft_sample_index: 1,
          lane: "direct_probe",
          fixed_source: "PRIVATE_FIXED_SOURCE",
          retrieved_context: {
            requests: withContext
              ? [{ status: "found", code: "const x = 1;" }]
              : [],
          },
        };
        const priorAttempts = [
          {
            buggy_outcomes: ["needs_repair"],
            semantic_fingerprint: "internal",
          },
        ];
        for (const direct of [false, true]) {
          for (const stage of ["Plan", "Implementation"]) {
            const name = `renderTargetProbe${stage}Prompt`;
            const formalName = `renderTargetProbe${direct ? "Direct" : ""}${stage}Prompt`;
            const options = {
              priorAttempts,
              plan: { boundary_plan: [] },
              maxAssets: 0,
            };
            const actual = prompts[name](packet, { ...options, direct });
            assert.equal(actual, formal[formalName](packet, options));
            assert.ok(!actual.includes("PRIVATE_FIXED_SOURCE"));
            if (strategy === "target_probe_ldh") {
              const { strategy: _, ...defaultPacket } = packet;
              assert.equal(
                prompts[name](defaultPacket, { ...options, direct }),
                actual,
              );
            }
          }
        }
        const common = {
          asset: { append_code: "expect(value).toBe(true);" },
          buggySummary: { status: "needs_repair" },
        };
        const calls = {
          renderTargetProbeMinimizePrompt: {
            ...common,
            retryContext: withContext
              ? { previous_buggy_status: "buggy_passed" }
              : null,
          },
          renderTargetHarnessRepairContextRequestPrompt: {
            ...common,
            plan: {},
            tracebackContext: [],
            maxContextRequests: withContext ? 2 : 0,
          },
          renderTargetHarnessRepairPrompt: {
            ...common,
            plan: {},
            tracebackContext: [],
            repairContext: {},
          },
          renderTargetContractAgnosticRepairPrompt: { ...common, plan: {} },
        };
        for (const [name, options] of Object.entries(calls)) {
          assert.equal(
            prompts[name](packet, options),
            formal[name](packet, options),
          );
        }
      },
    );
  }
}
let controllers;
const laneControllers = [];
if (formalRoot) {
  const formalRun = formalPath("run");
  const { ts, tree } = sourceModule(path.join(formalRun, "workflow.mjs"));
  const grouped = tree.statements.find(
    (node) =>
      ts.isFunctionDeclaration(node) &&
      node.name?.text === "groupedAttemptRecord",
  );
  const formalGrouped = new Function(
    `${grouped.getText(tree)}; return groupedAttemptRecord;`,
  )();
  test("repair attempt records preserve history and current state", () => {
    const attempts = [],
      expectedAttempts = [];
    const records = [
      {
        decision: "repair",
        proposal_path: "first/proposal.json",
      },
      { error: { message: "invalid reply" } },
      { decision: "repair", proposal_path: "third/proposal.json" },
      { decision: "retain_original" },
    ];
    for (const [index, record] of records.entries()) {
      const original = structuredClone(record);
      const state = [0, 2].includes(index)
        ? { asset: `asset-${index}` }
        : undefined;
      const result = recordRepairAttempt(record, attempts, state);
      expectedAttempts.push(structuredClone(record));
      const grouped = formalGrouped(record, expectedAttempts);
      assert.deepEqual(result.record, {
        called: true,
        attempts: grouped.attempts || [original],
      });
      assert.equal(grouped.attempt_count, result.record.attempts.length);
      assert.deepEqual(attempts, expectedAttempts);
      assert.equal(attempts.at(-1), record);
      assert.deepEqual(record, original);
      assert.equal(Object.hasOwn(result, "state"), state !== undefined);
      if (state !== undefined) assert.equal(result.state, state);
      assert.equal(result.record.attempts, attempts);
    }
  });
  controllers = [];
  for (const sourcePath of [
    fileURLToPath(new URL("../typescript/run/workflow.mjs", import.meta.url)),
    path.join(formalRun, "workflow.mjs"),
  ]) {
    let { source, tree } = sourceModule(sourcePath);
    const edits = [];
    for (const node of tree.statements) {
      const literal = node.moduleSpecifier;
      if (
        literal &&
        ts.isStringLiteral(literal) &&
        literal.text.startsWith(".")
      ) {
        edits.push([
          literal.getStart(tree),
          literal.end,
          JSON.stringify(
            pathToFileURL(path.resolve(path.dirname(sourcePath), literal.text))
              .href,
          ),
        ]);
      }
      if (
        ts.isFunctionDeclaration(node) &&
        node.name?.text === "runTargetSample"
      ) {
        edits.push([
          node.body.getStart(tree),
          node.body.end,
          "{ return runtime.options.sampleRunner(arguments[0]); }",
        ]);
      }
    }
    for (const [start, end, value] of edits.sort((a, b) => b[0] - a[0])) {
      source = source.slice(0, start) + value + source.slice(end);
    }
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), "probe-schedule-"));
    try {
      const file = path.join(directory, "workflow.mjs");
      fs.writeFileSync(
        file,
        source +
          "\nexport { runGuidedCaseSamples as controller, runLaneSample as laneController };\n",
      );
      const loaded = await import(pathToFileURL(file).href);
      controllers.push(loaded.controller);
      laneControllers.push(loaded.laneController);
    } finally {
      fs.rmSync(directory, { recursive: true, force: true });
    }
  }
}

for (const scenario of [
  "passed",
  "sample_error",
  "provider_retry",
  "write_once",
  "write_always",
  "write_retryable",
]) {
  test(
    `sample checkpoint error boundary matches formal: ${scenario}`,
    { skip: !formalRoot },
    async (t) => {
      const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-checkpoint-"));
      t.after(() => fs.rmSync(root, { recursive: true, force: true }));
      const nativeWrite = fs.writeFileSync;
      let writes = 0;
      const events = [];
      t.mock.method(fs, "writeFileSync", (file, text, ...args) => {
        const name = path.basename(file).split(".tmp-")[0];
        assert.ok(["result.json", "error.json"].includes(name));
        events.push([name, JSON.parse(text)]);
        if (name === "result.json") {
          writes += 1;
          if (
            scenario === "write_always" ||
            scenario === "write_retryable" ||
            (scenario === "write_once" && writes === 1)
          ) {
            throw Object.assign(new Error("fixture write failure"), {
              retryable: scenario === "write_retryable",
            });
          }
        }
        return nativeWrite(file, text, ...args);
      });
      const observed = [];
      for (const run of laneControllers) {
        fs.rmSync(root, { recursive: true, force: true });
        fs.mkdirSync(root);
        writes = 0;
        events.length = 0;
        const calls = [];
        const packet = { target_units: [], evaluation_mode: "paired_reveal" };
        const runtime = {
          caseData: { case_id: "arithmetic" },
          packet: { prior: true },
          options: {
            strategy: "target_probe_ldh",
            evaluationMode: "paired_reveal",
            sampleRunner: (sample) => {
              assert.equal(sample.runtime.packet, packet);
              assert.deepEqual(runtime.packet, { prior: true });
              const { onProgress, ...args } = sample;
              assert.equal(typeof onProgress, run === laneControllers[0] ? "function" : "undefined");
              calls.push({ ...args, runtime: undefined });
              if (["sample_error", "provider_retry"].includes(scenario))
                throw Object.assign(new Error("fixture sample failure"), {
                  retryable: scenario === "provider_retry",
                });
              return {
                sample_id: sample.sampleId,
                status: "exhausted",
                bug_revealed: false,
              };
            },
          },
        };
        let result;
        try {
          result = {
            row: await run({
              runtime,
              packet,
              sampleId: "direct-001",
              sampleDir: root,
              priorAttempts: [],
              promptStyle: "direct",
              harnessRepairBudget: 1,
              lane: "direct_probe",
            }),
          };
        } catch (error) {
          result = {
            error: {
              type: error.name,
              message: error.message,
              retryable: error.retryable,
            },
          };
        }
        observed.push({
          result,
          calls,
          writes,
          events: structuredClone(events),
          files: fs
            .readdirSync(root)
            .sort()
            .map((name) => [
              name,
              fs.readFileSync(path.join(root, name), "utf8"),
            ]),
        });
      }
      assert.deepEqual(observed[0], observed[1]);
      assert.equal(observed[0].calls.length, 1);
      assert.equal(
        observed[0].writes,
        scenario === "write_once" || scenario === "write_always"
          ? 2
          : scenario === "provider_retry"
            ? 0
            : 1,
      );
    },
  );
}

const schedules = [1, 2].flatMap((unitCount) =>
  [
    [2, 2, 2],
    [0, 2, 1],
    [0, 0, 2],
    [0, 0, 0],
  ].flatMap((budgets) =>
    TARGET_PROBE_STRATEGIES.map((strategy) => ({
      unitCount,
      budgets,
      strategy,
    })),
  ),
);

for (const { unitCount, budgets, strategy } of schedules) {
  for (const mode of ["paired_reveal", "single_revision_discovery"]) {
  for (const scenario of ["exhausted", "revealed", "mixed", "error"]) {
    for (const limit of [1, 2, 3]) {
      test(
        `${mode} schedule: ${strategy} ${unitCount} units ${budgets} ${scenario} limit=${limit}`,
        { skip: !formalRoot },
        async () => {
          const root = fs.mkdtempSync(
            path.join(os.tmpdir(), "probe-schedule-"),
          );
          try {
            const options = runOptions({
              strategy,
              evaluationMode: mode,
              model: "fixture",
              directSamples: budgets[0],
              samples: budgets[1],
              softSamples: budgets[2],
              maxRevealCandidates: limit,
            });
            const packet = {
              strategy: options.strategy,
              evaluation_mode: mode,
              target_units: ["u1", "u2"].slice(0, unitCount).map((id) => ({
                unit_id: id,
                filepath: "arithmetic.ts",
                qualname: id,
                kind: "function",
              })),
            };
            const observed = [];
            for (const [index, controller] of controllers.entries()) {
              const calls = [];
              const runtime = {
                caseData: { case_id: "fixture" },
                options: {
                  ...options,
                  sampleRunner({ runtime: _, onProgress, ...args }) {
                    assert.equal(typeof onProgress, index === 0 ? "function" : "undefined");
                    calls.push(structuredClone(args));
                    if (scenario === "error") throw new Error("fixture error");
                    const revealed =
                      scenario === "revealed" ||
                      (scenario === "mixed" && args.sampleId.endsWith("001"));
                    return {
                      sample_id: args.sampleId,
                      status: scenario,
                      assets: [{ asset_id: "a", [mode === "single_revision_discovery" ? "stable_failure_candidate" : "bug_revealed"]: revealed }],
                    };
                  },
                },
              };
              const rows = await controller(
                runtime,
                structuredClone(packet),
                root,
              );
              const checkpoints = rows.map((row) =>
                JSON.parse(
                  fs.readFileSync(
                    path.join(root, "samples", row.sample_id, "result.json"),
                    "utf8",
                  ),
                ),
              );
              let progress = rows.length
                ? JSON.parse(
                    fs.readFileSync(path.join(root, "progress.json"), "utf8"),
                  )
                : null;
              if (index === 1 && progress) {
                progress = {
                  samples: progress.samples.map(({ sample_id, result_path }) => ({
                    sample_id, result_path,
                  })),
                };
              }
              observed.push({ rows, calls, checkpoints, progress });
            }
            assert.deepEqual(observed[0], observed[1]);
          } finally {
            fs.rmSync(root, { recursive: true, force: true });
          }
        },
      );
    }
  }
  }
}
