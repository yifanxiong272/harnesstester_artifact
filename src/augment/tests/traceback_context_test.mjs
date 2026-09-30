import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import test from "node:test";

import { tracebackContextFromFailure } from "../typescript/prompt/context.mjs";

const dependencies = process.env.ARTIFACT_TEST_NODE_MODULES;
const require = createRequire(dependencies ? path.join(dependencies, "../package.json") : import.meta.url);
const typescript = require("typescript");

function fixture(t, lines) {
  const projectRoot = fs.mkdtempSync(path.join(os.tmpdir(), "augment-traceback-"));
  t.after(() => fs.rmSync(projectRoot, { recursive: true, force: true }));
  fs.mkdirSync(path.join(projectRoot, "src"));
  fs.writeFileSync(path.join(projectRoot, "src/target.ts"), lines.join("\n"));
  return {
    projectRoot,
    read(line) {
      return tracebackContextFromFailure({
        projectRoot, typescript, sourceRoots: ["src"],
        failure: { failure_output: `Error: fixture\n    at run (${projectRoot}/src/target.ts:${line}:3)` },
      });
    },
  };
}

const declarations = [
  { name: "function", prefix: ["export function run() {"], suffix: ["}"], qualname: "run" },
  { name: "method", prefix: ["export class Worker {", "  run() {"], suffix: ["  }", "}"], qualname: "Worker.run" },
  { name: "constructor", prefix: ["export class Worker {", "  constructor() {"], suffix: ["  }", "}"], qualname: "Worker.constructor" },
  { name: "arrow", prefix: ["export const run = () => {"], suffix: ["};"], qualname: "run" },
  { name: "nested function", prefix: ["export function outer() {", "  function run() {"], suffix: ["  }", "  return run();", "}"], qualname: "outer.run" },
];

for (const { name, prefix, suffix, qualname } of declarations) {
  for (const length of [3, 90, 200]) {
    test(`traceback includes every body line: ${name}, ${length} lines`, (t) => {
      const lines = [
        ...prefix,
        ...Array.from({ length }, (_, i) => `  step(); // body ${i + 1}`),
        ...suffix,
      ];
      const { read } = fixture(t, lines);
      const declarationStart = prefix.length;
      const declarationEnd = prefix.length + length + 1;
      const originalStart = Math.max(1, declarationStart - 1);
      const originalEnd = Math.min(lines.length, declarationEnd + 1, originalStart + 89);
      for (let line = declarationStart + 1; line < declarationEnd; line += 1) {
        const records = read(line);
        assert.equal(records.length, 1);
        const [record] = records;
        assert.equal(record.status, "found");
        assert.equal(record.request.qualname, qualname);
        assert.equal(record.request.reason, `src/target.ts:${line}`);
        assert.ok(record.start_line <= line && line <= record.end_line,
          `frame ${line} omitted from ${record.start_line}-${record.end_line}`);
        assert.ok(record.end_line - record.start_line + 1 <= 90);
        assert.equal(record.code_excerpt,
          lines.slice(record.start_line - 1, record.end_line)
            .map((text, index) => `${String(record.start_line + index).padStart(5, " ")} | ${text}`)
            .join("\n"));
        if (line <= originalEnd) {
          assert.deepEqual([record.start_line, record.end_line], [originalStart, originalEnd]);
        } else {
          const expectedStart = Math.max(declarationStart,
            Math.min(line - 45, declarationEnd - 89));
          assert.deepEqual([record.start_line, record.end_line],
            [expectedStart, Math.min(declarationEnd, expectedStart + 89)]);
        }
      }
    });
  }
}

test("module-level traceback windows retain file bounds and eight lines of context", (t) => {
  const lines = Array.from({ length: 200 }, () => "step();");
  const { read } = fixture(t, lines);
  for (const line of [1, 100, 200]) {
    const [record] = read(line);
    assert.equal(record.request.qualname, "");
    assert.deepEqual([record.start_line, record.end_line],
      [Math.max(1, line - 8), Math.min(lines.length, line + 8)]);
  }
});

test("traceback keeps three distinct source frames in order", (t) => {
  const lines = ["export function run() {", ...Array(200).fill("  step();"), "}"];
  const { projectRoot } = fixture(t, lines);
  const failure_output = [180, 180, 170, 160, 150]
    .map(line => `    at run (${projectRoot}/src/target.ts:${line}:3)`).join("\n");
  const records = tracebackContextFromFailure({
    projectRoot, typescript, sourceRoots: ["src"], failure: { failure_output },
  });
  assert.deepEqual(records.map(record => record.request.reason),
    [180, 170, 160].map(line => `src/target.ts:${line}`));
  for (const [index, line] of [180, 170, 160].entries()) {
    assert.ok(records[index].start_line <= line && line <= records[index].end_line);
  }
});
