import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import test from "node:test";

import * as context from "../typescript/prompt/context.mjs";

const root = process.env.AUGMENT_FORMAL_ROOT || process.env.PROBE_FORMAL_ROOT;
const formal = root ? await import(pathToFileURL(path.join(root, "src/common/test_augmentF/TS/context.mjs"))) : null;
const dependencies = process.env.ARTIFACT_TEST_NODE_MODULES || process.env.PROBE_TEST_NODE_MODULES;
const require = createRequire(dependencies ? path.join(dependencies, "../package.json") : import.meta.url);
const typescript = require("typescript");
const source = `export const VALUE = 1;
export class Counter {
  constructor(public value: number) {}
  step(amount: number) { return this.value + amount; }
  get current() { return this.value; }
}
export function outer() {
  function nested() { return 1; }
  return nested();
}
export function repeated(value: number): number;
export function repeated(value: string): string;
export function repeated(value: any) { return value; }
interface Duplicate { value: number; }
interface Duplicate { other: string; }
`;

function fixture(t) {
  const projectRoot = fs.mkdtempSync(path.join(os.tmpdir(), "augment-context-"));
  t.after(() => fs.rmSync(projectRoot, { recursive: true, force: true }));
  fs.mkdirSync(path.join(projectRoot, "src"));
  const files = {
    "counter.ts": source, "empty.ts": "", "broken.ts": "export function broken(\n",
    "long.test.ts": Array.from({ length: 400 }, (_, index) => `// ${index} ${"x".repeat(180)}`).join("\n"),
    "notes.txt": "text", "component.tsx": "export const View = () => <div />;\n",
  };
  for (const [file, text] of Object.entries(files)) fs.writeFileSync(path.join(projectRoot, "src", file), text);
  fs.symlinkSync("counter.ts", path.join(projectRoot, "src/alias.ts"));
  fs.symlinkSync(os.tmpdir(), path.join(projectRoot, "src/outside.ts"));
  return { projectRoot, typescript, objective: { filepath: "src/counter.ts" } };
}

for (const kind of ["module_context", "test_file_context", "class_definition", "function_definition", "symbol_definition", "export_surface", "unknown"]) {
  test(`context output matches formal: ${kind}`, { skip: !formal }, (t) => {
    const options = fixture(t);
    const requests = [];
    for (const filepath of [
      "src/counter.ts", "src/empty.ts", "src/long.test.ts", "src/broken.ts", "src/component.tsx",
      "src/notes.txt", "src/alias.ts", "src/outside.ts", "src/missing.ts", "src", "", "../outside.ts",
      "/absolute.ts", "C:/outside.ts", "src\\counter.ts", "src//counter.ts", "src/./counter.ts", "src/\0counter.ts",
    ]) {
      for (const [start_line, end_line] of [[undefined, undefined], [0, 0], [2, 1], [3, 10], [200, 300], [-2, 4], ["bad", "bad"]]) {
        requests.push({ kind, filepath, start_line, end_line, qualname: "Counter.step", reason: "fixture" });
      }
    }
    for (const qualname of ["Counter", "Counter.constructor", "Counter.current", "outer", "outer.nested", "VALUE", "repeated", "Duplicate", "missing", ""]) {
      requests.push({ kind, filepath: "src/counter.ts", qualname });
    }
    for (const request of requests) {
      assert.deepEqual(context.resolveContextRequests({ ...options, requests: [request] }), formal.resolveContextRequests({ ...options, requests: [request] }));
    }
  });
}

test("mixed context requests preserve budgets, deduplication and visible-span filtering", { skip: !formal }, (t) => {
  const options = fixture(t);
  const requests = [
    ...[1, 91, 181, 271, 361].map((start_line) => ({ kind: "module_context", filepath: "src/long.test.ts", start_line })),
    { kind: "test_file_context", filepath: "src/long.test.ts", start_line: 1 },
    { kind: "function_definition", filepath: "src/counter.ts", qualname: "outer" },
    { kind: "module_context", filepath: "src/counter.ts", start_line: 7, end_line: 9 },
  ];
  for (const batch of [requests, [...requests].reverse(), [...requests, ...requests]]) {
    for (const visibleContext of [[], [{ path: "src/long.test.ts", start_line: 1, end_line: 180 }]]) {
      assert.deepEqual(context.resolveContextRequests({ ...options, requests: batch, visibleContext }), formal.resolveContextRequests({ ...options, requests: batch, visibleContext }));
    }
  }
});

test("traceback context retains the same project frames and excerpts", { skip: !formal }, (t) => {
  const options = fixture(t);
  const failure = { failure_output: `Error: fixture\n    at step (${options.projectRoot}/src/counter.ts:4:3)\n    at nested (${options.projectRoot}/src/counter.ts:8:3)\n    at ${options.projectRoot}/src/broken.ts:1:1` };
  assert.deepEqual(context.tracebackContextFromFailure({ ...options, failure, sourceRoots: ["src"] }), formal.tracebackContextFromFailure({ ...options, failure, sourceRoots: ["src"] }));
});
