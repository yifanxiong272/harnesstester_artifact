import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { analyzeFactProject } from "../typescript/flow/analysis_fact.mjs";
import { typescriptBoundaries } from "../typescript/source_rules.mjs";
import { loadInputs } from "../../augment/typescript/input/snapshot.mjs";
import { buildCoverageTargetManifest } from "../../augment/typescript/input/coverage_targets.mjs";
import { rankCoverageFiles } from "../../augment/typescript/general_coverage.mjs";

const artifact = fileURLToPath(new URL("../../../", import.meta.url));
const typescriptRoot = process.env.TYPESCRIPT_ROOT;
const source = `import { generateText } from "ai";
function consume(value: any) { return value.text; }
function unrelated() { return "constant"; }
export async function run(input: string) {
  const response = await generateText({ prompt: input });
  if (response.text) {
    unrelated();
    return consume(response);
  }
  return "";
}
`;

function temporary(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "ldh-artifact-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return root;
}

function writeJson(file, value) {
  fs.writeFileSync(file, JSON.stringify(value));
}

for (const mode of [
  "block_only",
  "control-dependence-direct",
  "control-dependence-recursive",
]) {
  test(`flow and control output: ${mode}`, { skip: !typescriptRoot }, (t) => {
    const root = temporary(t);
    fs.writeFileSync(path.join(root, "subject.ts"), source);
    const ts = createRequire(path.join(typescriptRoot, "package.json"))(
      "typescript",
    );
    const payload = analyzeFactProject({
      ts,
      root,
      files: ["subject.ts"],
      project: "fixture",
      sourceRules: typescriptBoundaries(),
      options: { maxIterations: 120, controlDependenceMode: mode },
    });
    assert.equal(payload.fixed_point.converged, true);
    assert.deepEqual(
      payload.sources.map((item) => item.location.start_line),
      [5],
    );
    assert.ok(
      payload.data_dependence.some((item) => item.location.start_line === 2),
    );
    assert.equal(
      payload.control_dependence.some(
        (item) => item.location.function === "unrelated",
      ),
      mode !== "block_only",
    );
  });
}

test("control modes preserve block flow and only extend function regions", { skip: !typescriptRoot }, (t) => {
  const root = temporary(t);
  fs.writeFileSync(path.join(root, "subject.ts"), `import { generateText } from "ai";
function leaf() { return "constant"; }
function direct() { return leaf(); }
export async function run() {
  const response = await generateText({ prompt: "test" });
  if (response.text) {
    const count = 1;
    direct();
  }
  return response;
}
`);
  const ts = createRequire(path.join(typescriptRoot, "package.json"))("typescript");
  let baseline;
  for (const [mode, functions] of [
    ["block_only", []],
    ["control-dependence-direct", ["direct"]],
    ["control-dependence-recursive", ["direct", "leaf"]],
  ]) {
    const payload = analyzeFactProject({
      ts, root, files: ["subject.ts"], project: "fixture",
      sourceRules: typescriptBoundaries(),
      options: { maxIterations: 120, controlDependenceMode: mode },
    });
    assert.equal(payload.fixed_point.converged, true);
    baseline ??= payload;
    assert.deepEqual(payload.sources, baseline.sources);
    assert.deepEqual(payload.data_dependence, baseline.data_dependence);
    assert.deepEqual(payload.control_dependence.map(item => item.location.function).sort(), functions);
    for (const line of [7, 8]) {
      const region = payload.data_dependence.find(item => item.location.start_line === line);
      assert.ok(region?.flows.some(flow => flow.dependence_type === "control"), `${mode}: line ${line}`);
    }
    assert.ok(!payload.data_dependence.some(item => [2, 3].includes(item.location.start_line)));
  }
});

for (const project of ["openclaw", "roo-code", "kimi-code"]) {
  test(
    `copied public CLI output feeds augment: ${project}`,
    { skip: !typescriptRoot },
    (t) => {
      const root = temporary(t);
      const copied = path.join(root, "artifact");
      for (const directory of ["llm_dependent", "common", "cli"]) {
        fs.cpSync(
          path.join(artifact, "src", directory),
          path.join(copied, "src", directory),
          {
            recursive: true,
            filter: (file) =>
              !["tests", "node_modules", "__pycache__"].includes(
                path.basename(file),
              ),
          },
        );
      }
      for (const file of [
        "run.py",
        "resources/projects.json",
      ]) {
        fs.mkdirSync(path.dirname(path.join(copied, file)), { recursive: true });
        fs.copyFileSync(path.join(artifact, file), path.join(copied, file));
      }
      const checkout = path.join(root, "checkout");
      fs.mkdirSync(checkout);
      writeJson(path.join(checkout, "package.json"), { type: "module" });
      fs.symlinkSync(
        path.join(typescriptRoot, "node_modules"),
        path.join(checkout, "node_modules"),
        "dir",
      );
      fs.writeFileSync(path.join(checkout, "subject.ts"), source);
      fs.writeFileSync(path.join(checkout, "seed.test.ts"), "export {};\n");
      writeJson(path.join(root, "sources.json"), { files: ["subject.ts"] });
      const env = { ...process.env };
      delete env.PYTHONPATH;
      const result = spawnSync(
        process.env.ARTIFACT_TEST_PYTHON || "python3",
        [
          path.join(copied, "run.py"),
          "llm-dependent",
          "--project",
          project,
          "--project-root",
          checkout,
          "--source-base",
          "sources.json",
          "--typescript-root",
          checkout,
          "--out",
          "regions.json",
        ],
        {
          cwd: root,
          env,
          encoding: "utf8",
          timeout: 30000,
        },
      );
      assert.equal(result.status, 0, result.stdout + result.stderr);
      assert.ok(fs.existsSync(path.join(root, "regions.compact.json")));
      assert.ok(!fs.existsSync(path.join(root, "regions.augment.json")));
      const payload = JSON.parse(
        fs.readFileSync(path.join(root, "regions.json")),
      );
      assert.equal(payload.fixed_point.max_iterations, 120);
      assert.ok(payload.sources.length);
      writeJson(path.join(root, "facts.json"), {
        project,
        files: {
          "subject.ts": {
            lines: { total: [[1, 7]], covered: [] },
            branches: [{ line: 6, total: 2, covered: 1 }],
          },
        },
        test_coverage: {
          "subject.ts": { "seed.test.ts": { lines: [[1, 1]], branch_lines: [] } },
        },
      });
      const base = path.join(root, "base.json");
      writeJson(base, {
        project,
        project_root: "checkout",
        ldh: { regions_json: "regions.json" },
        general_cov: { coverage_json: "facts.json" },
      });
      const inputs = loadInputs(base);
      assert.deepEqual([...inputs.ldhFiles], ["subject.ts"]);
      const manifest = buildCoverageTargetManifest({
        projectRoot: checkout,
        generalTestScores: inputs.generalTestScores,
        fileRanking: rankCoverageFiles(
          inputs.generalCoverage,
          inputs.ldhFiles,
        ),
        testPackages: [{ cwd: "." }],
      });
      assert.deepEqual(
        manifest.targets.map((item) => item.filepath),
        ["subject.ts"],
      );
      assert.equal(manifest.targets[0].seed_test.test_file, "seed.test.ts");
      const facts = JSON.parse(fs.readFileSync(path.join(root, "facts.json")));
      const measuredFile = facts.files["subject.ts"];
      measuredFile.lines.covered = measuredFile.lines.total;
      measuredFile.branches[0].covered = measuredFile.branches[0].total;
      writeJson(path.join(root, "facts.json"), facts);
      assert.equal(loadInputs(base).ldhFiles.size, 0);
    },
  );
}
