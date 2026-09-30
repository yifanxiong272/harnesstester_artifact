import assert from "node:assert/strict";
import fs from "node:fs";
import crypto from "node:crypto";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";
import { formalRoot, formalPath, sourceModule } from "./typescript_support.mjs";
import { buildTargetPacket } from "../typescript/input/target_packets.mjs";
import { runOptions } from "../typescript/run/options.mjs";
import {
  runTargetSample,
  runGuidedCaseSamples,
} from "../typescript/run/workflow.mjs";
import { runPreparedCase } from "../typescript/run/case.mjs";
import { CaseTimeBudgetExceeded } from "../typescript/run/deadline.mjs";
import { preparedValidation } from "../typescript/run/session.mjs";
import {
  buggyFailureSummary,
  repairDisposition,
  repairTracebackContext,
} from "../typescript/run/repair.mjs";
import { validationSummary } from "../typescript/run/session.mjs";
import { validationFailureKind } from "../typescript/run/reporting.mjs";
import { isDiscoveryFailure, failureFingerprint } from "../typescript/run/discovery.mjs";
import { removeManagedPaths } from "../typescript/support/storage.mjs";
import {
  assetResultRow,
  confirmRevealCandidate,
} from "../typescript/run/candidate.mjs";
import {
  parseProbePlan,
  parseProposalPartial,
} from "../typescript/prompt/proposal.mjs";
import {
  publicEntrypoints,
  priorAttemptLedger,
} from "../typescript/run/generation.mjs";

let formalSample;
let formalAssetResultRow;
let formalConfirm;
let formalValidationSummary;
let formalBuggyFailureSummary;
let formalLedger;
let formalDiscovery;
if (formalRoot) {
  const sourcePath = formalPath("run/workflow.mjs");
  let { source, tree, ts } = sourceModule(sourcePath);
  for (const statement of [...tree.statements].reverse()) {
    const literal = statement.moduleSpecifier;
    if (
      literal &&
      ts.isStringLiteral(literal) &&
      literal.text.startsWith(".")
    ) {
      source =
        source.slice(0, literal.getStart(tree)) +
        JSON.stringify(
          pathToFileURL(path.resolve(path.dirname(sourcePath), literal.text))
            .href,
        ) +
        source.slice(literal.end);
    }
  }
  const directory = fs.mkdtempSync(
    path.join(os.tmpdir(), "probe-formal-module-"),
  );
  const modulePath = path.join(directory, "workflow.mjs");
  fs.writeFileSync(
    modulePath,
    source +
      "\nexport { runTargetSample, assetResultRow, confirmRevealCandidate, validationSummary, buggyFailureSummary, priorAttemptLedger, isDiscoveryFailure, failureFingerprint };\n",
  );
  try {
    const formal = await import(pathToFileURL(modulePath).href);
    formalSample = formal.runTargetSample;
    formalAssetResultRow = formal.assetResultRow;
    formalConfirm = formal.confirmRevealCandidate;
    formalValidationSummary = formal.validationSummary;
    formalBuggyFailureSummary = formal.buggyFailureSummary;
    formalLedger = formal.priorAttemptLedger;
    formalDiscovery = formal;
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
}

for (const mode of ["paired_reveal", "single_revision_discovery"]) {
test(
  `prior attempt ledger matches formal grouping, recency, and truncation: ${mode}`,
  { skip: !formalLedger },
  () => {
    const base = {
      target_unit_ids: ["second", "first"],
      test_intent: "compare an arithmetic result",
      input_construction: "zero",
      primary_oracle: "equality",
      oracle_family: " shared family ",
    };
    const assets = [
      { passed: true },
      { status: "passed" },
      { status: "assertion_failed" },
      { status: "needs_repair" },
      {},
    ].map((summary, index) => ({ ...base, asset_id: `a${index}`, [mode === "single_revision_discovery" ? "latest" : "buggy"]: summary }));
    assets.push(
      {
        ...base,
        oracle_family: "another family",
        semantic_fingerprint: "known",
      },
      { ...base, status: "error", semantic_fingerprint: "failed" },
      { ...base, oracle_family: "", primary_oracle: "different equality" },
      { status: "error" },
      {},
      assets[0],
    );
    for (const ordered of [assets, [...assets].reverse()]) {
      for (let length = 0; length <= ordered.length; length += 1) {
        const rows = ordered.slice(0, length).map((asset) => ({
          evaluation_mode: mode,
          assets: [asset],
        }));
        const original = structuredClone(rows);
        for (const limit of [-1, 0, 1, 2, 18]) {
          assert.deepEqual(
            priorAttemptLedger(rows, limit),
            formalLedger(rows, limit),
          );
          assert.deepEqual(rows, original);
        }
      }
    }
  },
);
}

for (const collection of [undefined, {}, { exact_single_test: true }]) {
  for (const status of [
    undefined,
    "passed",
    "assertion_failed",
    "needs_repair",
  ]) {
    test(
      `validation summary and failure prompts retain evidence: ${status}, ${JSON.stringify(collection)}`,
      { skip: !formalValidationSummary },
      () => {
        const result = {
          status,
          collection,
          exit_code: status === "passed" ? 0 : 1,
          timed_out: status === "needs_repair",
          signal: "",
          test_counts: { total: 2, passed: 1, failed: 1 },
          output_tail: "fixture output ".repeat(400),
          evidence: {
            passed: status === "passed",
            classification_source: "structured_reporter",
            classification_reason: "fixture reason",
            diagnostics: { tests: [{ nodeid: "counter", state: status }] },
            failed_hooks: [],
            failed_nodeids: ["counter"],
            failure_excerpt: "fixture failure",
          },
        };
        const original = structuredClone(result);
        const actual = validationSummary("fixture-revision", result);
        const expected = formalValidationSummary("fixture-revision", result);
        assert.deepEqual(expected.collection, collection || {});
        assert.equal(Object.hasOwn(actual, "collection"), false);
        // Repair and minimization receive identical projected failure evidence.
        for (const limit of [0, 800, 8000]) {
          assert.equal(
            JSON.stringify(buggyFailureSummary(actual, limit)),
            JSON.stringify(formalBuggyFailureSummary(expected, limit)),
          );
        }
        delete expected.collection;
        assert.deepEqual(actual, expected);
        assert.deepEqual(result, original);
      },
    );
  }
}

const SAMPLE_METADATA_FIELDS = [
  "boundary_plan", "plan_context", "plan_context_request_count",
  "plan_retrieved_context_count", "plan_parse_errors", "plan_parse_error_count",
  "parse_errors", "parse_error_count", "dropped_duplicate_assets",
  "dropped_duplicate_asset_count",
];

const REPAIR_DERIVED_FIELDS = new Set([
  "called", "attempts", "attempt_count", "context_request_count",
  "retrieved_context_count", "parse_error_count", "diagnosis",
  "additive_variant", "use_repaired",
]);

const ASSET_EXPLANATION_FIELDS = [
  "supporting_evidence", "expected_observation", "novelty_from_prior", "bug_hypothesis",
];

function repairEvidence(record) {
  if (!record.called) {
    const { attempt_count, ...evidence } = record;
    return evidence;
  }
  const attempts = record.attempts || [record];
  assert.equal(record.attempt_count, attempts.length);
  return {
    called: true,
    attempts: attempts.map((item) => Object.fromEntries(
      Object.entries(item).filter(([key]) => !REPAIR_DERIVED_FIELDS.has(key)),
    )),
  };
}

function formalEvidence(value) {
  if (Array.isArray(value)) return value.map(formalEvidence);
  if (value && typeof value === "object" && !Buffer.isBuffer(value)) {
    const result = Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, formalEvidence(item)]),
    );
    if (Object.hasOwn(result, "sample_id") && Array.isArray(result.assets)) {
      // Phase files are compared byte-for-byte separately below.
      for (const key of SAMPLE_METADATA_FIELDS) delete result[key];
      assert.equal(result.asset_count, result.assets.length);
      delete result.asset_count;
      if (Object.hasOwn(result, "revealed_asset_ids")) {
        assert.deepEqual(result.revealed_asset_ids,
          result.assets.filter((asset) => asset.status === "revealed")
            .map((asset) => asset.asset_id));
        delete result.revealed_asset_ids;
      }
      if (Object.hasOwn(result, "stable_failure_asset_ids")) {
        assert.deepEqual(result.stable_failure_asset_ids,
          result.assets.filter(asset => asset.status === "stable_failure_candidate").map(asset => asset.asset_id));
        delete result.stable_failure_asset_ids;
      }
    }
    if (Object.hasOwn(result, "repair_classification")) {
      assert.deepEqual(result.repair_classification, repairDisposition(result.latest || result.buggy));
      delete result.repair_classification;
    }
    if (Object.hasOwn(result, "semantic_fingerprint") && (Object.hasOwn(result, "buggy") || Object.hasOwn(result, "latest"))) {
      for (const key of ASSET_EXPLANATION_FIELDS) delete result[key];
    }
    if (Object.hasOwn(result, "fixed_failure_kind")) {
      assert.equal(result.fixed_failure_kind, validationFailureKind(result.fixed));
      delete result.fixed_failure_kind;
    }
    if (Object.hasOwn(result, "use_minimized") && Object.hasOwn(result, "called")) {
      if (Object.hasOwn(result, "attempt_count")) {
        assert.equal(result.attempt_count, (result.attempts || [result]).length);
        delete result.attempt_count;
      }
      if (Object.hasOwn(result, "preserve_retry_count")) {
        assert.equal(result.preserve_retry_count, 1);
        assert.equal(result.attempts.length, 2);
        delete result.preserve_retry_count;
      }
      delete result.parse_error_count;
    }
    for (const key of ["harness_repair", "contract_agnostic_repair"])
      if (Object.hasOwn(result, key)) result[key] = repairEvidence(result[key]);
    if (
      Object.hasOwn(result, "required_runs") &&
      Object.hasOwn(result, "stable") &&
      Array.isArray(result.runs)
    ) {
      for (const run of result.runs) delete run.buggy_failure_fingerprint;
    }
    if (result.latest && result.confirmation?.initial_failure_fingerprint) {
      // Migrate only fingerprint representation; still compare every stability decision.
      result.confirmation.initial_failure_fingerprint = failureFingerprint(result.latest);
      for (const run of result.confirmation.runs)
        run.failure_fingerprint = failureFingerprint(run.latest);
    }
    if (Array.isArray(result.fixed_variants)) {
      assert.deepEqual(result.original_variant, result.fixed_variants[0]);
      delete result.original_variant;
      const revealed = result.fixed_variants.filter(
        (variant) => variant.bug_revealed,
      );
      if (revealed.length) {
        assert.deepEqual(result.revealed_variants, revealed);
        assert.deepEqual(
          result.revealed_variant_ids,
          revealed.map((variant) => variant.variant_id),
        );
        assert.deepEqual(
          result.revealed_asset_ids,
          [...new Set(revealed.map((variant) => variant.asset_id))].sort(),
        );
        delete result.revealed_variants;
        delete result.revealed_variant_ids;
        delete result.revealed_asset_ids;
      }
    }
    return result;
  }
  return value;
}

function fixture(t, secondTarget = false) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-ts-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const roots = {};
  for (const [kind, increment] of [
    ["buggy", 1],
    ["fixed", 2],
  ]) {
    const checkout = path.join(root, kind);
    fs.mkdirSync(path.join(checkout, "src"), { recursive: true });
    fs.writeFileSync(
      path.join(checkout, "src/arithmetic.ts"),
      `/** Advance by two. */\nexport function advance(value: number) {\n  return value + ${increment};\n}\n` +
        (secondTarget
          ? "\nexport function double(value: number) { return value * 2; }\n"
          : ""),
    );
    fs.writeFileSync(
      path.join(checkout, "package.json"),
      '{"private":true,"type":"module"}\n',
    );
    fs.writeFileSync(
      path.join(checkout, "vitest.config.ts"),
      'export default { test: { include: ["test/**/*.test.ts"] } };\n',
    );
    if (process.env.PROBE_TEST_NODE_MODULES)
      fs.symlinkSync(
        path.resolve(process.env.PROBE_TEST_NODE_MODULES),
        path.join(checkout, "node_modules"),
        "dir",
      );
    roots[kind] = checkout;
  }
  const caseData = {
    case_id: "arithmetic",
    revisions: { buggy: "before", fixed: "after" },
    patch_targets: {
      target_units: [
        {
          unit_id: "u1",
          filepath: "src/arithmetic.ts",
          qualname: "advance",
          kind: "function",
          start_line: 2,
          end_line: 4,
        },
      ],
    },
  };
  if (secondTarget)
    caseData.patch_targets.target_units.push({
      unit_id: "u2",
      filepath: "src/arithmetic.ts",
      qualname: "double",
      kind: "function",
      start_line: 6,
      end_line: 6,
    });
  const packet = buildTargetPacket({
    project: "fixture",
    strategy: "target_probe_ldh",
    projectRoot: roots.buggy,
    targetUnits: caseData.patch_targets.target_units,
    testCommand: [
      "pnpm",
      "exec",
      "vitest",
      "run",
      "--config",
      "vitest.config.ts",
      "<generated-test-file>",
    ],
  });
  const entry =
    packet.public_target_routes.targets[0].entrypoints[0].entrypoint_id;
  const plan = {
    boundary_plan: [
      {
        boundary_id: "boundary-001",
        target_unit_ids: ["u1"],
        route: { entrypoint_id: entry },
        probe: {
          test_intent: "advance by two",
          activation_conditions: ["call advance with zero"],
        },
        invariant: {
          independent_oracle: "zero advances to two",
          supporting_evidence: "public docstring",
          expected_observation: "two",
          oracle_mode: "assertion",
        },
        oracle_family: "arithmetic increment",
        novelty_from_prior: "first attempt",
        bug_hypothesis: "incorrect increment",
      },
    ],
    context_requests: [],
  };
  const asset = {
    asset_id: "asset-001",
    boundary_id: "boundary-001",
    input_construction: "call with zero",
    observable_oracle: "public return is two",
    primary_oracle: "public result equality",
    mocking_plan: "none",
    test_file: "test/generated/benchmarkbr/test_advance.test.ts",
    append_code:
      'import { expect, it } from "vitest";\nimport { advance } from "../../../src/arithmetic";\nit("advances by two", () => { expect(advance(0)).toBe(2); });\n',
  };
  return { root, roots, caseData, packet, plan, asset };
}

for (const renamed of [false, true]) {
  test(
    `canonical result metadata matches formal: renamed ${renamed}`,
    { skip: !formalAssetResultRow },
    (t) => {
      const { root, roots, packet, plan, asset: raw } = fixture(t);
      raw.unexpected_metadata = "discarded by parsing";
      const { proposal } = parseProposalPartial(
        { assets: [raw] },
        {
          projectRoot: roots.buggy,
          canonicalPlan: parseProbePlan(plan).plan,
          publicEntrypoints: publicEntrypoints(packet),
        },
      );
      for (const fingerprint of ["", "saved-fingerprint"]) {
        const asset = { ...proposal.assets[0] };
        if (fingerprint) asset.semantic_fingerprint = fingerprint;
        const snapshot = structuredClone(asset);
        const state = {
          asset,
          proposalPath: path.join(root, "proposal.json"),
          buggy: { summary: { status: "assertion_failed", passed: false } },
        };
        for (const metadata of [
          {},
          { record: {} },
          { record: { called: true } },
        ]) {
          const details = {
            originalAsset: renamed ? { ...asset, asset_id: "original" } : asset,
            harnessRepair: metadata,
            minimization: metadata,
          };
          const actual = assetResultRow(state, details);
          const expected = formalAssetResultRow(
            asset,
            state.proposalPath,
            state.buggy,
            { ...details, repairClassification: repairDisposition(state.buggy.summary) },
          );
          assert.deepEqual(expected.repair_classification, repairDisposition(actual.buggy));
          delete expected.repair_classification;
          const expectedLedger = priorAttemptLedger([{ assets: [expected] }]);
          for (const key of ASSET_EXPLANATION_FIELDS) {
            assert.equal(expected[key], snapshot[key]);
            delete expected[key];
          }
          assert.deepEqual(actual, expected);
          assert.deepEqual(asset, snapshot);
          for (const key of [
            "append_code",
            "mocking_plan",
            "unexpected_metadata",
            ...ASSET_EXPLANATION_FIELDS,
          ])
            assert.equal(Object.hasOwn(actual, key), false);
          assert.deepEqual(
            priorAttemptLedger([{ assets: [actual] }]),
            expectedLedger,
          );
        }
      }
    },
  );
}

for (const count of [1, 3]) {
  for (const changedOutcome of [null, "buggy", "fixed"]) {
    test(
      `confirmation uses revision outcomes: ${count} runs, changed ${changedOutcome}`,
      { skip: !formalConfirm },
      (t) => {
        const root = fs.mkdtempSync(
          path.join(os.tmpdir(), "probe-confirmation-"),
        );
        t.after(() => fs.rmSync(root, { recursive: true, force: true }));
        const state = {
          asset: { test_asset_sha256: "fixture" },
          sampleDir: root,
        };
        const results = [];
        for (const confirm of [confirmRevealCandidate, formalConfirm]) {
          const calls = [];
          const runtime = {
            options: {
              revealConfirmationRuns: count,
              validationRunner({ revisionKind, asset, assetDir }) {
                calls.push({ revisionKind, asset, assetDir });
                const attempt = Math.ceil(calls.length / 2);
                let passed = revisionKind === "fixed";
                if (attempt === count && revisionKind === changedOutcome)
                  passed = !passed;
                return {
                  summary: {
                    passed,
                    status: passed ? "passed" : "assertion_failed",
                    failed_nodeids: passed
                      ? []
                      : [`case.test.ts > case ${attempt}`],
                    failure_excerpt: passed ? "" : `assertion ${attempt}`,
                  },
                };
              },
            },
          };
          results.push([confirm({ runtime, state, variant: "base" }), calls]);
        }
        const [actual, calls] = results[0];
        assert.deepEqual(results[0], formalEvidence(results[1]));
        assert.equal(calls.length, count * 2);
        assert.equal(actual.stable, changedOutcome === null);
        assert.deepEqual(
          actual.runs.slice(0, -1).map((run) => run.buggy.failure_excerpt),
          Array.from(
            { length: count - 1 },
            (_, index) => `assertion ${index + 1}`,
          ),
        );
      },
    );
  }
}

for (const failureAt of [1, 2, 3, 4]) {
  for (const expired of [false, true]) {
    test(
      `confirmation stops at failed revision call ${failureAt}, deadline=${expired}`,
      { skip: !formalConfirm },
      (t) => {
        const root = fs.mkdtempSync(
          path.join(os.tmpdir(), "probe-confirm-error-"),
        );
        t.after(() => fs.rmSync(root, { recursive: true, force: true }));
        const state = {
          asset: { test_asset_sha256: "fixture" },
          sampleDir: root,
        };
        const error = expired
          ? new CaseTimeBudgetExceeded()
          : new Error("fixture runner failure");
        const observed = [];
        for (const confirm of [confirmRevealCandidate, formalConfirm]) {
          const calls = [];
          const runtime = {
            options: {
              revealConfirmationRuns: 3,
              validationRunner({ revisionKind, asset, assetDir }) {
                calls.push({ revisionKind, asset, assetDir });
                if (calls.length === failureAt) throw error;
                return {
                  summary: {
                    passed: revisionKind === "fixed",
                    status:
                      revisionKind === "fixed" ? "passed" : "assertion_failed",
                  },
                };
              },
            },
          };
          assert.throws(
            () => confirm({ runtime, state, variant: "base" }),
            (actual) => actual === error,
          );
          assert.equal(calls.length, failureAt);
          observed.push(calls);
        }
        assert.deepEqual(observed[0], observed[1]);
        assert.deepEqual(
          observed[0].map((call) => call.revisionKind),
          ["buggy", "fixed", "buggy", "fixed"].slice(0, failureAt),
        );
      },
    );
  }
}

function fixedModel(responses) {
  const prompts = [];
  return {
    prompts,
    responses,
    async complete(prompt) {
      prompts.push(prompt);
      assert.ok(responses.length, "unexpected model call");
      return {
        choices: [{ message: { content: JSON.stringify(responses.shift()) } }],
      };
    },
  };
}

function options(extra = {}) {
  return runOptions({
    model: "fixture",
    provider: "openai",
    strategy: "target_probe_ldh",
    directSamples: 1,
    samples: 0,
    softSamples: 0,
    minimizeBuggyFailuresPerSample: 0,
    caseTimeBudgetSeconds: 60,
    ...extra,
  });
}

function scriptedValidation(scenario) {
  const calls = [];
  const validate = ({ revisionKind, asset, assetDir }) => {
    calls.push([revisionKind, asset.asset_id, asset.append_code]);
    if (
      (scenario === "repair_validation_error" &&
        ["harness-repair-", "contract-agnostic-repair-"].some((prefix) =>
          path.basename(assetDir).startsWith(prefix),
        )) ||
      (scenario === "minimize_validation_error" &&
        path.basename(assetDir) === "minimized")
    )
      throw new Error("fixture validation failure");
    const count = calls.filter(([kind]) => kind === revisionKind).length;
    let passed = revisionKind === "fixed";
    let status = passed ? "passed" : "assertion_failed";
    if (scenario === "both_fail") {
      passed = false;
      status = "assertion_failed";
    }
    if (scenario === "unstable" && revisionKind !== "fixed" && count > 1) {
      passed = true;
      status = "passed";
    }
    if (scenario === "nonassertion" && revisionKind !== "fixed")
      status = "needs_repair";
    if (
      scenario.startsWith("repair") &&
      asset.append_code.includes("missing_name")
    ) {
      passed = false;
      status = "needs_repair";
    }
    if (
      scenario.startsWith("minimize_preserve") &&
      revisionKind !== "fixed" &&
      path.basename(assetDir) === "minimized" &&
      (!assetDir.split(path.sep).includes("minimization-preserve-001") ||
        scenario.endsWith("lost"))
    ) {
      passed = true;
      status = "passed";
    }
    const summary = {
      passed,
      status,
      phase: "vitest",
      exit_code: passed ? 0 : 1,
      timed_out: false,
      failed_nodeids: passed ? [] : [`${asset.test_file}::advances by two`],
      failure_excerpt: passed
        ? ""
        : status === "needs_repair"
          ? "ImportError: missing_name"
          : "AssertionError: 1 != 2",
    };
    return { summary, result: { evidence: summary }, materialized: {} };
  };
  validate.calls = calls;
  return validate;
}

function exceptionSummary(changes = {}) {
  return {
    status: "needs_repair", passed: false, timed_out: false,
    classification_source: "structured_reporter",
    classification_reason: "non_assertion_or_incomplete_execution",
    failed_nodeids: ["test/advance.test.ts > advance"], failed_hooks: [],
    failure_excerpt: "ValueError: cannot advance",
    ...changes,
  };
}

test("discovery eligibility matches formal; semantic paths remain distinct", () => {
  const variants = [
    [{}, true], [{ status: "assertion_failed" }, true],
    [{ status: "passed", passed: true }, false], [{ timed_out: true }, false],
    [{ classification_source: "text" }, false],
    [{ classification_reason: "collection_error" }, false],
    [{ failed_nodeids: [] }, false], [{ failed_hooks: ["beforeEach"] }, false],
  ];
  for (const [changes, eligible] of variants) {
    const summary = exceptionSummary(changes);
    assert.equal(isDiscoveryFailure(summary), eligible);
    if (formalDiscovery) {
      assert.equal(isDiscoveryFailure(summary), formalDiscovery.isDiscoveryFailure(summary));
    }
  }
  const first = exceptionSummary({ failure_excerpt: "Error at /tmp/one/source.ts:12:3" });
  const second = exceptionSummary({ failure_excerpt: "Error at /tmp/two/source.ts:89:5" });
  assert.notEqual(failureFingerprint(first), failureFingerprint(second));
});

for (const strategy of ["target_probe_ldh", "target_probe_contract_agnostic"]) {
  for (const [scenario, status] of [
    ["passed", "latest_passed"], ["exception", "stable_failure_candidate"],
    ["setup", "latest_needs_repair"], ["fingerprint_drift", "unstable_failure"],
    ["repair_passed", "latest_needs_repair"], ["minimized_drift", "stable_failure_candidate"],
  ]) {
    test(`discovery selection ${strategy} ${scenario}`, async t => {
      const { root, roots, caseData, packet, plan, asset } = fixture(t);
      const mode = "single_revision_discovery";
      Object.assign(packet, { strategy, evaluation_mode: mode });
      const replies = [plan, { assets: [asset] }];
      if (["exception", "setup"].includes(scenario)) replies.push({ action: "retain_original" });
      if (scenario === "repair_passed") replies.push({ action: "repair", assets: [{ ...asset, asset_id: "repaired" }] });
      if (scenario === "minimized_drift") replies.push({ assets: [{ ...asset, asset_id: "minimized" }] });
      const observed = [];
      for (const [index, run] of [runTargetSample, ...(formalSample ? [formalSample] : [])].entries()) {
        const model = fixedModel(structuredClone(replies));
        const calls = [];
        const runtime = {
          caseData, packet, env: {},
          manifest: { evaluation_mode: mode, source_roots: ["src"], latest_checkout: { path: roots.buggy } },
          options: options({ strategy, evaluationMode: mode, modelClient: model,
            minimizeBuggyFailuresPerSample: Number(scenario === "minimized_drift"),
            validationRunner({ revisionKind, asset, assetDir }) {
              assert.equal(revisionKind, "latest");
              calls.push([revisionKind, asset, assetDir]);
              const summary = exceptionSummary({ status: "assertion_failed" });
              if (["exception", "setup", "repair_passed"].includes(scenario)) summary.status = "needs_repair";
              if (scenario === "setup") summary.failed_hooks = ["beforeEach"];
              if (scenario === "passed" || asset.asset_id === "repaired") Object.assign(summary, { status: "passed", passed: true, failed_nodeids: [] });
              if ((scenario === "fingerprint_drift" && calls.length === 2) || (scenario === "minimized_drift" && path.basename(assetDir).startsWith("minimized-confirmation"))) summary.failure_excerpt = "different failure";
              return { summary, result: { evidence: summary }, materialized: {} };
            },
          }),
        };
        let row = await run({ runtime, packet: structuredClone(packet), sampleId: "direct-001",
          sampleDir: path.join(root, "sample"), priorAttempts: [], promptStyle: "direct", harnessRepairBudget: 1 });
        assert.equal(model.responses.length, 0);
        if (index) row = formalEvidence(row);
        const result = row.assets[0];
        assert.equal(result.status, status);
        assert.ok(!result.buggy && !result.fixed);
        if (scenario === "minimized_drift") {
          assert.equal(result.asset_id, asset.asset_id);
          assert.equal(result.confirmation.stable, true);
          assert.equal(calls.length, 6);
        }
        if (scenario === "fingerprint_drift") {
          assert.equal(calls.length, 3);
          assert.deepEqual(result.confirmation.runs.map(run => run.passed), [false, true]);
        }
        observed.push({ row, calls, prompts: model.prompts });
      }
      if (observed.length === 2) assert.deepEqual(observed[0], observed[1]);
    });
  }
}

for (const [scenario, pairedExpected, strategy] of [
  ["stable", true],
  ["unstable", false],
  ["both_fail", false],
  ["nonassertion", true],
  ["repair_direct", true],
  ["repair_context", true],
  ["repair_retain", false],
  ["repair_disabled", false],
  ["repair_budget_exhausted", false],
  ["repair_extra", true],
  ["repair_twice", true],
  ["repair_invalid_between", true],
  ["repair_twice_minimize", true],
  ["repair_then_retain", false],
  ["repair_then_invalid", false],
  ["repair_validation_error", false],
  ["repair_boundary_switch", false],
  ["repair_target_override", true],
  ["initial_context", true],
  ["minimize", true],
  ["minimize_preserve", true],
  ["minimize_preserve_lost", true],
  ["minimize_invalid", true],
  ["minimize_extra", true],
  ["minimize_validation_error", true],
  ["minimize_boundary_switch", true],
  ["minimize_target_override", true],
].flatMap(([scenario, expected]) =>
  ["target_probe_ldh", "target_probe_contract_agnostic"]
    .filter(
      (strategy) =>
        strategy === "target_probe_ldh" ||
        !["repair_context", "initial_context"].includes(scenario),
    )
    .map((strategy) => [scenario, expected, strategy]),
)) {
  for (const discovery of [false, true]) {
  if (discovery && scenario === "nonassertion") continue;
  const mode = discovery ? "single_revision_discovery" : "paired_reveal";
  const expected = discovery && scenario === "both_fail" ? true : pairedExpected;
  test(`candidate outcome: ${mode} ${strategy} ${scenario}`, async (t) => {
    const { root, roots, caseData, packet, plan, asset } = fixture(
      t,
      scenario.endsWith("boundary_switch"),
    );
    packet.strategy = strategy;
    packet.evaluation_mode = mode;
    const repairKey =
      strategy === "target_probe_ldh"
        ? "harness_repair"
        : "contract_agnostic_repair";
    const repairBudget = scenario === "repair_budget_exhausted" ? 0 : 1;
    if (scenario.endsWith("boundary_switch")) {
      const boundary = structuredClone(plan.boundary_plan[0]);
      Object.assign(boundary, {
        boundary_id: "boundary-002",
        target_unit_ids: ["u2"],
      });
      boundary.route.entrypoint_id =
        packet.public_target_routes.targets[1].entrypoints[0].entrypoint_id;
      plan.boundary_plan.push(boundary);
    }
    if (scenario === "initial_context")
      plan.context_requests = [
        {
          kind: "function_definition",
          filepath: "src/arithmetic.ts",
          qualname: "advance",
          reason: "inspect contract",
        },
      ];
    const original = scenario.startsWith("repair")
      ? {
          ...asset,
          append_code: asset.append_code.replace(
            "{ advance }",
            "{ missing_name }",
          ),
        }
      : asset;
    const responses = [plan, { assets: [original] }];
    if (scenario === "repair_context") {
      responses.push(
        {
          action: "request_context",
          diagnosis: "wrong import",
          requests: [
            {
              kind: "module_context",
              filepath: "src/arithmetic.ts",
              reason: "check public name",
            },
          ],
        },
        { assets: [asset] },
      );
    } else if (
      scenario.endsWith("boundary_switch") ||
      scenario.endsWith("target_override")
    ) {
      const changed = {
        ...asset,
        ...(scenario.endsWith("boundary_switch")
          ? { boundary_id: "boundary-002" }
          : { target_unit_ids: ["unknown"] }),
      };
      responses.push({
        assets: [changed],
        ...(scenario.startsWith("repair") ? { action: "repair" } : {}),
      });
    } else if (
      ["repair_direct", "repair_extra", "repair_validation_error"].includes(
        scenario,
      )
    )
      responses.push({
        action: "repair",
        diagnosis: "wrong import",
        assets: scenario === "repair_extra" ? [asset, asset] : [asset],
      });
    else if (
      ["repair_twice", "repair_then_retain", "repair_then_invalid",
        "repair_invalid_between", "repair_twice_minimize"].includes(
        scenario,
      )
    ) {
      responses.push({
        action: "repair",
        assets: [{
          ...original,
          asset_id: "attempt-1",
          append_code: `${original.append_code}\n// first repair\n`,
        }],
      });
      if (scenario === "repair_invalid_between")
        responses.push({ action: "repair", assets: [{}] });
      responses.push(
        ["repair_twice", "repair_invalid_between", "repair_twice_minimize"].includes(scenario)
          ? { action: "repair", assets: [{ ...asset, asset_id: "attempt-2" }] }
          : scenario === "repair_then_retain"
            ? { action: "retain_original" }
            : { action: "repair", assets: [{}] },
      );
      if (scenario === "repair_twice_minimize")
        responses.push({ assets: [{ ...asset, asset_id: "minimized" }] });
    } else if (scenario === "repair_retain")
      responses.push({
        action: "retain_original",
        diagnosis: "retain original evidence",
      });
    else if (scenario === "minimize_invalid") responses.push({ assets: [] });
    else if (scenario.startsWith("minimize")) {
      responses.push({
        assets: scenario === "minimize_extra" ? [asset, asset] : [asset],
      });
      if (scenario.startsWith("minimize_preserve"))
        responses.push({ assets: [asset] });
    }
    const originalResponses = structuredClone(responses);
    const originalPacket = structuredClone(packet);
    const model = fixedModel(responses);
    const runtime = {
      caseData,
      packet,
      env: {},
      manifest: {
        case_id: caseData.case_id,
        evaluation_mode: mode,
        source_roots: ["src"],
        [`${discovery ? "latest" : "buggy"}_checkout`]: { path: roots.buggy },
      },
      options: options({
        strategy,
        evaluationMode: mode,
        modelClient: model,
        validationRunner: scriptedValidation(scenario),
        minimizeBuggyFailuresPerSample: Number(
          scenario.startsWith("minimize") || scenario === "repair_twice_minimize",
        ),
        harnessRepairAttempts: scenario === "repair_invalid_between" ? 3 : [
          "repair_twice",
          "repair_then_retain",
          "repair_then_invalid",
          "repair_twice_minimize",
        ].includes(scenario)
          ? 2
          : Number(scenario !== "repair_disabled"),
      }),
    };
    const row = await runTargetSample({
      runtime,
      packet,
      sampleId: "direct-001",
      sampleDir: path.join(root, "samples/direct-001"),
      priorAttempts: [],
      promptStyle: "direct",
      harnessRepairBudget: repairBudget,
    });
    assert.equal(Boolean(row[discovery ? "stable_failure_candidate" : "bug_revealed"]), expected, JSON.stringify(row));
    if (discovery) {
      assert.ok(runtime.options.validationRunner.calls.every(call => call[0] === "latest"));
      assert.ok(row.assets.every(asset => !asset.fixed && !asset.buggy));
    }
    for (const key of SAMPLE_METADATA_FIELDS) assert.equal(Object.hasOwn(row, key), false);
    for (const key of ["asset_count", "revealed_asset_ids"])
      assert.equal(Object.hasOwn(row, key), false);
    for (const result of row.assets) {
      assert.equal(Object.hasOwn(result, "repair_classification"), false);
      const minimized = result.minimization || {};
      for (const attempt of [minimized, ...(minimized.attempts || [])])
        for (const key of ["attempt_count", "preserve_retry_count", "parse_error_count"])
          assert.equal(Object.hasOwn(attempt, key), false);
    }
    assert.equal(responses.length, 0);
    if (["repair_disabled", "repair_budget_exhausted"].includes(scenario)) {
      assert.equal(row.assets[0][repairKey].called, false);
      assert.equal(model.prompts.length, 2);
    }
    const repair = row.assets[0][repairKey];
    if (repair?.called) {
      assert.deepEqual(Object.keys(repair).sort(), ["attempts", "called"]);
      for (const [index, attempt] of repair.attempts.entries()) {
        assert.equal(attempt.attempt, index + 1);
        for (const key of REPAIR_DERIVED_FIELDS)
          assert.equal(Object.hasOwn(attempt, key), false);
      }
      if (["repair_twice", "repair_then_retain", "repair_then_invalid",
        "repair_twice_minimize"].includes(scenario))
        assert.equal(repair.attempts.length, 2);
      if (scenario === "repair_invalid_between") {
        assert.equal(repair.attempts.length, 3);
        assert.ok(repair.attempts[1].error);
        assert.match(model.prompts[3], /first repair/u);
        assert.match(model.prompts[4], /first repair/u);
      }
      for (const attempt of repair.attempts)
        if (attempt.sample_dir)
          assert.equal(path.basename(path.dirname(attempt.sample_dir)), asset.asset_id);
    }
    if (expected && !discovery) {
      const revealed = row.assets[0].fixed_variants.filter(
        (variant) => variant.bug_revealed,
      );
      assert.equal(revealed[0].confirmation.stable, true);
      for (const variant of revealed)
        for (const run of variant.confirmation.runs)
          assert.deepEqual(Object.keys(run).sort(), [
            "attempt",
            "buggy",
            "fixed",
            "passed",
            "test_asset_sha256",
          ]);
    }
    if (scenario === "repair_context") {
      const attempt = repair.attempts[0];
      const decision = JSON.parse(fs.readFileSync(attempt.context_request_path));
      const context = JSON.parse(fs.readFileSync(attempt.retrieved_context_path));
      assert.equal(decision.action, "request_context");
      assert.equal(context.requested_context.requests.length, 1);
      assert.equal(context.requested_context.requests[0].status, "found");
      assert.match(model.prompts.at(-1), /function advance/u);
    }
    if (scenario === "initial_context")
      assert.match(model.prompts[1], /function advance/u);
    if (scenario === "minimize")
      assert.equal(row.assets[0].minimization.use_minimized, true);
    if (scenario === "repair_twice_minimize") {
      const result = row.assets[0];
      assert.equal(result.asset_id, "minimized");
      if (!discovery) assert.deepEqual(result.fixed_variants.map((v) => v.variant), [
        "base", "repaired", "minimized",
      ]);
      assert.equal(path.dirname(result.proposal_path),
        path.join(repair.attempts.at(-1).sample_dir, "minimized"));
    }
    if (scenario.endsWith("boundary_switch")) {
      const stage = scenario.startsWith("repair") ? repairKey : "minimization";
      const record = scenario.startsWith("repair")
        ? row.assets[0][stage].attempts.at(-1)
        : row.assets[0][stage];
      assert.match(record.error.message, /boundary_id/u);
    }
    if (scenario.startsWith("minimize_preserve")) {
      assert.equal(row.assets[0].minimization.attempts.length, 2);
      assert.equal(
        row.assets[0].minimization.use_minimized,
        scenario === "minimize_preserve",
      );
    }
    if (formalSample) {
      const formalModel = fixedModel(originalResponses);
      const formalRuntime = {
        ...runtime,
        packet: originalPacket,
        options: {
          ...runtime.options,
          modelClient: formalModel,
          validationRunner: scriptedValidation(scenario),
        },
      };
      const sampleDir = path.join(root, "samples/direct-001");
      const outputs = () =>
        Object.fromEntries(
          fs
            .readdirSync(sampleDir, { recursive: true })
            .filter((file) => fs.statSync(path.join(sampleDir, file)).isFile())
            .map((file) => {
              const content = fs.readFileSync(path.join(sampleDir, file));
              // Result objects preserve their fields, not JSON key order.
              return [
                file,
                file.endsWith("result.json") ? JSON.parse(content) : content,
              ];
            }),
        );
      const savedOutputs = outputs();
      fs.rmSync(sampleDir, { recursive: true, force: true });
      const formalRow = await formalSample({
        runtime: formalRuntime,
        packet: originalPacket,
        sampleId: "direct-001",
        sampleDir: path.join(root, "samples/direct-001"),
        priorAttempts: [],
        promptStyle: "direct",
        harnessRepairBudget: repairBudget,
      });
      assert.deepEqual(row, formalEvidence(formalRow));
      assert.deepEqual(
        priorAttemptLedger([row]),
        priorAttemptLedger([formalRow]),
      );
      assert.deepEqual(model.prompts, formalModel.prompts);
      assert.deepEqual(
        runtime.options.validationRunner.calls,
        formalRuntime.options.validationRunner.calls,
      );
      assert.deepEqual(savedOutputs, formalEvidence(outputs()));
    }
  });
  }
}

for (const scenario of [
  "forged_metadata",
  "redefined_plan",
  "unknown_boundary",
  "nonlist_plan",
  "nonobject_boundary",
  "missing_exhaustion",
  "exhausted",
  "unknown_target",
  "empty_targets",
  "duplicate_targets",
  "unknown_entrypoint",
  "mixed_assets",
  "plan_notes",
  "focused_target_override",
  "focused_plan_mismatch",
  "focused_joint_targets",
  "whole_target_alternative",
  "mixed_target_assets",
]) {
  test(
    `canonical plan binding matches formal: ${scenario}`,
    { skip: !formalSample },
    async (t) => {
      const { root, roots, packet, plan, asset } = fixture(t, true);
      const implementation = { assets: [asset] };
      const boundary = plan.boundary_plan[0];
      if (scenario.startsWith("focused")) packet.focus_target_unit_id = "u1";
      if (scenario === "forged_metadata")
        Object.assign(asset, {
          target_unit_ids: ["unknown"],
          public_entrypoint_id: "unknown",
          oracle_mode: "crash",
          test_intent: "different intent",
        });
      else if (scenario === "redefined_plan") {
        const replacement = structuredClone(boundary);
        replacement.target_unit_ids = ["u2"];
        replacement.probe.test_intent = "different intent";
        implementation.boundary_plan = [replacement];
      } else if (scenario === "nonlist_plan") plan.boundary_plan = {};
      else if (scenario === "nonobject_boundary")
        plan.boundary_plan = ["not a boundary"];
      else if (["missing_exhaustion", "exhausted"].includes(scenario)) {
        plan.boundary_plan = [];
        if (scenario === "exhausted")
          plan.exhausted_reason = "no remaining boundary";
      } else if (scenario === "unknown_boundary") asset.boundary_id = "unknown";
      else if (
        ["unknown_target", "empty_targets", "duplicate_targets"].includes(
          scenario,
        )
      )
        boundary.target_unit_ids = {
          unknown_target: ["unknown"],
          empty_targets: [],
          duplicate_targets: ["u1", "u1"],
        }[scenario];
      else if (scenario === "unknown_entrypoint")
        boundary.route.entrypoint_id = "unknown";
      else if (scenario === "mixed_assets")
        implementation.assets.push({ ...asset, boundary_id: "unknown" });
      else if (scenario === "plan_notes") {
        plan.plan_notes = ["planning note"];
        implementation.plan_notes = ["implementation note"];
      } else if (scenario === "focused_target_override") {
        asset.target_unit_ids = ["u2"];
      } else if (scenario === "focused_joint_targets") {
        boundary.target_unit_ids = ["u1", "u2"];
      } else if (
        [
          "focused_plan_mismatch",
          "whole_target_alternative",
          "mixed_target_assets",
        ].includes(scenario)
      ) {
        const other = structuredClone(boundary);
        other.target_unit_ids = ["u2"];
        other.route.entrypoint_id =
          packet.public_target_routes.targets[1].entrypoints[0].entrypoint_id;
        if (scenario === "mixed_target_assets") {
          other.boundary_id = "boundary-002";
          plan.boundary_plan.push(other);
          implementation.assets.push({
            ...asset,
            asset_id: "asset-002",
            boundary_id: "boundary-002",
          });
        } else {
          plan.boundary_plan = [other];
          if (scenario === "whole_target_alternative")
            packet.whole_target_pass = true;
        }
      }
      const sampleDir = path.join(root, "samples/direct-001");
      const run = async (sample) => {
        const model = fixedModel(structuredClone([plan, implementation]));
        const validation = scriptedValidation("stable");
        const currentPacket = structuredClone(packet);
        const runtime = {
          packet: currentPacket,
          env: {},
          manifest: {
            source_roots: ["src"],
            buggy_checkout: { path: roots.buggy },
          },
          options: options({
            modelClient: model,
            validationRunner: validation,
          }),
        };
        let result;
        try {
          result = await sample({
            runtime,
            packet: currentPacket,
            sampleId: "direct-001",
            sampleDir,
            priorAttempts: [],
            promptStyle: "direct",
            harnessRepairBudget: 1,
          });
        } catch (error) {
          result = { error: [error.name, error.message] };
        }
        const outputs = Object.fromEntries(
          fs
            .readdirSync(sampleDir, { recursive: true })
            .filter((file) => fs.statSync(path.join(sampleDir, file)).isFile())
            .map((file) => [file, fs.readFileSync(path.join(sampleDir, file))]),
        );
        fs.rmSync(sampleDir, { recursive: true });
        return {
          result,
          prompts: model.prompts,
          calls: validation.calls,
          outputs,
        };
      };
      const actual = await run(runTargetSample);
      assert.deepEqual(actual, formalEvidence(await run(formalSample)));
      if (
        [
          "forged_metadata",
          "redefined_plan",
          "mixed_assets",
          "plan_notes",
          "focused_target_override",
          "focused_joint_targets",
          "whole_target_alternative",
          "mixed_target_assets",
        ].includes(scenario)
      ) {
        assert.equal(actual.result.bug_revealed, true);
        assert.deepEqual(
          actual.result.assets.map((item) => item.target_unit_ids),
          scenario === "focused_joint_targets"
            ? [["u1", "u2"]]
            : scenario === "whole_target_alternative"
              ? [["u2"]]
              : scenario === "mixed_target_assets"
                ? [["u1"], ["u2"]]
                : [["u1"]],
        );
      } else if (scenario === "exhausted") {
        assert.equal(actual.result.status, "exhausted");
        assert.deepEqual(actual.calls, []);
      } else {
        assert.ok(actual.result.error);
        assert.deepEqual(actual.calls, []);
      }
    },
  );
}

for (const phase of [
  "plan",
  "implementation",
  "repair-decision",
  "repair",
  "minimization",
]) {
  for (const failure of ["model", "raw_payload", "prompt_write", "raw_write"]) {
    test(
      `phase failure artifacts match formal: ${phase} ${failure}`,
      { skip: !formalSample },
      async (t) => {
        const { root, roots, packet, plan, asset } = fixture(t);
        const sampleDir = path.join(root, "samples/direct-001");
        let directory = sampleDir;
        const original = structuredClone(asset);
        const responses = [plan, { assets: [original] }];
        if (phase.startsWith("repair")) {
          original.append_code = original.append_code.replace(
            "{ advance }",
            "{ missing_name }",
          );
          responses.push(
            {
              action: "request_context",
              requests: [
                {
                  kind: "module_context",
                  filepath: "src/arithmetic.ts",
                  reason: "inspect",
                },
              ],
            },
            { assets: [asset] },
          );
          directory = path.join(
            directory,
            "assets/asset-001/harness-repair-001",
          );
        } else if (phase === "minimization") {
          responses.push({ assets: [asset] });
          directory = path.join(directory, "assets/asset-001");
        }
        const failCall = {
          plan: 1,
          implementation: 2,
          "repair-decision": 3,
          repair: 4,
          minimization: 3,
        }[phase];
        // Keep atomic-write diagnostics identical across the two executions.
        let temporaryId = 0;
        t.mock.method(crypto, "randomUUID", () => `fixture-${++temporaryId}`);
        const run = async (sample) => {
          temporaryId = 0;
          if (failure.endsWith("_write"))
            fs.mkdirSync(
              path.join(
                directory,
                `${phase}.${failure === "prompt_write" ? "prompt.md" : "raw.json"}`,
              ),
              { recursive: true },
            );
          const model = fixedModel(structuredClone(responses));
          const complete = model.complete.bind(model);
          let raised = false;
          model.complete = async (prompt) => {
            const response = await complete(prompt);
            if (failure === "model" && model.prompts.length === failCall)
              throw new Error("fixture model timeout");
            return response;
          };
          model.rawPayload = (response) => {
            if (
              failure === "raw_payload" &&
              model.prompts.length === failCall &&
              !raised
            ) {
              raised = true;
              throw new Error("fixture response serialization failure");
            }
            return { provider: "fixture", model: "fixture", response };
          };
          const validation = scriptedValidation(
            phase.startsWith("repair") ? "repair_context" : "stable",
          );
          const currentPacket = structuredClone(packet);
          const runtime = {
            packet: currentPacket,
            env: {},
            manifest: {
              source_roots: ["src"],
              buggy_checkout: { path: roots.buggy },
            },
            options: options({
              modelClient: model,
              validationRunner: validation,
              minimizeBuggyFailuresPerSample: Number(phase === "minimization"),
            }),
          };
          let result;
          try {
            result = await sample({
              runtime,
              packet: currentPacket,
              sampleId: "direct-001",
              sampleDir,
              priorAttempts: [],
              promptStyle: "direct",
              harnessRepairBudget: 1,
            });
          } catch (error) {
            result = { error: [error.name, error.message] };
          }
          const outputs = Object.fromEntries(
            fs
              .readdirSync(sampleDir, { recursive: true })
              .filter((file) =>
                fs.statSync(path.join(sampleDir, file)).isFile(),
              )
              .map((file) => [
                file,
                fs.readFileSync(path.join(sampleDir, file)),
              ]),
          );
          fs.rmSync(sampleDir, { recursive: true });
          return {
            result,
            prompts: model.prompts,
            calls: validation.calls,
            outputs,
          };
        };
        const actual = await run(runTargetSample);
        assert.deepEqual(actual, formalEvidence(await run(formalSample)));
        assert.equal(
          actual.prompts.length,
          failCall - Number(failure === "prompt_write"),
        );
      },
    );
  }
}

test("direct, strict, and soft lanes persist exhaustion checkpoints", async (t) => {
  const { root, packet, caseData } = fixture(t);
  packet.target_units.push({ ...packet.target_units[0], unit_id: "u2" });
  const model = fixedModel(
    Array.from({ length: 3 }, () => ({
      boundary_plan: [],
      exhausted_reason: "no additional family",
    })),
  );
  const runtime = {
    caseData,
    packet,
    manifest: {},
    env: {},
    options: options({
      samples: 1,
      softSamples: 1,
      modelClient: model,
      validationRunner: () => {
        throw Error("unexpected validation");
      },
    }),
  };
  const rows = await runGuidedCaseSamples(
    runtime,
    packet,
    path.join(root, "result"),
  );
  assert.deepEqual(
    rows.map((row) => row.lane),
    ["direct_probe", "hard_core", "soft_extension"],
  );
  assert.ok(rows.every((row) => row.status === "exhausted"));
  for (const row of rows)
    assert.ok(
      fs.existsSync(
        path.join(root, "result/samples", row.sample_id, "result.json"),
      ),
    );
});

test(
  "real Vitest confirms the same isolated candidate",
  { skip: !process.env.PROBE_TEST_NODE_MODULES },
  async (t) => {
    const { root, roots, caseData, plan, asset } = fixture(t);
    const before = Object.fromEntries(
      Object.entries(roots).map(([kind, dir]) => [
        kind,
        fs.readFileSync(path.join(dir, "src/arithmetic.ts"), "utf8"),
      ]),
    );
    const runDir = await runPreparedCase({
      caseData,
      buggyRoot: roots.buggy,
      fixedRoot: roots.fixed,
      config: {
        project: "fixture",
        source_roots: ["src"],
        probe: {
          test_command: [
            "pnpm",
            "exec",
            "vitest",
            "run",
            "--config",
            "vitest.config.ts",
            "<generated-test-file>",
          ],
        },
      },
      options: options({
        modelClient: fixedModel([plan, { assets: [asset] }]),
      }),
      runDir: path.join(root, "result"),
    });
    assert.equal(fs.existsSync(path.join(runDir, "summary.json")), false);
    const row = JSON.parse(
      fs.readFileSync(path.join(runDir, "samples/direct-001/result.json"), "utf8"),
    );
    assert.equal(row.bug_revealed, true, JSON.stringify(row));
    for (const [kind, dir] of Object.entries(roots)) {
      assert.equal(
        fs.readFileSync(path.join(dir, "src/arithmetic.ts"), "utf8"),
        before[kind],
      );
      assert.equal(fs.existsSync(path.join(dir, "test")), false);
    }
    const visit = (dir) =>
      fs.readdirSync(dir, { withFileTypes: true }).forEach((entry) => {
        assert.ok(!entry.name.startsWith("validation-"));
        if (entry.isDirectory()) visit(path.join(dir, entry.name));
      });
    visit(runDir);
  },
);

test("cleanup removes scratch paths without traversing dependency symlinks", (t) => {
  const { root } = fixture(t);
  const kept = path.join(root, "kept");
  const scratch = path.join(root, "scratch");
  fs.mkdirSync(kept);
  fs.mkdirSync(scratch);
  fs.writeFileSync(path.join(kept, "dependency.txt"), "keep");
  fs.symlinkSync(kept, path.join(scratch, "dependency"), "dir");
  assert.deepEqual(removeManagedPaths([scratch, scratch]), [
    { path: scratch, existed: true, removed: true },
    { path: scratch, existed: false, removed: true },
  ]);
  assert.equal(
    fs.readFileSync(path.join(kept, "dependency.txt"), "utf8"),
    "keep",
  );
});

test(
  "prepared execution preserves allowed environment and excludes credentials",
  {
    skip: !process.env.PROBE_TEST_NODE_MODULES,
  },
  (t) => {
    const { root, roots, caseData, packet, asset } = fixture(t);
    const result = preparedValidation({
      runtime: {
        roots,
        caseData,
        packet,
        options: options(),
        env: {
          PATH: process.env.PATH,
          LANG: "C",
          OPENAI_API_KEY: "fixture-secret",
          EXTRA_SETTING: "unused",
        },
      },
      revisionKind: "buggy",
      asset: {
        ...asset,
        append_code:
          'import { it, expect } from "vitest";\nit("environment", () => { expect(process.env.LANG).toBe("C"); expect(process.env.OPENAI_API_KEY).toBeUndefined(); expect(process.env.EXTRA_SETTING).toBeUndefined(); });\n',
      },
      assetDir: path.join(root, "validation"),
    });
    assert.equal(result.summary.status, "passed", JSON.stringify(result));
  },
);

test("output cannot overwrite a checkout", async (t) => {
  const { roots, caseData } = fixture(t);
  await assert.rejects(
    runPreparedCase({
      caseData,
      buggyRoot: roots.buggy,
      fixedRoot: roots.fixed,
      config: { project: "fixture" },
      options: options(),
      runDir: path.join(roots.buggy, "output"),
    }),
    /disjoint/u,
  );
});

test("case deadline preserves completed sample checkpoints", async (t) => {
  const { root, roots, caseData } = fixture(t);
  let calls = 0;
  const modelClient = {
    async complete() {
      if (calls++) throw new CaseTimeBudgetExceeded();
      return {
        choices: [
          {
            message: {
              content: JSON.stringify({
                boundary_plan: [],
                exhausted_reason: "no additional family",
              }),
            },
          },
        ],
      };
    },
  };
  const runDir = await runPreparedCase({
    caseData,
    buggyRoot: roots.buggy,
    fixedRoot: roots.fixed,
    config: { project: "fixture", source_roots: ["src"] },
    options: options({
      directSamples: 2,
      modelClient,
      validationRunner: () => ({ summary: { passed: true, status: "passed" } }),
    }),
    runDir: path.join(root, "result"),
  });
  assert.equal(fs.existsSync(path.join(runDir, "summary.json")), false);
  const manifest = JSON.parse(
    fs.readFileSync(path.join(runDir, "manifest.json"), "utf8"),
  );
  assert.equal("packet_count" in manifest, false);
  for (const [kind, root] of Object.entries(roots)) {
    assert.deepEqual(manifest[`${kind}_checkout`], { path: fs.realpathSync(root) });
  }
  const expectedOptions = options({ directSamples: 2 });
  delete expectedOptions.evaluationMode;
  assert.deepEqual(
    manifest.options,
    JSON.parse(JSON.stringify(expectedOptions)),
  );
  for (const key of ["modelClient", "validationRunner"])
    assert.equal(key in manifest.options, false);
  const progress = JSON.parse(
    fs.readFileSync(path.join(runDir, "progress.json"), "utf8"),
  );
  assert.equal(progress.samples.length, 1);
  assert.equal(progress.error.type, "CaseTimeBudgetExceeded");
  const row = JSON.parse(
    fs.readFileSync(progress.samples[0].result_path, "utf8"),
  );
  assert.equal(row.sample_id, "direct-001");
  assert.equal(row.status, "exhausted");
  assert.deepEqual(Object.keys(progress.samples[0]), ["sample_id", "result_path"]);
});

test("materialization failure cleans the disposable workspace", (t) => {
  const { root, roots, caseData, packet, asset } = fixture(t);
  const assetDir = path.join(root, "output");
  assert.throws(() =>
    preparedValidation({
      runtime: { roots, caseData, packet, options: options(), env: {} },
      revisionKind: "buggy",
      asset: { ...asset, test_file: "../outside.ts" },
      assetDir,
    }),
  );
  assert.ok(
    fs.readdirSync(assetDir).every((name) => !name.startsWith("validation-")),
  );
  assert.equal(
    JSON.parse(
      fs.readFileSync(path.join(assetDir, "buggy.materialized.json"), "utf8"),
    ).cleanup.removed,
    true,
  );
});

test(
  "traceback context resolves a disposable source frame",
  { skip: !process.env.PROBE_TEST_NODE_MODULES },
  (t) => {
    const { root, roots, caseData, packet, asset } = fixture(t);
    fs.writeFileSync(
      path.join(roots.buggy, "src/arithmetic.ts"),
      'export function advance(value: number) {\n  throw new TypeError("fixture failure");\n}\n',
    );
    const result = preparedValidation({
      runtime: {
        roots,
        caseData,
        packet,
        options: options(),
        env: process.env,
      },
      revisionKind: "buggy",
      asset,
      assetDir: path.join(root, "output"),
    });
    const context = repairTracebackContext(
      { buggy_checkout: { path: roots.buggy }, source_roots: ["src"] },
      result.summary,
      "paired_reveal",
    );
    assert.ok(
      context.some((item) => item.filepath === "src/arithmetic.ts"),
      JSON.stringify(result.summary),
    );
    assert.match(JSON.stringify(context), /fixture failure/u);
  },
);
