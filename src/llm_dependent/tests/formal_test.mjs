import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import test from "node:test";

import { analyzeFactProject } from "../typescript/flow/analysis_fact.mjs";
import { DirtyFunctionQueue, enqueueChangedRefs } from "../typescript/flow/fact_analysis/worklist.mjs";
import { refKey } from "../typescript/flow/models.mjs";
import { typescriptBoundaries } from "../typescript/source_rules.mjs";
import { regionPayload, withoutUnusedArguments } from "./formal_evidence.mjs";

const formalRoot = process.env.LDH_FORMAL_ROOT;
const typescriptRoot = process.env.TYPESCRIPT_ROOT;
const enabled = Boolean(formalRoot && typescriptRoot);
const artifact = fileURLToPath(new URL("../typescript/", import.meta.url));
const reference = path.join(formalRoot || ".", "src/common/llm_dependent/TS");

test(
  "retained dirty-queue operations match formal",
  { skip: !enabled },
  async () => {
    const formal = await import(
      pathToFileURL(path.join(reference, "flow/fact_analysis/worklist.mjs"))
    );
    for (const keys of [[], ["b", "a"], ["c", "a", "b"]]) {
      const order = keys.map((key) => ({ key }));
      const actual = new DirtyFunctionQueue(order);
      const expected = new formal.DirtyFunctionQueue(order);
      for (const batch of [["a", "b", "a", "unknown"], [], ["c", "b", "a"]]) {
        for (const key of batch) {
          actual.add(key);
          expected.add(key);
        }
        assert.deepEqual(actual.drain(), expected.drain());
      }
    }
  },
);

for (const wrapped of [false, true]) {
  for (const ignoreLocalFunction of [null, "self", "reader", "unknown"]) {
    test(`changed refs preserve scheduling: wrapped=${wrapped}, ignore=${ignoreLocalFunction}`, { skip: !enabled }, async () => {
      const formal = await import(pathToFileURL(path.join(reference, "flow/fact_analysis/worklist.mjs")));
      const refs = [
        { kind: "local", function: "self", path: "options.nested.value" },
        { kind: "module", file: "agent.ts", path: "options.nested.value" },
        { kind: "class_field", class: "Agent", path: "options.nested.value" },
        { kind: "return", function: "callee", path: "result" },
      ];
      const readers = ref => new Map([[refKey(ref), new Set(["self", "reader", "unknown"])]]);
      const input = {
        callersByCallee: new Map([["callee", new Set(["caller", "self", "unknown"])]]),
        localRefReaders: readers(refs[0]),
        moduleRefReaders: readers(refs[1]),
        classFieldReaders: readers(refs[2]),
        descendantRefReaders: new Map(refs.slice(0, 3).flatMap(ref => [
          [refKey({ ...ref, path: "options" }), new Set(["parent", "self"])],
          [refKey({ ...ref, path: "options.nested" }), new Set(["reader", "self"])],
        ])),
        ignoreLocalFunction,
      };
      const order = ["parent", "self", "caller", "reader"].map(key => ({ key }));
      const actual = new DirtyFunctionQueue(order);
      const expected = new formal.DirtyFunctionQueue(order);
      const actualCalls = [];
      const expectedCalls = [];
      for (const [queue, calls] of [[actual, actualCalls], [expected, expectedCalls]]) {
        const add = queue.add;
        queue.add = function (id) { calls.push(id); add.call(this, id); };
      }
      for (const batch of [[], ...refs.map(ref => [ref, ref]), refs, [...refs].reverse()]) {
        const values = wrapped ? batch.map(ref => ({ ref, kinds: new Set(["taint", "type"]) })) : batch;
        enqueueChangedRefs({ ...input, refs: values, queue: actual });
        formal.enqueueChangedRefs({ ...input, refs: values, queue: expected });
        assert.deepEqual(actualCalls, expectedCalls);
        assert.deepEqual([...actual.pending], [...expected.pending]);
        assert.deepEqual(actual.drain(), expected.drain());
      }
    });
  }
}

function files(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const file = path.join(directory, entry.name);
    return entry.isDirectory()
      ? files(file)
      : file.endsWith(".mjs")
        ? [file]
        : [];
  });
}

test(
  "analysis syntax and source catalog preserve formal semantics",
  { skip: !enabled },
  async () => {
    const ts = createRequire(path.join(typescriptRoot, "package.json"))(
      "typescript",
    );
    const printer = ts.createPrinter({ removeComments: true });
    const print = (file, omit = [], formal = false, omitImports = false) => {
      const source = ts.createSourceFile(
        file, fs.readFileSync(file, "utf8").replaceAll("../source-rules.mjs", "../source_rules.mjs"),
        ts.ScriptTarget.Latest, true, ts.ScriptKind.JS,
      );
      if (formal) withoutUnusedArguments(ts, source);
      source.statements = ts.factory.createNodeArray(
        source.statements.filter(statement => !omit.includes(statement.name?.text)
          && !(omitImports && ts.isImportDeclaration(statement))),
      );
      let printed = printer.printFile(source);
      if (!formal && file === path.join(artifact, "flow/source_locator.mjs")) {
        const corrected = String.raw`/\.(?:ts|tsx|mts|cts|js|jsx|mjs|cjs)$/`;
        assert.equal(printed.split(corrected).length, 2);
        printed = printed.replace(corrected, String.raw`/\.(?:ts|tsx|js|jsx|mjs|cjs)$/`);
      }
      return printed;
    };
    for (const file of files(path.join(artifact, "flow"))) {
      const relative = path.relative(artifact, file);
      if (relative === "flow/fact_analysis/worklist.mjs") continue;
      if (["flow/analysis_fact.mjs", "flow/resolver/utils.mjs", "flow/facts.mjs"].includes(relative)) continue;
      // Parameter-shadowing corrections have independent positive/negative fixtures.
      const bindingFix = relative === "flow/resolver/names.mjs";
      const omit = bindingFix ? ["resolveExprName", "resolveName", "parameterScopeLimit"]
        : relative === "flow/payload.mjs" ? ["buildFactPayload"]
        // Explicit manifest selection is covered by source_manifest_test.mjs.
        : relative === "flow/source_locator.mjs" ? ["loadFileList", "sourceFilesFromPayload", "isProductSourceFile"] : [];
      assert.equal(print(file, omit, false, bindingFix), print(path.join(reference, relative), omit, true, bindingFix), relative);
    }
    const formal = await import(
      pathToFileURL(path.join(reference, "source-rules.mjs"))
    );
    // Descriptive catalog text is omitted; every matching field and rule order remains.
    const catalog = (items) =>
      items.map(({ notes, description, ...rule }) => rule);
    assert.deepEqual(
      catalog(typescriptBoundaries()),
      catalog(formal.typescriptBoundaries()),
    );
  },
);

for (const mode of [
  "block_only",
  "control-dependence-direct",
  "control-dependence-recursive",
]) {
  for (const limit of [1, 120]) {
    test(
      `payload matches formal: ${mode}, limit=${limit}`,
      { skip: !enabled },
      async (t) => {
        const root = fs.mkdtempSync(path.join(os.tmpdir(), "ldh-compare-"));
        t.after(() => fs.rmSync(root, { recursive: true, force: true }));
        const sources = {
          "provider.ts":
            'import OpenAI from "openai";\nexport async function model() {\n return new OpenAI().responses.create({input:"x"});\n}\n',
          "agent.ts":
            'import { model } from "./provider";\nfunction pure() { return "constant"; }\nexport async function run() {\n const value = await model();\n if (value) {\n  pure();\n }\n return value;\n}\n',
        };
        for (const [file, text] of Object.entries(sources))
          fs.writeFileSync(path.join(root, file), text);
        const ts = createRequire(path.join(typescriptRoot, "package.json"))(
          "typescript",
        );
        const formal = await import(
          pathToFileURL(path.join(reference, "flow/analysis_fact.mjs"))
        );
        const rules = await import(
          pathToFileURL(path.join(reference, "source-rules.mjs"))
        );
        const input = {
          ts,
          root,
          files: Object.keys(sources),
          project: "fixture",
          options: { maxIterations: limit, controlDependenceMode: mode },
        };
        assert.deepEqual(
          analyzeFactProject({ ...input, sourceRules: typescriptBoundaries() }),
          regionPayload(formal.analyzeFactProject({
            ...input,
            sourceRules: rules.typescriptBoundaries(),
          })),
        );
      },
    );
  }
}

test(
  "formal TypeScript regression corpus runs on the copied artifact",
  { skip: !enabled },
  (t) => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "ldh-regressions-"));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const copied = path.join(root, "typescript");
    fs.cpSync(artifact, copied, { recursive: true });
    fs.cpSync(
      path.join(reference, "flow/tests"),
      path.join(copied, "flow/tests"),
      { recursive: true },
    );
    for (const file of files(path.join(copied, "flow/tests"))) {
      const source = fs.readFileSync(file, "utf8");
      fs.writeFileSync(file, source.replaceAll("source-rules.mjs", "source_rules.mjs"));
    }
    const result = spawnSync(
      process.execPath,
      [path.join(copied, "flow/tests/run-regressions.mjs")],
      {
        env: { ...process.env, TMPDIR: root },
        cwd: root,
        encoding: "utf8",
        timeout: 120000,
      },
    );
    assert.equal(result.status, 0, result.stdout + result.stderr);
    assert.match(result.stdout, /TS LDCR regressions passed: \d+/);
    console.log(result.stdout.trim().split("\n").at(-1));
  },
);
