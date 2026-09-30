import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import test from "node:test";

import { analyzeFactProject } from "../typescript/flow/analysis_fact.mjs";
import { buildProjectIndex } from "../typescript/flow/indexing.mjs";
import { resolveExprName } from "../typescript/flow/resolver/names.mjs";
import { typescriptBoundaries } from "../typescript/source_rules.mjs";
import { regionPayload } from "./formal_evidence.mjs";

const typescriptRoot = process.env.TYPESCRIPT_ROOT;
const formal = process.env.LDH_FORMAL_ROOT
  ? await import(pathToFileURL(path.join(process.env.LDH_FORMAL_ROOT, "src/common/llm_dependent/TS/flow/analysis_fact.mjs")))
  : null;
const prefix = `import { generateText } from "ai";
function constant(options: unknown) { return { text: "constant" }; }
`;
const cases = [
  ["direct parameter", `function run(generateText: typeof constant) {
    return generateText({ prompt: "x" });
  }
  run(constant);`, 0, 1],
  ["captured parameter", `function run(generateText: typeof constant) {
    function nested() { return generateText({ prompt: "x" }); }
    return nested();
  }
  run(constant);`, 0, 1],
  ["returned closure", `function run(generateText: typeof constant) {
    return () => generateText({ prompt: "x" });
  }
  run(constant)();`, 0, 1],
  ["destructured parameter", `function run({ call: generateText }: { call: typeof constant }) {
    return generateText({ prompt: "x" });
  }
  run({ call: constant });`, 0, 1],
  ["array parameter", `function run([generateText]: [typeof constant]) {
    return generateText({ prompt: "x" });
  }
  run([constant]);`, 0, 1],
  ["inline callback parameter", `function run() {
    return [constant].map(generateText => generateText({ prompt: "x" }));
  }
  run();`, 0, 1],
  ["namespace parameter", `import * as ai from "ai";
  function run(ai: { generateText: typeof constant }) {
    return ai.generateText({ prompt: "x" });
  }
  run({ generateText: constant });`, 0, 1],
  ["unshadowed import", `function run() {
    return generateText({ prompt: "x" });
  }`, 1],
  ["unshadowed closure", `function run() {
    function nested() { return generateText({ prompt: "x" }); }
    return nested();
  }`, 1],
  ["unshadowed inline callback", `function run() {
    return ["x"].map(prompt => generateText({ prompt }));
  }`, 1],
  ["sibling scope", `function other(generateText: typeof constant) {
    return generateText({ prompt: "x" });
  }
  function run() { return generateText({ prompt: "x" }); }`, 1, 2],
  ["local callback", `function run() {
    const generateText = (options: unknown) => constant(options);
    return generateText({ prompt: "x" });
  }`, 0],
  ["provider through client facts", `import OpenAI from "openai";
  function run(OpenAI: unknown, client: any) {
    return client.responses.create({ input: "x" });
  }
  function main() { return run(null, new OpenAI()); }`, 1],
  ["local callable inside parameter scope", `function run(generateText: unknown) {
    function nested() {
      function generateText() { return constant(null); }
      return generateText();
    }
    return nested();
  }`, 0],
  ["separate type namespace", `class Client {
    invoke() { return generateText({ prompt: "x" }); }
  }
  function run(Client: Client) { return Client.invoke(); }`, 1],
];

for (const [name, body, sources, formalSources = sources] of cases) {
  test(`provider source binding: ${name}`, { skip: !typescriptRoot }, (t) => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "ldh-shadowing-"));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    fs.writeFileSync(path.join(root, "subject.ts"), prefix + body);
    const ts = createRequire(path.join(typescriptRoot, "package.json"))("typescript");
    const input = {
      ts, root, files: ["subject.ts"], project: "fixture",
      sourceRules: typescriptBoundaries(),
      options: { maxIterations: 120, controlDependenceMode: "block_only" },
    };
    const payload = analyzeFactProject(input);
    assert.equal(payload.sources.length, sources, JSON.stringify(payload.sources));
    if (!sources) assert.deepEqual(payload.data_dependence, []);
    assert.equal(payload.fixed_point.converged, true);
    if (formal) {
      const reference = formal.analyzeFactProject(input);
      assert.equal(reference.sources.length, formalSources);
      if (sources === formalSources) assert.deepEqual(payload, regionPayload(reference));
    }
  });
}

test("a string parameter is not a sibling callable, while direct calls still resolve", { skip: !typescriptRoot }, (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "ldh-parameter-alias-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  fs.writeFileSync(path.join(root, "subject.ts"), `function run() {
    const heading = (value: string) => String(value);
    const value = (text: string) => String(text);
    return value("x");
  }`);
  const ts = createRequire(path.join(typescriptRoot, "package.json"))("typescript");
  const index = buildProjectIndex({ ts, root, files: ["subject.ts"] });
  const functions = [...index.functions.values()];
  const heading = functions.find(info => info.qualname === "run.heading");
  const value = functions.find(info => info.qualname === "run.value");
  const run = functions.find(info => info.qualname === "run");
  const argument = heading.node.body.arguments[0];
  assert.deepEqual(resolveExprName(ts, argument, heading.scope, index), []);
  const call = run.node.body.statements.at(-1).expression;
  assert.deepEqual(
    resolveExprName(ts, call.expression, run.scope, index).map(item => item.function),
    [value.key],
  );
});
