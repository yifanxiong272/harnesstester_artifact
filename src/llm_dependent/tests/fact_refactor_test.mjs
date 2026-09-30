import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import test from "node:test";

import { FlowAnalyzer } from "../typescript/flow/analysis_fact.mjs";
import { exprInfo } from "../typescript/flow/fact_analysis/expr_info.mjs";
import { FactStore } from "../typescript/flow/facts.mjs";
import * as utils from "../typescript/flow/resolver/utils.mjs";
import { typescriptBoundaries } from "../typescript/source_rules.mjs";
import { regionPayload, formalFactState, analyzedRun, withoutUnusedArguments } from "./formal_evidence.mjs";

const enabled = Boolean(process.env.LDH_FORMAL_ROOT && process.env.TYPESCRIPT_ROOT);
const reference = path.join(process.env.LDH_FORMAL_ROOT || ".", "src/common/llm_dependent/TS");
const ts = enabled ? createRequire(path.join(process.env.TYPESCRIPT_ROOT, "package.json"))("typescript") : null;
const formal = enabled ? await import(pathToFileURL(path.join(reference, "flow/analysis_fact.mjs"))) : null;
const formalUtils = enabled ? await import(pathToFileURL(path.join(reference, "flow/resolver/utils.mjs"))) : null;
const formalFacts = enabled ? await import(pathToFileURL(path.join(reference, "flow/facts.mjs"))) : null;

test("unchanged TypeScript transfer declarations still match formal syntax", { skip: !enabled }, () => {
  const printer = ts.createPrinter({ removeComments: true });
  const changed = new Set([
    "seedModuleStatement", "seedModuleTarget", "moduleValueInfo",
    "propagateObjectLiteralFields", "eventChannelPayloadRefs", "moduleTargetRefs",
    "dedupeRefsByKey", "dedupeRefs", "dedupeResolvedNames", "dedupeCallTargets", "uniqueBy",
    "setHasFactValue", "addFactValue", "addReturnParamDeps", "#addRefValues", "#addStringMapValues",
    "runFixedPoint", "enqueueChangedRefs", "mergeDirtyStats", "emptyDirtyStats",
    "mergeDirtyStatsFromDrain", "mergeCountMap", "drainChangedRefs", "#markChanged",
    "addTaint", "addParamTaint", "addProvider", "addType", "addAlias", "addParamDep", "addString",
    "evalExpr", "mergeChildExprInfo", "infoForPath", "eventChannelPayloadInfo",
    "callCalleeInfo", "readRefFacts", "formalInputInfo",
  ]);
  function declarations(file, formal = false) {
    const source = ts.createSourceFile(file,
      fs.readFileSync(file, "utf8").replaceAll("../source-rules.mjs", "../source_rules.mjs"),
      ts.ScriptTarget.Latest, true, ts.ScriptKind.JS);
    if (formal) withoutUnusedArguments(ts, source);
    const output = [];
    for (const statement of source.statements) {
      if (ts.isImportDeclaration(statement) && statement.importClause?.namedBindings?.elements?.some(
        item => item.name.text === "uniqueBy",
      )) continue;
      if (ts.isClassDeclaration(statement)) {
        for (const member of statement.members) {
          if (!changed.has(member.name?.text)) output.push(printer.printNode(ts.EmitHint.Unspecified, member, source));
        }
      } else if (!changed.has(statement.name?.text)) {
        output.push(printer.printNode(ts.EmitHint.Unspecified, statement, source));
      }
    }
    return output;
  }
  for (const relative of ["flow/analysis_fact.mjs", "flow/resolver/utils.mjs", "flow/facts.mjs"]) {
    const artifact = fileURLToPath(new URL(`../typescript/${relative}`, import.meta.url));
    assert.deepEqual(declarations(artifact), declarations(path.join(reference, relative), true), relative);
  }
});

function pairedStores() {
  const actual = new FactStore();
  const expected = new formalFacts.FactStore();
  return {
    actual,
    expected,
    call(method, ...args) {
      const result = actual[method](...args);
      const reference = expected[method](...args);
      assert.deepEqual(result, method === "drainChangedRefs" ? reference.map(item => item.ref) : reference, method);
      assert.deepEqual({ ...actual }, formalFactState(expected), method);
      return result;
    },
  };
}

for (const [add, get] of [
  ["addTaint", "taintOf"], ["addParamTaint", "paramTaintOf"],
  ["addProvider", "providerOf"], ["addType", "typeOf"],
  ["addAlias", "aliasOf"], ["addParamDep", "paramDepOf"], ["addString", "stringOf"],
]) {
  test(`fact-set writes match formal: ${add}`, { skip: !enabled }, () => {
    const { call, actual, expected } = pairedStores();
    const ref = { kind: "local", function: "f", path: "options.nested.value" };
    const span = { filepath: "provider.ts", start_line: 2, end_line: 4 };
    const target = { key: "handler", positional_offset: 0 };
    const values = [span, { ...span, extra: "same span" }, target, { ...target },
      { positional_offset: 0, key: "handler" }, "provider", "provider", null, undefined, 0, "0"];
    for (const batch of [undefined, [], new Set(), values, values, new Set(values)]) {
      call(add, ref, batch);
      call(get, ref);
      call("descendantRefsOf", { ...ref, path: "options" });
      call("drainChangedRefs");
      call("drainChangedRefs");
    }
    assert.equal([...actual[get](ref)][0], span);
    assert.equal([...expected[get](ref)][0], span);
    // Stored objects retain identity: mutations must affect the next comparison.
    span.end_line = 5;
    call(add, ref, [{ filepath: "provider.ts", start_line: 2, end_line: 4 }, { ...span }]);
    call("drainChangedRefs");
    actual[get](ref).clear();
    call(get, ref);
  });
}

test("return parameter merges preserve notifications, empty entries, and copies", { skip: !enabled }, () => {
  const { actual, call } = pairedStores();
  const first = { function: "f", name: "options" };
  const second = { function: "f", name: "fallback" };
  const span = { filepath: "agent.ts", start_line: 3, end_line: 3 };
  call("addReturnParamDeps", "f", [], span);
  assert.equal(actual.returnParamDeps.has("f"), true);
  for (const [deps, value] of [
    [[first, { ...first }, second], span], [[first], { ...span }],
    [new Set([second]), { ...span, end_line: 4 }], [undefined, span],
  ]) {
    call("addReturnParamDeps", "f", deps, value);
    call("returnParamDepsOf", "f");
    call("drainChangedRefs");
  }
  const copy = call("returnParamDepsOf", "f");
  assert.equal(copy.get("f:options").dep, first);
  assert.equal([...copy.get("f:options").spans][0], span);
  copy.get("f:options").spans.clear();
  copy.clear();
  call("returnParamDepsOf", "f");
  span.end_line = 8;
  call("addReturnParamDeps", "f", [first], { ...span, end_line: 3 });
  call("drainChangedRefs");
});

test("mixed fact kinds retain changed-ref order and error behavior", { skip: !enabled }, () => {
  const { actual, expected, call } = pairedStores();
  const refs = [
    { kind: "return", function: "f", path: "nested.value" },
    { kind: "module", file: "a.ts", path: "options.value" },
    { kind: "class_field", class: "Agent", path: "options.value" },
  ];
  for (const ref of refs) {
    for (const method of ["addString", "addType", "addProvider", "addString"]) {
      call(method, ref, ["first", "second", "first"]);
    }
    call("descendantRefsOf", { ...ref, path: "" });
    call("descendantRefsOf", { ...ref, path: "options" });
  }
  call("drainChangedRefs");
  call("drainChangedRefs");
  for (const args of [[{ kind: "unknown" }, []], [refs[0], 1]]) {
    let error;
    try { expected.addString(...args); } catch (caught) { error = caught; }
    assert.ok(error);
    assert.throws(() => actual.addString(...args), { name: error.name, message: error.message });
    assert.deepEqual({ ...actual }, formalFactState(expected));
  }
});

test("deduplication preserves formal keys, first objects, and order", { skip: !enabled }, () => {
  const cases = {
    dedupeRefs: [null, {}, { kind: "local", function: "f", path: "x" },
      { path: "x", function: "f", kind: "local" }, { kind: "return", function: "f" }],
    dedupeResolvedNames: [
      { kind: "function", full_name: "a", function: "f" },
      { kind: "function", full_name: "a", function: "f", extra: 1 },
      { kind: "class", full_name: "a", class: "c" },
      { kind: "external", full_name: "a", function: "", class: null },
    ],
    dedupeCallTargets: [{ key: "f", positional_offset: 0 }, { key: "f", positional_offset: 1 },
      { key: "f", positional_offset: 0, extra: 1 }, { key: "g" }],
  };
  for (const [name, pool] of Object.entries(cases)) {
    for (let seed = 0; seed < 40; seed += 1) {
      const items = Array.from({ length: seed }, (_, i) => pool[(i * 7 + seed) % pool.length]);
      const expected = formalUtils[name](items);
      const actual = utils[name](items);
      assert.deepEqual(actual, expected);
      actual.forEach((item, index) => assert.equal(item, expected[index]));
    }
  }
});

test("object field propagation preserves read/write order and recursive facts", { skip: !enabled }, () => {
  const samples = ["{}", "{ value, nested: { value }, method() { return value; } }",
    "{ ...base, [key]: value, 1: value, accessor: undefined }",
    "{ deep: { ...base, inner: { callback: value } }, value: other }"];
  for (const code of samples) {
    const source = ts.createSourceFile("fixture.ts", `const result = ${code};`, ts.ScriptTarget.Latest, true);
    const literal = source.statements[0].declarationList.declarations[0].initializer;
    function run(Analyzer) {
      const calls = [];
      const analyzer = Object.create(Analyzer.prototype);
      Object.assign(analyzer, {
        ts,
        bindingValueInfo(node) {
          calls.push(["read", node.getText(source)]);
          const info = exprInfo();
          info.strings.add(node.getText(source));
          return info;
        },
        spreadDescendantFieldInfo(node) { calls.push(["spread", node.getText(source)]); return exprInfo(); },
        addInfoToRef(...args) { calls.push(["write", ...args]); },
        addFieldInfosToRef(...args) { calls.push(["fields", ...args]); },
      });
      analyzer.propagateObjectLiteralFields(literal, [
        { kind: "local", function: "f", path: "result" }, { kind: "module", file: "fixture.ts", path: "alias" },
      ], { info: { key: "f" } }, { filepath: "fixture.ts", start_line: 1, end_line: 1 });
      return calls;
    }
    assert.deepEqual(run(FlowAnalyzer), run(formal.FlowAnalyzer), code);
  }
});

const programs = {
  module: `import { model } from "./provider";
    const operations = { nested: { run: model }, run: model };
    const { run: alias } = operations;
    const table = { ...operations, other: { action: model } };
    export async function run() { return await alias(); }`,
  arguments: `import { model } from "./provider";
    async function consume(options) { return await options.nested.run(); }
    export async function run() { const options = { nested: { run: model } }; return consume(options); }`,
  literals: `import { model } from "./provider";
    async function consume(options) { return await options.deep.run(); }
    export async function run() { return consume({deep: {run: model}}); }`,
  callbacks: `import { model } from "./provider";
    function factory() { return { nested: { run: model } }; }
    export async function run() { const x = {...factory()}; return await x.nested.run(); }`,
  classes: `import { model } from "./provider";
    class Agent { action = model; async step() { const result = await this.action(); if(result) return result; } }
    export async function run() { return new Agent().step(); }`,
  destructuring: `import { model } from "./provider";
    export async function run() { const table = { action: model }; const { action = model, ...rest } = table;
      const [first] = [action]; const result = await first(); return result; }`,
  aliases: `import { model } from "./provider";
    function wrap(fn) { return fn; }
    export async function run() { const callbacks = [model, wrap(model)]; return await callbacks[0](); }`,
  channel: `import { model } from "./provider";
    class Bus { emit(name, value) {} on(name, handler) {} }
    export async function run() { const bus = new Bus(); bus.on("value", value => value.text);
      const output = await model(); bus.emit("value", output); return output; }`,
  readPaths: `import { model } from "./provider";
    const storage = { nested: { action: model } };
    export async function run(options = storage) {
      const alias = options.nested;
      const { action = storage.nested.action } = alias;
      const output = await action();
      return output?.text ?? String(output);
    }`,
  computedChannel: `import { model } from "./provider";
    class Bus { emit(name, value) {} on(name, handler) {} }
    function consume(bus: Bus) { bus["on"]("value", value => value?.text); }
    export async function run() {
      const bus = new Bus(); consume(bus); bus["emit"]("value", await model());
    }`,
  paramFields: `import { model } from "./provider";
    function consume(options) { return options.nested.action(); }
    function forward(input) { return consume(input); }
    export function run() { return forward({ nested: { action: model } }); }`,
  expressionMerges: `import { model } from "./provider";
    export async function run(flag) {
      const output = await model();
      const text = \`prefix \${output}\`;
      const chosen = flag ? output : null;
      const values = [output, chosen];
      if (output && chosen) return { text, values, value: output.text };
      return typeof output === "string" ? output.length : 0;
    }`,
  declarationKinds: `import OpenAI from "openai";
    export interface Worker { invoke(): Promise<unknown>; }
    export type Alias = Worker;
    const Parent = class { client = new OpenAI(); };
    export default class Agent extends Parent implements Worker {
      async invoke(client = this.client) { return client.responses.create({input: "fixture"}); }
    }
    export async function run(worker: Alias = new Agent()) {
      const result = await worker.invoke();
      if (result) return result;
    }`,
  transports: `import { request } from "undici";
    export async function run() {
      const options = {method: "POST", body: JSON.stringify({input: "fixture"})};
      const first = await fetch("https://api.openai.com/v1/responses", options);
      const second = await request("https://api.openai.com/v1/chat/completions", options);
      return { first, second };
    }`,
};
for (const [name, source] of Object.entries(programs)) {
  for (const mode of ["block_only", "control-dependence-direct", "control-dependence-recursive"]) {
    for (const maxIterations of [1, 2, 120]) {
      test(`field-flow payload matches formal: ${name}/${mode}/${maxIterations}`, { skip: !enabled }, t => {
        const root = fs.mkdtempSync(path.join(os.tmpdir(), "artifact-flow-refactor-"));
        t.after(() => fs.rmSync(root, { recursive: true, force: true }));
        fs.writeFileSync(path.join(root, "provider.ts"), 'import OpenAI from "openai"; export async function model() { return new OpenAI().responses.create({input:"fixture"}); }');
        fs.writeFileSync(path.join(root, "agent.ts"), source);
        const args = { ts, root, files: ["provider.ts", "agent.ts"], project: "fixture",
          sourceRules: typescriptBoundaries(), options: { controlDependenceMode: mode, maxIterations } };
        const actual = analyzedRun(FlowAnalyzer, args);
        const expected = analyzedRun(formal.FlowAnalyzer, args);
        assert.deepEqual(actual.payload, regionPayload(expected.payload));
        assert.deepEqual(actual.events, expected.events);
        assert.deepEqual(actual.facts, formalFactState(expected.facts));
      });
    }
  }
}
