import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";

import * as seed from "../typescript/test_seed.mjs";
import { materializeProposal } from "../typescript/materialize.mjs";
import { loadTypeScript } from "../typescript/typescript_ast.mjs";

const formalRoot = process.env.AUGMENT_FORMAL_ROOT;
const enabled = Boolean(formalRoot);
const reference = path.join(formalRoot || ".", "src/common/test_augmentF/TS");
const formalSeed = enabled ? await import(pathToFileURL(path.join(reference, "test_seed.mjs"))) : null;
const formalMaterialize = enabled ? await import(pathToFileURL(path.join(reference, "materialize.mjs"))) : null;
const nodeModules = process.env.ARTIFACT_TEST_NODE_MODULES || process.env.PROBE_TEST_NODE_MODULES;
const compilerRoot = process.env.TYPESCRIPT_ROOT || (nodeModules ? path.dirname(nodeModules) : formalRoot);
const ts = enabled ? loadTypeScript(compilerRoot) : null;

const samples = {
  empty: "",
  comments: '// test("not a call", () => {});\nconst text = "it(1)";\n',
  cases: 'it("a", () => {});\ntest("b", () => {});',
  sameLine: 'const a = 1; it("case", () => {}); const b = 2;\n',
  trailingComment: '  it("case", () => {}); // retained\n  const value = 1;\n',
  emptySuite: 'describe("suite", () => { beforeEach(() => {}); });',
  nested: 'describe("outer", () => { describe("inner", () => { it("case", () => {}); }); });',
  siblingSuites: 'describe("empty", () => {});\ndescribe("full", () => { test("case", () => {}); });',
  helpers: 'describe("suite", () => { registerCases(); beforeEach(() => { setup(); }); expect(1).toBe(1); vi.mock("mod"); });',
  nestedFunction: 'function register() { test("case", () => {}); }\ndescribe("suite", () => { register(); });',
  nestedCalls: 'it("outer", () => { it("inner", () => {}); });',
  aliases: 'import { test as check, describe as group, beforeEach as setup } from "vitest";\ngroup("suite", () => { setup(() => {}); check("case", () => {}); });',
  namespace: 'import * as v from "vitest";\nv.describe("suite", () => { v.beforeEach(() => {}); v.it("case", () => {}); });',
  modifiers: 'describe.skip("suite", () => { it.skip("case", () => {}); });\ntest.each([1])("case", () => {});',
  computed: 'import * as v from "vitest";\nv["describe"]("suite", () => { v["it"]("case", () => {}); });',
  noCallback: 'describe("title");\ndescribe("suite", () => value);\nit("case");',
  returnCall: 'function cases() { return it("case", () => {}); }\ndescribe("suite", () => { cases(); });',
  jsx: 'const el = <div title="test()" />;\ndescribe("suite", () => { test("view", () => el); });',
};

for (const [name, input] of Object.entries(samples)) {
  test(`seed transformations match formal: ${name}`, { skip: !enabled }, () => {
    for (const extension of ["ts", "tsx", "js"]) {
      for (const newline of ["\n", "\r\n"]) {
        const filepath = `test/seed.test.${extension}`;
        for (const source of [input, `${input}\n`].map(text => text.replaceAll("\n", newline))) {
          const actual = seed.withoutSeedTestRegistrations(ts, filepath, source);
          const expected = formalSeed.withoutSeedTestRegistrations(ts, filepath, source);
          assert.deepEqual(actual, expected);
          for (const code of [source, actual.source]) {
            assert.equal(seed.withoutEmptyTestSuites(ts, filepath, code), formalSeed.withoutEmptyTestSuites(ts, filepath, code));
            assert.deepEqual(seed.testSuites(ts, filepath, code), formalSeed.testSuites(ts, filepath, code));
          }
        }
      }
    }
  });

  test(`materialized seed-based test matches formal: ${name}`, { skip: !enabled }, t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "artifact-seed-reference-"));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const filepath = "test/seed.test.tsx";
    fs.mkdirSync(path.join(root, "test"));
    fs.writeFileSync(path.join(root, filepath), input);
    const stripped = formalSeed.withoutSeedTestRegistrations(ts, filepath, input).source;
    const suites = formalSeed.testSuites(ts, filepath, stripped);
    for (const suiteId of ["top-level", ...suites.map(item => item.suite_id), "suite-missing"]) {
      const outputs = [];
      for (const materialize of [materializeProposal, formalMaterialize.materializeProposal]) {
        const testFile = "test/test-augment-example.test.tsx";
        const target = path.join(root, testFile);
        try {
          const record = materialize({
            projectRoot: root,
            seedTestFile: filepath,
            seedTestSha256: crypto.createHash("sha256").update(input).digest("hex"),
            targetModuleImport: "../src/target.js",
            typescript: ts,
            proposal: { test_file: testFile, suite_id: suiteId, append_code: 'it("generated", () => { expect(1).toBe(1); });' },
          });
          outputs.push({ record, code: fs.readFileSync(target, "utf8") });
        } catch (error) {
          outputs.push({ name: error.name, message: error.message });
        } finally {
          fs.rmSync(target, { force: true });
        }
      }
      assert.deepEqual(outputs[0], outputs[1], suiteId);
    }
  });
}
