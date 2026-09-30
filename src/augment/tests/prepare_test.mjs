import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";

import { prepareInputs } from "../typescript/input/prepare.mjs";
import { loadInputs } from "../typescript/input/snapshot.mjs";
import { loadGeneralCoverage } from "../typescript/general_coverage.mjs";
import { buildAugmentScope } from "./scope_reference.mjs";
import { projectFixture, writeJson } from "./typescript_fixture.mjs";

function inputs() {
  return {
    regions: {
      project: "typescript",
      sources: [{ location: { filepath: "src/a.ts", start_line: 2, end_line: 4 } }],
      data_dependence: [],
    },
    coverage: {
      project: "fixture",
      files: { "src/a.ts": {
        lines: { total: [[1, 5]], covered: [[1, 3]] },
        branches: [{ line: 2, total: 2, covered: 1 }],
      } },
      test_coverage: { "src/a.ts": {
        "test/a.test.ts": { lines: [[1, 3], [5, 5]], branch_lines: [[2, 2]] },
        "test/b.test.ts": { lines: [[1, 1]], branch_lines: [] },
      } },
    },
  };
}

test("preparation derives scores without counting branch outcomes or merging line kinds", () => {
  const { regions, coverage } = inputs();
  const before = JSON.stringify({ regions, coverage });
  const result = prepareInputs(regions, coverage, "fixture");
  assert.deepEqual([...result.ldhFiles], ["src/a.ts"]);
  assert.deepEqual(result.generalTestScores["src/a.ts"], [
    { test_file: "test/a.test.ts", score: 5 }, { test_file: "test/b.test.ts", score: 1 },
  ]);
  assert.equal(result.seedCoverage, null);
  assert.equal(JSON.stringify({ regions, coverage }), before);
});

test("only executable source/data gaps expand the candidate scope", () => {
  const { regions, coverage } = inputs();
  const file = coverage.files["src/a.ts"];
  regions.control_dependence = [{ location: { filepath: "unmeasured.ts", start_line: 1, end_line: 2 } }];
  file.lines.covered = [[1, 4]];
  assert.equal(prepareInputs(regions, coverage, "fixture").ldhFiles.size, 1, "branch-only gap");
  file.branches[0].covered = 2;
  assert.equal(prepareInputs(regions, coverage, "fixture").ldhFiles.size, 0, "line 5 is outside regions");
  regions.data_dependence = [{ location: { filepath: "src/a.ts", start_line: 5, end_line: 8 } }];
  assert.equal(prepareInputs(regions, coverage, "fixture").ldhFiles.size, 1);
  file.lines.covered = [[1, 8]];
  assert.equal(prepareInputs(regions, coverage, "fixture").ldhFiles.size, 0, "non-executable lines ignored");
});

test("line/count eligibility agrees with canonical branch-arm projection", () => {
  const { regions, coverage } = inputs();
  const location = line => ({ start: { line, column: 0 }, end: { line, column: 5 } });
  for (const missingLine of [false, true]) {
    for (const missingArm of [false, true]) {
      coverage.files["src/a.ts"].lines.covered = missingLine ? [[1, 3]] : [[1, 5]];
      coverage.files["src/a.ts"].branches[0].covered = missingArm ? 1 : 2;
      const raw = { "src/a.ts": {
        statementMap: Object.fromEntries([1, 2, 3, 4, 5].map(line => [line, location(line)])),
        s: { 1: 1, 2: 1, 3: 1, 4: Number(!missingLine), 5: Number(!missingLine) },
        branchMap: { 0: { type: "if", loc: location(2), locations: [location(2), location(2)] } },
        b: { 0: [1, Number(!missingArm)] },
      } };
      const scope = buildAugmentScope(regions, raw, { project: "fixture", projectRoot: process.cwd() });
      const expected = scope.targets.filter(item => item.uncovered_lines.length || item.uncovered_branch_slots.length);
      assert.deepEqual([...prepareInputs(regions, coverage, "fixture").ldhFiles], expected.map(item => item.filepath));
    }
  }
});

test("optional seed cache preserves only explicitly measured pairs", () => {
  const { regions, coverage } = inputs();
  coverage.seed_coverage = { project: "fixture", observations: {
    "test/a.test.ts": { sha256: "a".repeat(64), targets: {
      "src/a.ts": { sha256: "b".repeat(64), covered_lines: [1, 3] },
    } },
  } };
  const result = prepareInputs(regions, coverage, "fixture");
  assert.deepEqual([...result.seedCoverage.observations.keys()], ["test/a.test.ts"]);
  assert.deepEqual(result.seedCoverage.observations.get("test/a.test.ts").targets.get("src/a.ts").covered_lines, [1, 3]);
  assert.equal(result.generalTestScores["src/a.ts"].length, 2);
  delete coverage.seed_coverage;
  assert.deepEqual(prepareInputs(regions, coverage, "fixture"), {
    ...result, seedCoverage: null,
  });
});

for (const ranges of [null, [[0, 1]], [[3, 2]], [[1, 2], [2, 3]], [[3, 3], [1, 1]], [[1.5, 2]], [[1]]]) {
  test(`invalid test line ranges are rejected: ${JSON.stringify(ranges)}`, () => {
    const { regions, coverage } = inputs();
    coverage.test_coverage["src/a.ts"]["test/a.test.ts"].lines = ranges;
    assert.throws(() => prepareInputs(regions, coverage, "fixture"), /ranges/u);
  });
}

test("missing attribution and mismatched input identity fail before generation", () => {
  const { regions, coverage } = inputs();
  assert.throws(() => prepareInputs(regions, coverage, "other"), /project/u);
  delete coverage.test_coverage;
  assert.throws(() => prepareInputs(regions, coverage, "fixture"), /test_coverage/u);
  coverage.test_coverage = {};
  regions.sources[0].location.filepath = "src/missing.ts";
  assert.throws(() => prepareInputs(regions, coverage, "fixture"), /missing target file/u);
  regions.sources[0].location.filepath = "../outside.ts";
  assert.throws(() => prepareInputs(regions, coverage, "fixture"), /invalid source location/u);
});

test("loader accepts the three portable files without modifying the input directory", t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "augment_prepare_"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const { project, input } = projectFixture(root, path.join(root, "dependencies"));
  const before = fs.readdirSync(root);
  const result = loadInputs(input);
  assert.equal(result.baseInput.project_root, project);
  assert.deepEqual([...result.ldhFiles], ["src/target.ts"]);
  assert.deepEqual(fs.readdirSync(root), before);
  writeJson(input, { ...result.baseInput, ldh: {} });
  assert.throws(() => loadInputs(input), /Input path/u);
});

test("file-keyed coverage preserves denominators, zero coverage, and branch counts", () => {
  const { coverage } = inputs();
  coverage.files["src/a.ts"].lines.covered = [[1, 3], [9, 9]];
  coverage.files["src/unreached.ts"] = {
    lines: { total: [[2, 2]], covered: [] },
    branches: [{ line: 2, total: 2, covered: 0 }],
  };
  coverage.files["src/empty.ts"] = { lines: { total: [], covered: [] }, branches: [] };
  assert.deepEqual(loadGeneralCoverage(coverage), { files: {
    "src/a.ts": {
      total_lines: [1, 2, 3, 4, 5], covered_lines: [1, 2, 3],
      branches: [{ line: 2, total: 2, baseline_covered: 1, generated_covered_slots: [] }],
    },
    "src/unreached.ts": {
      total_lines: [2], covered_lines: [],
      branches: [{ line: 2, total: 2, baseline_covered: 0, generated_covered_slots: [] }],
    },
    "src/empty.ts": { total_lines: [], covered_lines: [], branches: [] },
  } });
});

test("file-keyed coverage rejects malformed containers and branch records", () => {
  for (const files of [undefined, null, [], "invalid"]) {
    assert.throws(() => loadGeneralCoverage({ files }), /files object/u);
  }
  for (const file of [null, [], 1]) {
    assert.throws(() => loadGeneralCoverage({ files: { "a.ts": file } }), /file record/u);
  }
  for (const branches of [
    [{ line: 2, total: 2, covered: 3 }],
    [{ line: 2, total: 2, covered: 1 }, { line: 2, total: 2, covered: 0 }],
  ]) {
    assert.throws(() => loadGeneralCoverage({ files: { "a.ts": { branches } } }), /branch record/u);
  }
});

test("README TS coverage example is accepted by the input preparation", () => {
  const readme = fs.readFileSync(new URL("../../../resources/inputs/README.md", import.meta.url), "utf8");
  const examples = [...readme.matchAll(/```json\n([\s\S]*?)\n```/gu)].map(match => JSON.parse(match[1]));
  const coverage = examples.find(example => example.test_coverage);
  assert.ok(coverage);
  const result = prepareInputs({
    sources: [{ location: { filepath: "src/example.ts", start_line: 1, end_line: 8 } }],
    data_dependence: [],
  }, coverage, coverage.project);
  assert.deepEqual([...result.ldhFiles], ["src/example.ts"]);
  assert.deepEqual(result.generalTestScores["src/example.ts"], [
    { test_file: "src/example.test.ts", score: 5 },
  ]);
});
