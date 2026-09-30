import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { buildTargetPacket } from "../typescript/input/target_packets.mjs";
import { runPreparedCase } from "../typescript/run/case.mjs";
import { CaseTimeBudgetExceeded } from "../typescript/run/deadline.mjs";
import { confirmedCandidateCount } from "../typescript/run/progress.mjs";

const dependencies = process.env.PROBE_TEST_NODE_MODULES;
const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8"));
const readOptional = (file) => fs.existsSync(file) ? readJson(file) : null;
const confirmationRuns = 2;

function fixture(t, mode, strategy) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-checkpoint-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const discovery = mode === "single_revision_discovery";
  const roots = {};
  for (const kind of discovery ? ["latest"] : ["buggy", "fixed"]) {
    const checkout = path.join(root, kind);
    fs.mkdirSync(path.join(checkout, "src"), { recursive: true });
    fs.writeFileSync(path.join(checkout, "src/arithmetic.ts"),
      "/** Advance by two. */\nexport function advance(value: number) {\n" +
      `  return value + ${kind === "fixed" ? 2 : 1};\n}\n`);
    fs.writeFileSync(path.join(checkout, "package.json"), '{"type":"module"}\n');
    fs.symlinkSync(path.resolve(dependencies), path.join(checkout, "node_modules"), "dir");
    roots[kind] = checkout;
  }
  const targetUnits = [{
    unit_id: "u1", filepath: "src/arithmetic.ts", qualname: "advance",
    kind: "function", start_line: 2, end_line: 4,
  }];
  const packet = buildTargetPacket({
    project: "fixture", strategy, projectRoot: Object.values(roots)[0], targetUnits,
  });
  const plan = {
    boundary_plan: [{
      boundary_id: "boundary-001", target_unit_ids: ["u1"],
      route: { entrypoint_id: packet.public_target_routes.targets[0].entrypoints[0].entrypoint_id },
      probe: { test_intent: "advance by two", activation_conditions: ["call advance"] },
      invariant: {
        independent_oracle: "zero advances to two", supporting_evidence: "public docstring",
        expected_observation: "two", oracle_mode: "assertion",
      },
      oracle_family: "arithmetic increment", novelty_from_prior: "first attempt",
      bug_hypothesis: "incorrect increment",
    }],
    context_requests: [],
  };
  const asset = {
    asset_id: "asset-001", boundary_id: "boundary-001",
    input_construction: "call with zero", observable_oracle: "public return is two",
    primary_oracle: "public result equality", mocking_plan: "none",
    test_file: "test/generated/benchmarkbr/test_advance.test.ts",
    append_code: 'import { expect, it } from "vitest";\n' +
      'import { advance } from "../../../src/arithmetic";\n' +
      'it("advances by two", () => {\n  const unused = 7;\n  expect(advance(0)).toBe(2);\n});\n',
  };
  return {
    root, roots, plan, asset,
    minimized: {
      ...asset, asset_id: "asset-minimized",
      append_code: asset.append_code.replace("  const unused = 7;\n", ""),
    },
    sibling: {
      ...asset, asset_id: "asset-002", input_construction: "call with one",
      test_file: "test/generated/benchmarkbr/test_advance_one.test.ts",
      append_code: asset.append_code.replace("advance(0)).toBe(2)", "advance(1)).toBe(3)"),
    },
    caseData: {
      case_id: "checkpoint", revisions: Object.fromEntries(Object.keys(roots).map((kind) => [kind, kind])),
      ...(discovery ? { target_units: targetUnits } : { patch_targets: { target_units: targetUnits } }),
    },
  };
}

function assertConfirmed(row, mode, strategy, assetId) {
  const discovery = mode === "single_revision_discovery";
  const status = discovery ? "stable_failure_candidate" : "revealed";
  assert.equal(row.sample_id, "direct-001");
  assert.equal(row.strategy, strategy);
  assert.equal(row.lane, "direct_probe");
  assert.equal(row.evaluation_mode, mode);
  assert.deepEqual(row.target_unit_ids, ["u1"]);
  assert.equal(row.status, status);
  assert.equal(row.bug_revealed, !discovery);
  assert.equal(confirmedCandidateCount([row], mode), 1);
  assert.equal(row.assets.length, 1);
  const asset = row.assets[0];
  assert.equal(asset.asset_id, assetId);
  assert.equal(asset.status, status);
  assert.equal(asset[discovery ? "stable_failure_candidate" : "bug_revealed"], true);
  const confirmation = discovery ? asset.confirmation :
    asset.fixed_variants.find((variant) => variant.asset_id === assetId).confirmation;
  assert.equal(confirmation.stable, true);
  assert.equal(confirmation.required_runs, confirmationRuns);
  assert.equal(confirmation.runs.length, confirmationRuns);
  assert.ok(confirmation.runs.every((run) => run.passed));
  const proposal = readJson(asset.proposal_path);
  assert.equal(proposal.asset_id, assetId);
  assert.match(asset.test_asset_sha256, /^[a-f0-9]{64}$/u);
  assert.equal(asset.test_asset_sha256, proposal.test_asset_sha256);
  assert.ok(confirmation.runs.every((run) => run.test_asset_sha256 === asset.test_asset_sha256));
  assert.equal("append_code" in asset, false);
  if (discovery) {
    assert.equal(row.stable_failure_candidate, true);
    for (const key of ["buggy", "fixed", "fixed_variants", "bug_revealed"])
      assert.equal(key in asset, false);
  } else {
    assert.equal("latest" in asset, false);
    assert.equal(asset.buggy.status, "assertion_failed");
    assert.equal(asset.fixed.status, "passed");
  }
}

const scenarios = [
  "minimization_model", "minimization_validation",
  "minimized_confirmation_first", "minimized_confirmation_last",
  "initial_confirmation_first", "initial_confirmation_last",
  "sibling_validation", "sibling_confirmation", "later_sample", "normal_minimization",
];

for (const mode of ["paired_reveal", "single_revision_discovery"]) {
  for (const strategy of ["target_probe_ldh", "target_probe_contract_agnostic"]) {
    for (const scenario of scenarios) {
      test(`budget checkpoint: ${mode} ${strategy} ${scenario}`, { skip: !dependencies }, async (t) => {
        const f = fixture(t, mode, strategy);
        const discovery = mode === "single_revision_discovery";
        const runDir = path.join(f.root, "run");
        const resultPath = path.join(runDir, "samples/direct-001/result.json");
        const sibling = scenario.startsWith("sibling_");
        const initial = scenario.startsWith("initial_confirmation_");
        const optional = scenario.startsWith("minim") || scenario === "normal_minimization";
        const normal = scenario === "normal_minimization";
        const deadline = new CaseTimeBudgetExceeded();
        let expired = 0;
        let checkpointBeforeMinimization = null;
        let checkpointAtDeadline = null;
        const modelCalls = [];
        const validations = [];
        const expire = () => {
          expired += 1;
          checkpointAtDeadline = readOptional(resultPath);
          throw deadline;
        };
        const responses = [f.plan, { assets: sibling ? [f.asset, f.sibling] : [f.asset] }];
        const modelClient = {
          async complete() {
            const call = modelCalls.length;
            modelCalls.push(call);
            if (call < 2) return reply(responses[call]);
            if (call === 2 && scenario === "later_sample") expire();
            if (call === 2 && optional) {
              checkpointBeforeMinimization = readOptional(resultPath);
              if (scenario === "minimization_model") expire();
              return reply({ assets: [f.minimized] });
            }
            throw new Error("unexpected scripted model call");
          },
        };
        const validationRunner = ({ revisionKind, asset, assetDir }) => {
          const stage = path.basename(assetDir);
          const preflight = asset.asset_id.startsWith("preflight-");
          const call = { revisionKind, assetId: asset.asset_id, stage, completed: false };
          if (!preflight) validations.push(call);
          // Throw from real validation seams, never from a timer or a replacement workflow.
          const lastConfirmation = stage.endsWith("-002") && revisionKind === (discovery ? "latest" : "fixed");
          if ((scenario === "minimization_validation" && stage === "minimized") ||
              (scenario === "minimized_confirmation_first" && stage === "minimized-confirmation-001") ||
              (scenario === "minimized_confirmation_last" && stage.startsWith("minimized-confirmation-") && lastConfirmation) ||
              (scenario === "initial_confirmation_first" && stage === "base-confirmation-001") ||
              (scenario === "initial_confirmation_last" && stage.startsWith("base-confirmation-") && lastConfirmation) ||
              (scenario === "sibling_validation" && asset.asset_id === "asset-002") ||
              (scenario === "sibling_confirmation" && asset.asset_id === "asset-002" && stage === "base-confirmation-002")) expire();
          const passed = preflight || revisionKind === "fixed" ||
            (scenario === "sibling_confirmation" && asset.asset_id === "asset-001");
          const summary = {
            passed, status: passed ? "passed" : "assertion_failed", phase: "vitest",
            exit_code: passed ? 0 : 1, timed_out: false,
            failed_nodeids: passed ? [] : [`${asset.test_file} > advances by two`],
            failure_excerpt: passed ? "" : "AssertionError: 1 != 2",
          };
          call.completed = true;
          return { summary, result: { evidence: summary }, materialized: {} };
        };
        const returned = await runPreparedCase({
          caseData: f.caseData,
          ...(discovery ? { latestRoot: f.roots.latest } : { buggyRoot: f.roots.buggy, fixedRoot: f.roots.fixed }),
          config: { project: "fixture", source_roots: ["src"] },
          options: {
            model: "fixture", provider: "openai", strategy,
            directSamples: scenario === "later_sample" ? 2 : 1, samples: 0, softSamples: 0,
            maxRevealCandidates: 10, assetsPerSample: 2, revealConfirmationRuns: confirmationRuns,
            minimizeBuggyFailuresPerSample: optional ? 1 : 0,
            caseTimeBudgetSeconds: 0, modelClient, validationRunner,
          },
          runDir,
        });
        assert.equal(returned, fs.realpathSync(runDir));
        assert.equal(readJson(path.join(runDir, "preflight.json")).passed, true);
        assert.equal(expired, normal ? 0 : 1, "the requested budget boundary must actually be reached");
        assert.equal(modelCalls.length, optional || scenario === "later_sample" ? 3 : 2);
        const progress = readJson(path.join(runDir, "progress.json"));
        if (normal) assert.equal("error" in progress, false);
        else assert.deepEqual(progress.error, { type: deadline.name, message: deadline.message });
        // Recovery must retain the existing result.json/progress schema, not invent a sidecar.
        assert.deepEqual(Object.keys(progress).sort(), normal ? ["samples"] : ["error", "samples"]);
        assert.equal(fs.existsSync(path.join(runDir, "summary.json")), false);
        if (initial) {
          assert.deepEqual(progress.samples, []);
          assert.equal(checkpointAtDeadline, null);
          assert.equal(fs.existsSync(resultPath), false);
          assert.equal(confirmedCandidateCount([], mode), 0);
          const completed = validations.filter((call) => call.completed && call.stage.startsWith("base-confirmation-"));
          assert.equal(completed.length, scenario.endsWith("first") ? 0 : (discovery ? 1 : 3));
          return;
        }
        assert.deepEqual(progress.samples, [{
          sample_id: "direct-001", result_path: path.join(returned, "samples/direct-001/result.json"),
        }]);
        const row = readJson(progress.samples[0].result_path);
        assert.equal(row.assets.length, 1, "an interrupted sibling must not enter the saved row");
        if (!normal) assert.deepEqual(row, checkpointAtDeadline);
        if (scenario === "sibling_confirmation") {
          assert.equal(row.assets[0].asset_id, "asset-001");
          assert.equal(row.status, discovery ? "latest_passed" : "buggy_passed");
          assert.equal(row.bug_revealed, false);
          assert.equal(confirmedCandidateCount([row], mode), 0);
        } else assertConfirmed(row, mode, strategy, normal ? "asset-minimized" : "asset-001");
        if (optional) {
          assert.ok(checkpointBeforeMinimization, "confirmed evidence must be on disk before optional work");
          assertConfirmed(checkpointBeforeMinimization, mode, strategy, "asset-001");
          assert.equal("minimization" in checkpointBeforeMinimization.assets[0], false);
          if (normal) {
            assert.deepEqual(Object.keys(row).sort(), Object.keys(checkpointBeforeMinimization).sort());
            assert.equal(row.assets[0].original_asset_id, "asset-001");
            assert.equal(row.assets[0].minimization.called, true);
            assert.equal(row.assets[0].minimization.use_minimized, true);
            assert.notEqual(row.assets[0].test_asset_sha256, checkpointBeforeMinimization.assets[0].test_asset_sha256);
            assert.equal(path.basename(path.dirname(row.assets[0].proposal_path)), "minimized");
          } else assert.deepEqual(row, checkpointBeforeMinimization);
        }
        if (sibling) assert.ok(validations.some((call) => call.assetId === "asset-002" && !call.completed));
        if (scenario === "later_sample") {
          assert.equal(fs.existsSync(path.join(runDir, "samples/direct-002/plan.prompt.md")), true);
          assert.equal(fs.existsSync(path.join(runDir, "samples/direct-002/result.json")), false);
        }
      });
    }
  }
}

function reply(content) {
  return { choices: [{ message: { content: JSON.stringify(content) } }] };
}
