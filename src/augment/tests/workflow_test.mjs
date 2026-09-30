import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";

import { createPackageVitestAdapter } from "../typescript/package_vitest_adapter.mjs";
import { runCoverageModelBacked } from "../typescript/run/workflow.mjs";
import { projectFixture, scriptedModel } from "./typescript_fixture.mjs";

const nodeModules = process.env.ARTIFACT_TEST_NODE_MODULES;
const packages = [{ name: "root", cwd: ".", coverageProvider: "istanbul" }];

for (const scenario of [
  "direct", "initial_context", "repair", "repair_context", "partial",
  "continuation", "transport_retry", "budget",
]) {
  test(`real Vitest workflow: ${scenario}`, { skip: !nodeModules }, async (t) => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "artifact-augment-ts-"));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const { project, input } = projectFixture(root, nodeModules);
    const adapter = createPackageVitestAdapter({
      packages, launcher: [process.execPath, path.join(nodeModules, "vitest/vitest.mjs")],
    });
    const conversations = [];
    const envFile = path.join(root, "model.env");
    fs.writeFileSync(envFile, "OPENAI_API_KEY=fixture-not-a-real-key\n");
    // Copied source must stay outside coverage-excluded build directory names.
    const options = {
      baseInputFile: input, outRoot: path.join(root, "results"), runId: "smoke", envFile,
      testPackages: packages, ...adapter, rounds: 2, timeoutSeconds: 15,
      repairContextRequests: 1,
      timeBudgetSeconds: scenario === "budget" ? 0.000001 : 0,
      completeModel: scriptedModel(scenario, conversations),
    };
    const { runDir, rows } = await runCoverageModelBacked(options);
    const progress = JSON.parse(fs.readFileSync(path.join(runDir, "progress.json")));
    assert.equal(fs.existsSync(path.join(runDir, "summary.json")), false);
    for (const key of ["accepted_count", "status_counts", "completed_rounds"]) {
      assert.equal(key in progress, false);
    }
    assert.equal(fs.existsSync(path.join(runDir, "workspaces")), false);
    assert.deepEqual(fs.readdirSync(path.join(project, "test")), ["seed.test.ts"]);
    if (scenario === "budget") {
      assert.equal(progress.stop_reason, "time_budget");
      assert.equal(conversations.length, 0);
    } else {
      assert.equal(rows.at(-1).status, "accepted", JSON.stringify(rows));
      for (const row of rows.filter(row => row.status === "accepted")) {
        for (const unit of row.accepted_units) {
          assert.equal(fs.existsSync(unit.accepted_file_snapshot), true);
        }
      }
      if (scenario === "continuation") {
        assert.ok(rows[0].passes.length >= 2);
        assert.ok(rows[0].passes.length <= 3);
      }
      if (scenario === "repair" || scenario === "repair_context") {
        const repairDir = path.join(runDir, "records/iteration-001/sample/repair");
        assert.equal(fs.existsSync(path.join(repairDir, "feedback.md")), true);
        assert.equal(fs.existsSync(path.join(repairDir, "proposal.json")), true);
        assert.equal(fs.existsSync(path.join(repairDir, "decision.json")), true);
        assert.ok(fs.readdirSync(repairDir).some(file => /^response-\d+\.raw\.json$/u.test(file)));
        assert.equal(fs.existsSync(`${repairDir}-001`), false);
      }
      if (scenario === "transport_retry") {
        assert.equal(rows[0].status, "model_failed");
        assert.equal(rows[0].objective_id, rows[1].objective_id);
      }
      if (scenario.includes("context")) {
        assert.ok(conversations.slice(1).some(messages => JSON.stringify(messages).includes("export const expected")));
      }
    }
    assert.equal(progress.checkpoints.at(-1).round, rows.length);
    await assert.rejects(runCoverageModelBacked(options), { code: "EEXIST" });
  });
}
