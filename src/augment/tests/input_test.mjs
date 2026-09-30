import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";

import { loadModelEnv } from "../typescript/run/client.mjs";
import { parseAugmentArgs, runAugmentCli } from "../typescript/run_cli.mjs";
import { runCoverageModelBacked } from "../typescript/run/workflow.mjs";
import { projectFixture } from "./typescript_fixture.mjs";

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "artifact-augment-input-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const { project, input } = projectFixture(root, path.join(root, "dependencies"));
  const envFile = path.join(root, "model.env");
  fs.writeFileSync(envFile, "OPENAI_API_KEY=fixture-not-a-real-key\n");
  return {
    root,
    project,
    options: {
      baseInputFile: input,
      envFile,
      testPackages: [{ name: "root", cwd: "." }],
      measureTestFileCoverage: () => assert.fail("validation must not start"),
      validateGeneratedTest: () => assert.fail("validation must not start"),
      completeModel: () => assert.fail("generation must not start"),
    },
  };
}

test("CLI parses project and input flags once without mutating process arguments", () => {
  const argv = process.argv;
  const values = parseAugmentArgs("augment", [
    "--project=openclaw",
    "--base-input=input.json",
    "--rounds",
    "2",
    "--quiet",
  ]);
  assert.equal(values.project, "openclaw");
  assert.equal(values["base-input"], "input.json");
  assert.equal(values.rounds, "2");
  assert.equal(values.quiet, true);
  assert.equal(process.argv, argv);
  assert.throws(() => parseAugmentArgs("augment", []), /--project is required/u);
  assert.throws(
    () => parseAugmentArgs("augment", ["--project", "openclaw"]),
    /--base-input is required/u,
  );
  assert.throws(
    () =>
      parseAugmentArgs("augment", [
        "--project",
        "openclaw",
        "--base-input",
        "input.json",
        "--language",
        "python",
      ]),
    /Python projects/u,
  );
});

test("CLI help works without a project or model configuration", (t) => {
  const output = [];
  t.mock.method(console, "log", (text) => output.push(text));
  assert.equal(parseAugmentArgs("augment", ["--help"]), null);
  assert.match(output[0], /--repair-context-requests/u);
});

test("CLI owns the TypeScript validation timeout default and override", () => {
  for (const project of ["openclaw", "roo-code", "kimi-code"]) {
    const args = ["--project", project, "--base-input", "input.json"];
    assert.equal(parseAugmentArgs("augment", args)["timeout-seconds"], "600");
    assert.equal(
      parseAugmentArgs("augment", [...args, "--timeout-seconds", "75"])["timeout-seconds"],
      "75",
    );
  }
});

test("CLI rejects a mismatched input project before creating output", async (t) => {
  const { root, options } = fixture(t);
  const out = path.join(root, "out");
  await assert.rejects(
    runAugmentCli({
      values: { project: "different", "base-input": options.baseInputFile },
      defaultOutRoot: out,
    }),
    /base input project does not match/u,
  );
  assert.equal(fs.existsSync(out), false);
});

test("model env-file values override inherited values", (t) => {
  const { options } = fixture(t);
  const env = loadModelEnv(options.envFile);
  assert.equal(env.OPENAI_API_KEY, "fixture-not-a-real-key");
  assert.equal(env.PATH, process.env.PATH);
});

test("nested and symlinked output paths leave the checkout untouched", async (t) => {
  const { root, project, options } = fixture(t);
  const alias = path.join(root, "project-alias");
  fs.symlinkSync(project, alias, "dir");
  for (const outRoot of [
    project,
    path.join(project, "new/output"),
    path.join(alias, "new/output"),
  ]) {
    await assert.rejects(
      runCoverageModelBacked({ ...options, outRoot }),
      /outside projectRoot/u,
    );
    assert.equal(fs.existsSync(path.join(project, "new")), false);
    assert.equal(fs.existsSync(path.join(project, "runs")), false);
  }
});

test("the checkout's parent is a valid external output directory", async (t) => {
  const { root, project, options } = fixture(t);
  const result = await runCoverageModelBacked({
    ...options,
    outRoot: root,
    runId: "parent-output",
    timeBudgetSeconds: 1e-9,
  });
  const progress = JSON.parse(fs.readFileSync(path.join(result.runDir, "progress.json")));
  assert.equal(progress.stop_reason, "time_budget");
  assert.equal(result.rows.length, 0);
  assert.equal(fs.existsSync(path.join(result.runDir, "workspaces")), false);
  assert.deepEqual(fs.readdirSync(path.join(project, "test")), ["seed.test.ts"]);
});
