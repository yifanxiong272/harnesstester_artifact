import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { gunzipSync } from "node:zlib";
import test from "node:test";

import { prepareInputs } from "../../augment/typescript/input/prepare.mjs";
import { createPackageVitestAdapter } from "../../augment/typescript/package_vitest_adapter.mjs";
import { CoverageFacts } from "../typescript_facts.mjs";

const collector = fileURLToPath(new URL("../typescript.mjs", import.meta.url));
const modules = process.env.ARTIFACT_TEST_NODE_MODULES;
const write = (file, data) => fs.writeFileSync(file, JSON.stringify(data));

function compareFormal(coverage, project, output) {
  const formal = process.env.AUGMENT_FORMAL_ROOT;
  if (!formal) return;
  const script = `
import gzip, json, runpy, sys, tempfile
from pathlib import Path
formal, project, output = map(Path, sys.argv[1:])
api = runpy.run_path(str(formal / "src/common/ts_coverage/file_level_coverage.py"))
sources = list(json.loads((output / "coverage.json").read_text())["files"])
with tempfile.TemporaryDirectory() as tmp:
    denominator, tests, statuses = [], [], []
    for i, row in enumerate(json.loads((output / "runs.json").read_text())):
        report = Path(tmp) / f"{i}.json"
        report.write_bytes(gzip.decompress((output / row["coverage_json"]).read_bytes()))
        (denominator if row.get("denominator") else tests).append(report)
        if row.get("test_file"):
            statuses.append({"test_file": row["test_file"], "coverage_json": str(report)})
    den = api["facts_from_maps"](denominator, sources, project)
    cov = api["facts_from_maps"](tests, sources, project)
    facts = api["attach_denominator"](cov, den, sources)
    reverse = api["build_reverse_index"](statuses, sources, project)
    print(json.dumps({"facts": facts, "reverse": reverse}))
`;
  const reference = JSON.parse(execFileSync(process.env.ARTIFACT_TEST_PYTHON ?? "python3",
    ["-c", script, formal, project, output], { encoding: "utf8" }));
  assert.deepEqual(coverage.files, Object.fromEntries(reference.facts.locations.map(({ file, ...row }) => [file, row])));
  for (const [file, tests] of Object.entries(coverage.test_coverage)) {
    for (const [name, row] of Object.entries(tests)) {
      for (const [field, index] of [["lines", "lines"], ["branch_lines", "branches"]]) {
        const actual = row[field].flatMap(([a, b]) => Array.from({ length: b - a + 1 }, (_, i) => a + i));
        const expected = Object.entries(reference.reverse[index][file] ?? {})
          .filter(([, names]) => names.includes(name)).map(([line]) => Number(line)).sort((a, b) => a - b);
        assert.deepEqual(actual, expected);
      }
    }
  }
}

function fixture(t, provider) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "collect_coverage_"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const project = path.join(root, "project");
  fs.mkdirSync(path.join(project, "src"), { recursive: true });
  fs.mkdirSync(path.join(project, "test"));
  fs.symlinkSync(modules, path.join(project, "node_modules"), "dir");
  write(path.join(project, "package.json"), { type: "module" });
  fs.writeFileSync(path.join(project, "src/agent.ts"), 'export function choose(x: boolean) {\n if(x) return "yes";\n return "no";\n}\n');
  fs.writeFileSync(path.join(project, "src/unreached.ts"), 'export function untouched() { return 42; }\n');
  for (const [name, expected] of [["good", "yes"], ["bad", "wrong"]]) {
    fs.writeFileSync(path.join(project, `test/${name}.test.ts`),
      `import {it,expect} from "vitest"; import {choose} from "../src/agent.js"; it("${name}",()=>expect(choose(true)).toBe("${expected}"));\n`);
  }
  write(path.join(root, "source_files.json"), { files: ["src/agent.ts", "src/unreached.ts"] });
  const config = path.join(root, "collection.json");
  write(config, { project: "example-native-name", project_root: "project", source_files: "source_files.json",
    command: [process.execPath, path.join(modules, "vitest/vitest.mjs")],
    packages: [{ cwd: ".", provider, include: ["src/**/*.ts"], tests: ["test/good.test.ts", "test/bad.test.ts"] }],
  });
  return { root, project, config, output: path.join(root, "output") };
}

for (const kind of ["nested", "checkout_alias", "parent_alias", "existing_alias", "checkout_root",
  "outside_nested", "outside_alias", "linked_outside", "sibling_prefix"]) {
  test(`${kind}: output containment is resolved before creating directories`, t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "collector_boundary_"));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const project = path.join(root, "project");
    const outside = path.join(root, "outside");
    fs.mkdirSync(project);
    fs.mkdirSync(outside);
    const source = path.join(project, "source.ts");
    fs.writeFileSync(source, "export const value = 1;\n");
    fs.writeFileSync(path.join(project, "source.test.ts"), "");
    fs.symlinkSync(project, path.join(root, "checkout_alias"), "dir");
    fs.symlinkSync(project, path.join(outside, "parent_alias"), "dir");
    fs.symlinkSync(outside, path.join(root, "outside_alias"), "dir");
    fs.symlinkSync(outside, path.join(project, "linked_outside"), "dir");
    const outputs = {
      nested: path.join(project, "new_parent/deeper/report"),
      checkout_alias: path.join(root, "checkout_alias/new_parent/deeper/report"),
      parent_alias: path.join(outside, "parent_alias/new_parent/report"),
      existing_alias: path.join(outside, "parent_alias"),
      checkout_root: project,
      outside_nested: path.join(outside, "new_parent/deeper/report"),
      outside_alias: path.join(root, "outside_alias/new_parent/report"),
      linked_outside: path.join(project, "linked_outside/new_parent/report"),
      sibling_prefix: path.join(root, "project-results/new_parent/report"),
    };
    const allowed = ["outside_nested", "outside_alias", "linked_outside", "sibling_prefix"].includes(kind);
    write(path.join(root, "source_files.json"), { files: ["source.ts"] });
    const fake = path.join(root, "vitest.mjs");
    fs.writeFileSync(fake, `
import fs from "node:fs";
import path from "node:path";
const dir = process.argv[process.argv.indexOf("--coverage.reportsDirectory") + 1];
const file = ${JSON.stringify(fs.realpathSync(source))};
fs.writeFileSync(path.join(dir, "coverage-final.json"), JSON.stringify({
  [file]: { path: file, statementMap: {}, s: {}, branchMap: {}, b: {} },
}));
`);
    const config = path.join(root, "collection.json");
    write(config, {
      project: "fixture", project_root: "checkout_alias", source_files: "source_files.json",
      command: [process.execPath, fake], packages: [{ tests: ["source.test.ts"] }],
    });
    const before = fs.readdirSync(root, { recursive: true }).sort();
    const output = outputs[kind];
    const result = spawnSync(process.execPath, [collector, "--config", config, "--out-dir", output],
      { encoding: "utf8", timeout: 15000 });
    assert.ifError(result.error);
    if (allowed) {
      assert.equal(result.status, 0, result.stderr);
      assert.ok(fs.existsSync(path.join(output, "coverage.json")));
      const records = JSON.parse(fs.readFileSync(path.join(output, "runs.json")));
      assert.equal(records.length, 2);
      assert.ok(records.every(row => row.status === "passed" && row.coverage_available));
    } else {
      assert.equal(result.status, 1, result.stderr);
      assert.match(result.stderr, /out-dir must be outside the checkout/u);
      assert.deepEqual(fs.readdirSync(root, { recursive: true }).sort(), before);
    }
  });
}

for (const provider of [undefined, "istanbul", "v8"]) {
  test(`${provider ?? "default v8"}: collection and Augment preserve provider selection`, { skip: !modules }, t => {
    const { config, project, output } = fixture(t, provider);
    execFileSync(process.execPath, [collector, "--config", config, "--out-dir", output], { timeout: 60000 });
    const records = JSON.parse(fs.readFileSync(path.join(output, "runs.json")));
    assert.equal(records.length, 3);
    assert.equal(records[0].status, "failed");
    assert.equal(records[1].status, "passed");
    assert.equal(records[2].status, "failed");
    assert.ok(records.every(row => row.coverage_available));
    assert.ok(records.every(row => row.command.includes(`--coverage.provider=${provider ?? "v8"}`)));
    const coverage = JSON.parse(fs.readFileSync(path.join(output, "coverage.json")));
    assert.equal(coverage.project, "example-native-name");
    assert.deepEqual(coverage.test_coverage["src/agent.ts"]["test/good.test.ts"],
      coverage.test_coverage["src/agent.ts"]["test/bad.test.ts"]);
    assert.deepEqual(coverage.files["src/unreached.ts"].lines.covered, []);
    assert.ok(coverage.files["src/unreached.ts"].lines.total.length);
    const prepared = prepareInputs({ sources: [{ location: { filepath: "src/agent.ts", start_line: 1, end_line: 4 } }], data_dependence: [] }, coverage, coverage.project);
    assert.equal(prepared.generalTestScores["src/agent.ts"].length, 2);
    compareFormal(coverage, project, output);
    for (const row of records) {
      assert.ok(fs.existsSync(path.join(output, row.log)), "Vitest must preserve the execution log");
      assert.ok(JSON.parse(gunzipSync(fs.readFileSync(path.join(output, row.coverage_json)))).constructor === Object);
      assert.ok(!fs.existsSync(path.join(output, row.coverage_json.slice(0, -3))));
    }
    const adapter = createPackageVitestAdapter({
      packages: [{ name: "root", cwd: ".", coverageProvider: provider }],
      launcher: [process.execPath, path.join(modules, "vitest/vitest.mjs")],
    });
    const validation = adapter.validateGeneratedTest({
      projectRoot: project, sourceProjectRoot: project, testFile: "test/good.test.ts",
      outDir: path.join(output, "augment"), timeoutSeconds: 30,
    });
    assert.equal(validation.status, "passed", validation.output_tail);
    assert.ok(validation.cmd.includes(`--coverage.provider=${provider ?? "v8"}`));
    assert.ok(fs.existsSync(validation.coverage_json));
  });
}

test("timeout without coverage records a missing observation, not zero coverage", { skip: !modules }, t => {
  const { root, config, output } = fixture(t, "istanbul");
  const fake = path.join(root, "slow.mjs");
  fs.writeFileSync(fake, "process.on('SIGTERM',()=>process.exit(1)); setInterval(()=>{},1000);\n");
  const settings = JSON.parse(fs.readFileSync(config));
  settings.command = [process.execPath, fake];
  settings.timeout_seconds = 0.2;
  settings.denominator_timeout_seconds = 0.2;
  write(config, settings);
  const result = spawnSync(process.execPath, [collector, "--config", config, "--out-dir", output], { timeout: 15000 });
  assert.equal(result.status, 1);
  const records = JSON.parse(fs.readFileSync(path.join(output, "runs.json")));
  assert.ok(records.every(row => row.status === "timeout" && !row.coverage_available));
  assert.ok(!fs.existsSync(path.join(output, "coverage.json")));
});

for (const fault of ["missing", "malformed", "wrong_test"]) {
  test(`${fault}: retain evidence without publishing an incomplete input`, { skip: !modules }, t => {
    const { root, project, config, output } = fixture(t, "istanbul");
    const script = path.join(root, "fake_vitest.mjs");
    fs.writeFileSync(script, `
import fs from "node:fs";
import path from "node:path";
const args = process.argv.slice(2);
const dir = args[args.indexOf("--coverage.reportsDirectory") + 1];
const reporter = args[args.indexOf("--outputFile") + 1];
const bad = args.at(-1).endsWith("bad.test.ts");
const payload = Object.fromEntries(["agent.ts", "unreached.ts"].map(name => {
  const file = path.join(${JSON.stringify(project)}, "src", name);
  return [file, { path: file, statementMap: {}, s: {}, branchMap: {}, b: {} }];
}));
if (!bad || ${JSON.stringify(fault)} !== "missing") {
  fs.writeFileSync(path.join(dir, "coverage-final.json"),
    bad && ${JSON.stringify(fault)} === "malformed" ? "{" : JSON.stringify(payload));
}
if (bad && ${JSON.stringify(fault)} === "wrong_test") {
  fs.writeFileSync(reporter, JSON.stringify({ testResults: [{ name: "test/unexpected.test.ts" }] }));
}
process.exitCode = bad ? 1 : 0;
`);
    const settings = JSON.parse(fs.readFileSync(config));
    settings.command = [process.execPath, script];
    write(config, settings);
    const result = spawnSync(process.execPath, [collector, "--config", config, "--out-dir", output], { timeout: 15000 });
    assert.equal(result.status, 1);
    const records = JSON.parse(fs.readFileSync(path.join(output, "runs.json")));
    assert.ok(records[0].coverage_available);
    assert.equal(records.at(-1).coverage_available, false);
    assert.equal(records.at(-1).status, "failed");
    assert.ok(fs.existsSync(path.join(output, records.at(-1).log)));
    assert.ok(!fs.existsSync(path.join(output, "coverage.json")));
  });
}

test("coverage merging uses branch identities rather than summing counts", t => {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "coverage_facts_")));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const loc = line => ({ start: { line, column: 0 }, end: { line, column: 5 } });
  const file = { path: path.join(root, "a.ts"), statementMap: { 0: loc(2) }, s: { 0: 1 },
    branchMap: { 0: { type: "if", loc: loc(2), locations: [loc(3), loc(4)] } }, b: { 0: [1, 0] } };
  const report = { [file.path]: file };
  const facts = new CoverageFacts("example", root, ["a.ts"]);
  facts.add(report, { denominator: true });
  facts.add(report, { testFile: "a.test.ts" });
  facts.add({ [file.path]: { ...file, branchMap: { 17: file.branchMap[0] }, b: { 17: [1, 0] } } },
    { testFile: "b.test.ts" });
  const result = facts.finish();
  assert.deepEqual(result.files["a.ts"].branches, [
    { line: 3, total: 1, covered: 1 }, { line: 4, total: 1, covered: 0 },
  ]);
  assert.deepEqual(result.test_coverage["a.ts"]["a.test.ts"].branch_lines, [[3, 4]]);
  facts.add({ [file.path]: { ...file, b: { 0: [0, 1] } } }, { testFile: "c.test.ts" });
  assert.deepEqual(facts.finish().files["a.ts"].branches, [
    { line: 3, total: 1, covered: 1 }, { line: 4, total: 1, covered: 1 },
  ]);
});

test("declarations have no runtime denominator, missing product reports are an error", t => {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "coverage_facts_")));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const facts = new CoverageFacts("example", root, ["types.d.ts"]);
  assert.deepEqual(facts.finish().files["types.d.ts"], { lines: { total: [], covered: [] }, branches: [] });
  assert.throws(() => new CoverageFacts("example", root, ["a.ts"]).finish(), /No executable denominator/u);
});
