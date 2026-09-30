import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { analyzeFactProject } from "../typescript/flow/analysis_fact.mjs";
import { typescriptBoundaries } from "../typescript/source_rules.mjs";
import { loadFileList } from "../typescript/flow/source_locator.mjs";

test("explicit source paths are retained regardless of helper or mock names", (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "source-manifest-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const files = ["agent.ts", "test-helper-provider.ts", "test-mocks.ts", "fixtures/adapter.js"];
  for (const file of files) {
    fs.mkdirSync(path.dirname(path.join(root, file)), { recursive: true });
    fs.writeFileSync(path.join(root, file), "export const result = 1;\n");
  }
  const sourceBase = path.join(root, "source_files.json");
  for (const manifest of [{ files }, { locations: files.map((file) => ({ file })) }]) {
    fs.writeFileSync(sourceBase, JSON.stringify(manifest));
    assert.deepEqual(loadFileList({ root, sourceBase }).files, files);
  }
  fs.writeFileSync(sourceBase, JSON.stringify({ files: [files[0]], locations: [{ file: files[1] }] }));
  assert.deepEqual(loadFileList({ root, sourceBase }).files, [files[0]]);
  fs.unlinkSync(path.join(root, files[1]));
  fs.writeFileSync(sourceBase, JSON.stringify({ files: [files[1]] }));
  assert.throws(() => loadFileList({ root, sourceBase }), /files are missing/u);
});

for (const extension of ["ts", "tsx", "mts", "cts", "js", "jsx", "mjs", "cjs"]) {
  test(`manifest preserves cross-file flow with canonical paths: ${extension}`, {
    skip: !process.env.TYPESCRIPT_ROOT,
  }, async t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "manifest-flow-"));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    fs.mkdirSync(path.join(root, "src"));
    const provider = `src/provider.${extension}`;
    const agent = "src/agent.ts";
    fs.writeFileSync(path.join(root, provider), 'import { generateText } from "ai";\nexport async function model() { return generateText({prompt: "fixture"}); }\n');
    fs.writeFileSync(path.join(root, agent), 'import { model } from "./provider";\nexport async function run() {\n  const value = await model();\n  return value.text;\n}\n');
    const ts = createRequire(path.join(process.env.TYPESCRIPT_ROOT, "package.json"))("typescript");
    const analyze = files => analyzeFactProject({
      ts, root, files, project: "fixture", sourceRules: typescriptBoundaries(),
      options: { maxIterations: 80, controlDependenceMode: "block_only" },
    });
    const expected = analyze([provider, agent]);
    assert.equal(expected.sources.length, 1);
    assert.equal(expected.data_dependence.length, 2);
    const sourceBase = path.join(root, "sources.json");
    const formal = process.env.LDH_FORMAL_ROOT ? await import(pathToFileURL(path.join(
      process.env.LDH_FORMAL_ROOT, "src/common/llm_dependent/TS/flow/source_locator.mjs",
    ))) : null;
    for (const files of [[provider, agent], [`./${provider}`, "src/../src/agent.ts"]]) {
      for (const payload of [{ files }, { locations: files.map(file => ({ file })) }]) {
        fs.writeFileSync(sourceBase, JSON.stringify(payload));
        const actual = loadFileList({ root, sourceBase }).files;
        assert.deepEqual(actual, [provider, agent]);
        assert.deepEqual(analyze(actual), expected);
        if (formal) {
          const oldFiles = formal.loadFileList({ root, sourceBase }).files;
          const omittedExtension = extension === "mts" || extension === "cts";
          assert.deepEqual(oldFiles, omittedExtension ? files.slice(1) : files);
          const old = analyze(oldFiles);
          if (!omittedExtension && files[0] === provider) {
            assert.deepEqual(old, expected);
          } else {
            assert.equal(old.sources.length, omittedExtension ? 0 : 1);
            assert.equal(old.data_dependence.length, 0);
          }
        }
      }
    }
    fs.writeFileSync(sourceBase, JSON.stringify({ files: [agent, `./${agent}`] }));
    assert.throws(() => loadFileList({ root, sourceBase }), /duplicate/u);
    fs.writeFileSync(sourceBase, JSON.stringify({ files: ["../outside.ts"] }));
    assert.throws(() => loadFileList({ root, sourceBase }), /escapes/u);
  });
}
