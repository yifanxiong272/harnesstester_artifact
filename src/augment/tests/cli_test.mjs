import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { once } from "node:events";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

import { projectFixture, scriptedModel, writeJson } from "./typescript_fixture.mjs";

const run = promisify(execFile);
const artifact = fileURLToPath(new URL("../../../", import.meta.url));
const python = process.env.ARTIFACT_TEST_PYTHON;
const nodeModules = process.env.ARTIFACT_TEST_NODE_MODULES;

for (const { language, strategy } of ["python", "typescript"].flatMap(language =>
  ["contract_directed", "contract_agnostic"].map(strategy => ({ language, strategy })),
)) {
  test(`standalone ${language} ${strategy} command shares default acceptance`, {
    skip: language === "python" ? !python : !nodeModules,
  }, async t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "artifact-augment-cli-"));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const copy = path.join(root, "artifact");
    fs.mkdirSync(copy);
    for (const name of ["run.py", "resources/projects.json", "src/cli", "src/common", "src/augment"]) {
      fs.mkdirSync(path.dirname(path.join(copy, name)), { recursive: true });
      fs.cpSync(path.join(artifact, name), path.join(copy, name), {
        recursive: true,
        filter: source => !["__pycache__", "tests"].includes(path.basename(source)),
      });
    }
    let project;
    let input;
    let model;
    const runtimeBin = path.join(root, "runtime_bin");
    fs.mkdirSync(runtimeBin);
    if (language === "typescript") {
      ({ project, input } = projectFixture(root, nodeModules));
      for (const name of ["input.json", "coverage.json"]) {
        const file = path.join(root, name);
        writeJson(file, { ...JSON.parse(fs.readFileSync(file)), project: "openclaw" });
      }
      fs.writeFileSync(path.join(project, "vitest.config.ts"),
        'export default { test: { setupFiles: ["test/runtime_setup.ts"] } };\n');
      fs.writeFileSync(path.join(project, "test/runtime_setup.ts"), [
        'import assert from "node:assert/strict";',
        'import path from "node:path";',
        `assert.equal(process.env.PATH.split(path.delimiter)[0], ${JSON.stringify(runtimeBin)});`,
        'assert.equal(process.env.NODE_OPTIONS || "", "");',
        '',
      ].join("\n"));
      const generate = scriptedModel("partial", []);
      model = payload => generate({ messages: payload.messages.filter(m => m.role !== "system") });
    } else {
      project = path.join(root, "project");
      fs.mkdirSync(path.join(project, "pkg"), { recursive: true });
      fs.mkdirSync(path.join(project, "tests/unittest"), { recursive: true });
      fs.writeFileSync(path.join(project, "pkg/__init__.py"), "");
      fs.writeFileSync(path.join(project, "pkg/mod.py"), "def choose(value):\n    return 'yes' if value else 'no'\n");
      writeJson(path.join(root, "regions.json"), {
        sources: [{ location: { filepath: "pkg/mod.py", start_line: 2 } }],
      });
      writeJson(path.join(root, "coverage.json"), {
        files: { "pkg/mod.py": { executed_lines: [1], missing_lines: [2] } },
      });
      input = path.join(root, "input.json");
      writeJson(input, {
        project: "pr-agent", project_root: "project",
        ldh: { regions_json: "regions.json" }, general_cov: { coverage_json: "coverage.json" },
        runtime: { python, coverage_source: "pkg" },
      });
      model = async ({ messages }) => {
        const suffix = messages.find(m => m.role === "user").content.match(/"test_name_suffix": "([^"]+)"/u)[1];
        return { choices: [{ message: { content: JSON.stringify({
          action: "propose_test", test_file: `tests/unittest/test_generated${suffix}.py`,
          append_code: `from pkg.mod import choose\n\ndef test_paths${suffix}():\n    assert choose(True) == 'yes'\n    assert choose(False) == 'no'\n\ndef test_bad${suffix}():\n    assert False\n`,
          expected_nodeids: [], targeted_objective_ids: [], targeted_lines: [],
          oracle: "return value", mocking_strategy: "none",
        }) } }] };
      };
    }
    let calls = 0;
    const server = http.createServer(async (request, response) => {
      const chunks = [];
      for await (const chunk of request) chunks.push(chunk);
      calls += 1;
      try { response.end(JSON.stringify(await model(JSON.parse(Buffer.concat(chunks))))); }
      catch (error) { response.writeHead(500); response.end(String(error)); }
    });
    server.listen(0, "127.0.0.1");
    await once(server, "listening");
    t.after(() => { server.closeAllConnections(); server.close(); });
    const env = {
      PATH: `${runtimeBin}${path.delimiter}${process.env.PATH}`, HOME: process.env.HOME,
      OPENAI_API_KEY: "fixture-not-a-real-key",
      OPENAI_BASE_URL: `http://127.0.0.1:${server.address().port}/v1`,
    };
    if (nodeModules) env.OPENCLAW_VITEST_LAUNCHER = `${process.execPath} ${path.join(nodeModules, "vitest/vitest.mjs")}`;
    const output = path.join(root, "output");
    const args = [
      path.join(copy, "run.py"),
      "augment", "--project", language === "python" ? "pr-agent" : "openclaw",
      "--base-input", input, "--out-root", output, "--run-id", "cli", "--rounds", "1",
    ];
    if (strategy !== "contract_directed") args.push("--strategy", strategy);
    if (language === "python") args.push("--python-bin", python);
    await run(python || "python3", args, { cwd: root, env, timeout: 60000 });
    const runDir = path.join(output, "runs/cli");
    const rows = JSON.parse(fs.readFileSync(path.join(runDir, "results.json")));
    assert.equal(rows[0].status, "accepted", JSON.stringify(rows));
    const progress = JSON.parse(fs.readFileSync(path.join(runDir, "progress.json")));
    assert.equal(progress.strategy, strategy);
    assert.equal(progress.acceptance_policy, "passing_subset");
    if (language === "python") {
      assert.equal(rows[0].accepted_nodeids.length, 1);
      assert.equal(rows[0].rejected_nodeids.length, 1);
    } else {
      assert.ok(rows[0].accepted_units.length > 0);
      assert.ok(rows[0].rejected_units.length > 0);
      for (const unit of rows[0].accepted_units) {
        assert.match(unit.test_name, /^paths/u);
      }
    }
    assert.ok(calls > 0);
    assert.ok(fs.existsSync(path.join(runDir, "accepted/files")));
    assert.equal(fs.existsSync(path.join(runDir, "workspaces")), false);
    assert.equal(fs.existsSync(path.join(copy, "src/probe")), false);
    assert.equal(fs.existsSync(path.join(copy, "src/llm_dependent")), false);
  });
}
