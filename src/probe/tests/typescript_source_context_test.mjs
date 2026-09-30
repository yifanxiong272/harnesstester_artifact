import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { formalRoot, formalModule as formal } from "./typescript_support.mjs";

import {
  buildTargetPacket,
  existingTestContexts,
} from "../typescript/input/target_packets.mjs";
import { publicTargetRoutes } from "../typescript/input/public_routes.mjs";
import { probeConstraints } from "../typescript/input/constraints.mjs";
import { moduleContracts } from "../typescript/input/module_contracts.mjs";
import {
  loadTypeScript,
  parseSource,
  scriptKindForPath,
  walkAst,
} from "../typescript/support/typescript.mjs";
import {
  loadTargetUnits,
  sourceFileIndex,
} from "../typescript/input/target_units.mjs";
import { promptPacket } from "../typescript/prompt/prompts.mjs";
import {
  parseContextRequests,
  resolveContextRequests,
  projectTracebackContext,
} from "../typescript/prompt/context.mjs";

function packetEvidence(packet) {
  const { packet_id, case_id, revision, repository_url, ...evidence } = packet;
  return evidence;
}

test("context parsing and retrieval default to one item and allow an explicit larger batch", (t) => {
  const projectRoot = fs.mkdtempSync(path.join(os.tmpdir(), "probe-context-cap-"));
  t.after(() => fs.rmSync(projectRoot, { recursive: true }));
  fs.mkdirSync(path.join(projectRoot, "src"));
  const requests = ["first", "second"].map((name) => {
    const filepath = `src/${name}.ts`;
    fs.writeFileSync(path.join(projectRoot, filepath), `export const ${name} = 1;`);
    return { kind: "module_context", filepath, qualname: "", reason: "" };
  });
  assert.deepEqual(parseContextRequests({ requests }).requests, requests.slice(0, 1));
  assert.deepEqual(parseContextRequests({ requests }, { maxRequests: 2 }).requests, requests);
  const args = { projectRoot, sourceRoots: ["src"], requests };
  const single = resolveContextRequests(args);
  assert.equal(single.max_requests, 1);
  assert.equal(single.requests.length, 1);
  const batch = resolveContextRequests({ ...args, maxRequests: 2 });
  assert.equal(batch.requests.length, 2);
  assert.ok(batch.requests.every((request) => request.status === "found"));
});

test("AST walker preserves order, subtree pruning, and exceptions", () => {
  const shared = { name: "shared" };
  const root = {
    name: "root",
    children: [
      { name: "first", children: [shared] },
      { name: "second", children: [shared] },
      { name: "last" },
    ],
  };
  const ts = {
    forEachChild(node, visit) {
      for (const child of node.children || []) {
        const result = visit(child);
        if (result) return result;
      }
    },
  };
  for (const result of [undefined, null, 0, true, "continue"]) {
    const visited = [];
    walkAst(ts, root, (node) => {
      visited.push(node.name);
      return node.name === "first" ? false : result;
    });
    assert.deepEqual(visited, ["root", "first", "second", "shared", "last"]);
  }
  const failure = new Error("visitor failed");
  const visited = [];
  assert.throws(
    () =>
      walkAst(ts, root, (node) => {
        visited.push(node.name);
        if (node.name === "first") throw failure;
      }),
    (error) => error === failure,
  );
  assert.deepEqual(visited, ["root", "first"]);
});

test(
  "AST walker matches inline compiler traversal on source syntax",
  { skip: !process.env.PROBE_TEST_NODE_MODULES },
  (t) => {
    const projectRoot = fixture(t);
    const ts = loadTypeScript(projectRoot);
    const tree = parseSource(ts, "counter.ts", source);
    const inline = (root, visitor) => {
      const visit = (node) => {
        if (visitor(node) === false) return;
        ts.forEachChild(node, visit);
      };
      visit(root);
    };
    for (const prune of [
      () => false,
      ts.isCallExpression,
      ts.isFunctionDeclaration,
      ts.isClassDeclaration,
      ts.isReturnStatement,
      ts.isArrowFunction,
      ts.isIdentifier,
    ]) {
      const record = (traverse) => {
        const nodes = [];
        traverse(tree, (node) => {
          nodes.push(node);
          if (prune(node)) return false;
        });
        return nodes;
      };
      const actual = record((root, visitor) => walkAst(ts, root, visitor));
      const expected = record(inline);
      assert.equal(actual.length, expected.length);
      actual.forEach((node, index) => assert.equal(node, expected[index]));
    }
  },
);

test(
  "source syntax selection preserves extensions and invalid-input errors",
  { skip: !formalRoot },
  async () => {
    const expected = await formal("support/typescript_loader.mjs");
    const ts = { ScriptKind: { JS: 1, JSX: 2, TS: 3, TSX: 4 } };
    const capture = (select, file) => {
      try {
        return { value: select(file, ts) };
      } catch (error) {
        return { name: error.name, message: error.message };
      }
    };
    for (const file of [
      "file.ts",
      "file.TS",
      "file.tsx",
      "file.TsX",
      "file.js",
      "file.JS",
      "file.jsx",
      "file.JsX",
      "file.d.ts",
      "file.mts",
      "file.mjs",
      "file.cjs",
      "file.j\u017f",
      ".jsx",
      "file.js/entry",
      "file.",
      "",
      "/",
      null,
      1,
      {},
    ])
      assert.deepEqual(
        capture(scriptKindForPath, file),
        capture(expected.scriptKindForPath, file),
      );
  },
);

test(
  "empty or disabled context requests preserve the early return",
  { skip: !formalRoot },
  async () => {
    const expected = await formal("prompt/context.mjs");
    for (const requests of [
      undefined,
      null,
      false,
      {},
      "",
      [],
      [{ filepath: "src/counter.ts", kind: "module_context" }],
    ]) {
      for (const maxRequests of [-1, 0, 2]) {
        if (Array.isArray(requests) && requests.length && maxRequests > 0)
          continue;
        const args = {
          projectRoot: null,
          sourceRoots: [],
          requests,
          maxRequests,
          maxTotalLines: 17,
          source: "fixture",
        };
        assert.equal(
          JSON.stringify(resolveContextRequests(args)),
          JSON.stringify(expected.resolveContextRequests({ maxRequests: 1, ...args })),
        );
      }
    }
  },
);

const source = `import { identity } from "./base.js";
export { identity as same } from "./base.js";
export const LIMIT = 3;
const increment = (value: number) => identity(value) + 1;
export function advance(value: number) {
  function nested() { return increment(value); }
  return nested();
}
export class Counter {
  total = 0;
  constructor() { this.total = 0; }
  static start() { return increment(0); }
  get value() { return this.total; }
  set value(value: number) { this.total = value; }
  async step() { this.total = increment(this.total); return this.total; }
  private hidden() { return this.total; }
  #private() { return this.total; }
}
export interface Options { amount: number }
export type Amount = number;
export enum State { Ready, Done }
export const helper = { step: (value: number) => increment(value) };
export const factory = () => new Counter();
const indirect = ((value: number) => advance(value)) satisfies (value: number) => number;
export { indirect as alias };
export default Counter;
`;

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-source-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const files = {
    "package.json": '{"type":"module"}',
    "src/counter.ts": source,
    "src/base.ts":
      "export function identity(value: number) { return value; }\n",
    "src/empty.ts": "",
    "src/objects.ts": `const nested = { group: { run: (x: number) => x + 1 } };
export { nested };
export default {
  run(x: number) { return x + 1; },
  step: (x: number) => x + 1,
  group: { run: (x: number) => x + 1 },
};
`,
    "src/typed.d.ts": "declare const value: number;\n",
    "src/counter.test.ts":
      'import { advance } from "./counter.js";\n' +
      "// padding\n".repeat(900) +
      'test("advance", () => { expect(advance(0)).toBe(1); });\n',
    "src/counter.spec.ts": "assert(true);\n",
    "test/alias.test.ts": 'const counter = require("../src/counter.js");\n',
    "tests/another.test.ts": 'const mod = import("../src/counter");\n',
    "elsewhere.ts": "const SECRET = 1;\n",
  };
  for (const [name, text] of Object.entries(files)) {
    const file = path.join(root, name);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, text);
  }
  if (process.env.PROBE_TEST_NODE_MODULES)
    fs.symlinkSync(
      process.env.PROBE_TEST_NODE_MODULES,
      path.join(root, "node_modules"),
      "dir",
    );
  return root;
}

test(
  "export contract records and limits match formal",
  { skip: !formalRoot },
  async (t) => {
    const projectRoot = fixture(t);
    const expected = await formal("input/module_contracts.mjs");
    const filepath = "src/exports.ts";
    const exports = [
      "export default function () { return 1; }",
      "export default class { run() { return 1; } }",
      "export const first = 1, second = 2; export const { item } = { item: 1 };",
      "export const [first, second] = [1, 2];",
      "export declare namespace Group { function value(): number; }",
      "export type Value = number; export interface Shape { value: number }; export enum State { Ready }",
      'export { value as renamed } from "./base"; export * from "./base"; export * as group from "./base";',
      'export { type Value } from "./base"; export type * from "./base";',
      "const value = 1; export { value }; export = value;",
      Array.from({ length: 100 }, (_, i) => `export const v${i} = ${i};`).join(
        "\n",
      ),
    ];
    for (const text of exports) {
      fs.writeFileSync(path.join(projectRoot, filepath), text);
      for (const generatedTestRoots of [
        [],
        ["test/generated/"],
        ["../invalid", "custom/probes"],
        ["test/./generated", "test/generated/", "test\\generated"],
        Array.from({ length: 8 }, (_, i) => `test/group${i}`),
      ]) {
        for (const limit of [0, 1, 24]) {
          const options = { generatedTestRoots, limit };
          const files = [filepath, filepath, "src/missing.ts", "src/base.ts"];
          assert.equal(
            JSON.stringify(moduleContracts(projectRoot, files, options)),
            JSON.stringify(
              expected.moduleContracts(projectRoot, files, options),
            ),
          );
        }
      }
    }
  },
);

test(
  "module contracts keep first imports and skip unavailable files",
  { skip: !formalRoot },
  async (t) => {
    const projectRoot = fixture(t);
    const expected = await formal("input/module_contracts.mjs");
    fs.mkdirSync(path.join(projectRoot, "src/directory.ts"));
    const files = [
      "../outside.ts",
      "src/missing.ts",
      "src/directory.ts",
      "src/./base.ts",
      "src\\base.ts",
      "src/base.ts",
      "src/empty.ts",
      "src/counter.ts",
    ];
    for (const limit of [-1, 0, 1, 2, 24]) {
      const options = {
        limit,
        generatedTestRoots: [
          "test/./generated",
          "test/generated/",
          "test/other",
        ],
      };
      assert.equal(
        JSON.stringify(moduleContracts(projectRoot, files, options)),
        JSON.stringify(expected.moduleContracts(projectRoot, files, options)),
      );
    }
  },
);

test(
  "source lines and first-wins target identities match formal",
  { skip: !formalRoot },
  async (t) => {
    const projectRoot = fixture(t);
    const expected = await formal("input/target_units.mjs");
    const context = await formal("prompt/context.mjs");
    const filepath = "src/lines.ts";
    for (const text of [
      "",
      "one",
      "one\n",
      "one\r\ntwo\r\n",
      "\n\n",
      "one\rtwo",
      "one\r\n\n",
    ]) {
      fs.writeFileSync(path.join(projectRoot, filepath), text);
      const specs = [-2, 0, 1, 2, 10].flatMap((start_line) =>
        [-2, 0, 1, 2, 10].map((end_line) => ({
          filepath,
          start_line,
          end_line,
          qualname: `range-${start_line}-${end_line}`,
        })),
      );
      specs.push(
        {
          filepath,
          unit_id: "duplicate",
          start_line: 2,
          end_line: 2,
          qualname: "second",
        },
        {
          filepath,
          unit_id: "duplicate",
          start_line: 1,
          end_line: 1,
          qualname: "first",
        },
        {
          filepath,
          unit_id: "duplicate",
          start_line: 1,
          end_line: 1,
          qualname: "tied",
        },
      );
      const original = structuredClone(specs);
      const actual = loadTargetUnits(projectRoot, specs);
      assert.equal(
        JSON.stringify(actual),
        JSON.stringify(expected.loadTargetUnits(projectRoot, specs)),
      );
      assert.equal(
        actual.find((unit) => unit.unit_id === "duplicate").qualname,
        "first",
      );
      assert.deepEqual(specs, original);
      assert.deepEqual(
        sourceFileIndex(projectRoot, [filepath, filepath]),
        expected.sourceFileIndex(projectRoot, [filepath, filepath]),
      );
      for (const maxModuleLines of [0, 1, 90]) {
        const args = {
          projectRoot,
          sourceRoots: ["src"],
          requests: [{ kind: "module_context", filepath }],
          maxModuleLines,
        };
        assert.deepEqual(
          resolveContextRequests(args),
          context.resolveContextRequests({ maxRequests: 1, ...args }),
        );
      }
    }
  },
);

for (const maxLines of [0, 3, 90]) {
  test(
    `nested symbol scope and ranges match formal: ${maxLines} lines`,
    { skip: !formalRoot },
    async (t) => {
      const projectRoot = fixture(t);
      const filepath = "src/scopes.ts";
      const text = `export function outer() {
  function inner() { const inside = 1; return inside; }
  class Local {
    constructor() { const built = 1; }
    get value() { return 1; }
    set value(n: number) { const changed = n; }
    run() {
      class Nested { run() { return 1; } }
      const callback = (n: number) => n;
      return callback(1);
    }
    ["a.b"]() { return 1; }
  }
  return new Local();
}
export default class { run() { const unnamed = 1; return unnamed; } }
const first = (n: number) => n, second = function (n: number) { return n; };
const { left, right } = { left: 1, right: 2 };
interface Options { value: number }
type Value = number;
enum Phase { Ready }
namespace Group { export function grouped() { return 1; } }
`;
      fs.writeFileSync(path.join(projectRoot, filepath), text);
      const expected = await formal("prompt/context.mjs");
      const requests = [
        ...["Local", "Local.Nested"].map((qualname) => [
          "class_definition",
          qualname,
        ]),
        ...[
          "outer",
          "inner",
          "Local.constructor",
          "Local.value",
          "Local.run",
          "Local.Nested.run",
          "Local.a.b",
          "run",
          "first",
          "second",
          "grouped",
        ].map((qualname) => ["function_definition", qualname]),
        ...[
          "inside",
          "Local.built",
          "Local.changed",
          "Local.callback",
          "unnamed",
          "first",
          "second",
          "{ left, right }",
          "Options",
          "Value",
          "Phase",
        ].map((qualname) => ["symbol_definition", qualname]),
        ["function_definition", "Local.callback"],
        ["function_definition", "outer.inner"],
        ["function_definition", "Group.grouped"],
      ].map(([kind, qualname]) => ({ kind, qualname, filepath }));
      const args = {
        projectRoot,
        sourceRoots: ["src"],
        requests,
        maxRequests: requests.length,
        maxTotalLines: 1000,
        maxModuleLines: maxLines,
      };
      const actual = resolveContextRequests(args);
      assert.equal(
        JSON.stringify(actual),
        JSON.stringify(expected.resolveContextRequests({ maxRequests: 1, ...args })),
      );
      assert.ok(
        actual.requests.filter((item) => item.status === "found").length >= 20,
      );
      // Every source line exercises owner selection, including overlapping getter/setter ranges.
      for (let line = 1; line < text.split("\n").length; line++) {
        const traceArgs = {
          projectRoot,
          sourceRoots: ["src"],
          failureText: `Error: fixture\n    at run (${path.join(projectRoot, filepath)}:${line}:1)`,
          maxLines,
        };
        assert.deepEqual(
          projectTracebackContext(traceArgs),
          expected.projectTracebackContext(traceArgs),
        );
      }
    },
  );
}

for (const linked of [false, true]) {
  test(
    `unique test context ranking matches formal: links ${linked}`,
    { skip: !formalRoot },
    async (t) => {
      const projectRoot = fixture(t);
      for (const excluded of ["node_modules", "dist", "coverage", ".git"]) {
        const directory = path.join(projectRoot, "tests", excluded);
        fs.mkdirSync(directory, { recursive: true });
        fs.writeFileSync(
          path.join(directory, "counter.test.ts"),
          'import { advance } from "../../src/counter.js";\n',
        );
      }
      if (linked) {
        fs.symlinkSync("../src", path.join(projectRoot, "tests/linked"), "dir");
        fs.symlinkSync(
          "../src/counter.test.ts",
          path.join(projectRoot, "test/copy.test.ts"),
        );
      }
      const expected = await formal("input/target_packets.mjs");
      const targets = units.map((unit, index) => ({
        ...unit,
        unit_id: `u${index}`,
      }));
      for (const maxFiles of [-1, 0, 1, 2, 20]) {
        for (const maxChars of [0, 1, 20, 7000]) {
          const options = { maxFiles, maxChars };
          assert.deepEqual(
            existingTestContexts(projectRoot, targets, options),
            expected.existingTestContexts(projectRoot, targets, options),
          );
        }
      }
    },
  );
}

const units = [
  ["advance", 5, 8, "function"],
  ["advance.nested", 6, 6, "function"],
  ["increment", 4, 4, "function"],
  ["Counter", 9, 18, "class"],
  ["Counter.constructor", 11, 11, "method"],
  ["Counter.start", 12, 12, "method"],
  ["Counter.value", 13, 13, "method"],
  ["Counter.step", 15, 15, "method"],
  ["Counter.hidden", 16, 16, "method"],
  ["helper.step", 22, 22, "function"],
  ["factory", 23, 23, "function"],
  ["indirect", 24, 24, "function"],
].map(([qualname, start_line, end_line, kind]) => ({
  filepath: "src/counter.ts",
  qualname,
  start_line,
  end_line,
  kind,
}));

test(
  "ordered import indexes preserve statement priority and the packet limit",
  { skip: !formalRoot },
  async (t) => {
    const projectRoot = fixture(t);
    const expected = await formal("input/target_packets.mjs");
    for (const count of [79, 80, 81]) {
      const imports = Array.from({ length: count }, (_, i) =>
        [`import "./item${i}.js";`, `export * from "./item${i}.js";`].join(
          "\n",
        ),
      ).join("\n");
      fs.writeFileSync(path.join(projectRoot, "src/imports.ts"), imports);
      const args = {
        project: "fixture",
        caseId: "imports",
        revision: "before",
        strategy: "target_probe_ldh",
        repositoryUrl: "",
        projectRoot,
        constraints: probeConstraints(),
        testCommand: ["vitest", "run"],
        patchTargets: {
          target_units: [{ filepath: "src/imports.ts", kind: "file" }],
        },
      };
      const formalPacket = expected.buildTargetPacket(args);
      delete formalPacket.packet_id;
      const actual = buildTargetPacket({ ...args, targetUnits: args.patchTargets.target_units });
      assert.equal(JSON.stringify(actual), JSON.stringify(packetEvidence(formalPacket)));
      assert.equal(actual.module_imports.length, Math.min(count, 80));
      assert.ok(
        actual.module_imports.every((item) =>
          item.statement.startsWith("import "),
        ),
      );
    }
    const targets = [
      { unit_id: "first", filepath: "src/counter.ts" },
      { unit_id: "first", filepath: "src/counter.js" },
      { unit_id: "second", filepath: "src/counter.ts" },
      { unit_id: "base", filepath: "src/base.ts" },
    ];
    for (const selected of [targets, [...targets].reverse()]) {
      assert.equal(
        JSON.stringify(
          existingTestContexts(projectRoot, selected, { maxFiles: 20 }),
        ),
        JSON.stringify(
          expected.existingTestContexts(projectRoot, selected, {
            maxFiles: 20,
          }),
        ),
      );
    }
  },
);

test(
  "module reference syntax preserves packet and existing-test selection",
  { skip: !formalRoot },
  async (t) => {
    const projectRoot = fixture(t);
    const expected = await formal("input/target_packets.mjs");
    const statements = [
      'import { identity } from "./base.js";',
      'import type { Value } from "./base.js";',
      'import "./base.js";',
      'export { identity } from "./base.js";',
      'export type { Value } from "./base.js";',
      'export * as base from "./base.js";',
      'import base = require("./base.js");',
      'const base = require("./base.js");',
      'const base = import("./base.js");',
      "const base = require(`./base.js`);",
      "const base = import(`./base.js`);",
      "const base = require(`./${name}`);",
      "const base = import(`./${name}`);",
      'const base = object.require("./base.js");',
      'require(); import(""); require("");',
      'import ""; export * from "";',
      'function nested() { return import("./base.js"); }',
      'require("./base.js"); require("./base.js");',
    ];
    for (const statement of [
      ...statements,
      statements.join("\n"),
      statements.toReversed().join("\n"),
    ]) {
      fs.writeFileSync(path.join(projectRoot, "src/references.ts"), statement);
      fs.writeFileSync(
        path.join(projectRoot, "test/reference.test.ts"),
        statement.replaceAll("./base.js", "../src/base.js"),
      );
      const args = {
        project: "fixture",
        caseId: "references",
        revision: "before",
        strategy: "target_probe_ldh",
        repositoryUrl: "",
        projectRoot,
        constraints: probeConstraints(),
        testCommand: ["vitest", "run"],
        patchTargets: {
          target_units: [
            { filepath: "src/references.ts", kind: "file" },
            { filepath: "src/base.ts", kind: "file" },
          ],
        },
      };
      const formalPacket = expected.buildTargetPacket(args);
      delete formalPacket.packet_id;
      assert.deepEqual(
        buildTargetPacket({ ...args, targetUnits: args.patchTargets.target_units }),
        packetEvidence(formalPacket), statement,
      );
    }
  },
);

for (const strategy of [
  "target_probe_ldh",
  "target_probe_contract_agnostic",
]) {
  test(
    `source packet matches formal: ${strategy}`,
    { skip: !formalRoot },
    async (t) => {
      const projectRoot = fixture(t);
      const args = {
        project: "fixture",
        caseId: "counter",
        revision: "before",
        strategy,
        repositoryUrl: "",
        projectRoot,
        constraints: probeConstraints(),
        testCommand: ["vitest", "run"],
        patchTargets: {
          target_units: [
            ...units,
            units[0],
            { filepath: "src/base.ts", kind: "file" },
            ...[
              ["nested.group.run", 1],
              ["default.run", 4],
              ["default.step", 5],
              ["default.group.run", 6],
            ].map(([qualname, line]) => ({
              filepath: "src/objects.ts",
              qualname,
              start_line: line,
              end_line: line,
              kind: "function",
            })),
          ],
        },
      };
      const expected = (
        await formal("input/target_packets.mjs")
      ).buildTargetPacket(args);
      const actual = buildTargetPacket({ ...args, targetUnits: args.patchTargets.target_units });
      const formalPrompts = await formal("prompt/prompts.mjs");
      // The fixture factory returns an instance, which has no static start method.
      const staticTarget = expected.public_target_routes.targets.find(
        (target) => target.target_unit_id.includes("::Counter.start@"),
      );
      const invalid = staticTarget.entrypoints.filter((route) => route.invocation_kind === "factory_method");
      assert.equal(invalid.length, 1);
      assert.deepEqual(invalid[0].call_path, ["factory", "Counter.start"]);
      staticTarget.entrypoints = staticTarget.entrypoints.filter((route) => route.invocation_kind !== "factory_method");
      const increment = expected.public_target_routes.targets.find((target) => target.target_unit_id.includes("::increment@"));
      assert.deepEqual(increment.entrypoints[3].call_path, ["factory", "Counter.start", "increment"]);
      const step = expected.public_target_routes.targets.find((target) => target.target_unit_id.includes("::Counter.step@"));
      const replacement = { ...step.entrypoints[0], call_path: ["Counter.step", "increment"] };
      replacement.entrypoint_id = `entrypoint-${crypto.createHash("sha1").update(JSON.stringify([
        replacement.filepath, increment.target_unit_id, replacement.import_kind,
        replacement.export_name, replacement.member_path, replacement.call_path, 3,
      ])).digest("hex").slice(0, 12)}`;
      increment.entrypoints[3] = replacement;
      assert.deepEqual(actual.public_target_routes, expected.public_target_routes);
      for (const includeModuleImports of [false, true]) {
        const options = { includeModuleImports };
        assert.equal(
          JSON.stringify(promptPacket(actual, options)),
          JSON.stringify(formalPrompts.promptPacket(expected, options)),
        );
      }
      assert.equal(Object.hasOwn(actual, "packet_id"), false);
      delete expected.packet_id;
      assert.deepEqual(actual, packetEvidence(expected));
      assert.equal(expected.existing_tests.length, 2);
      assert.ok(expected.public_target_routes.targets.length);
    },
  );
}

for (const reverseTargets of [false, true]) {
  test(
    `shared call graph matches formal: reverse targets ${reverseTargets}`,
    { skip: !formalRoot },
    async (t) => {
      const projectRoot = fixture(t);
      const definitions = [
        ["leaf", "function leaf(value: number) { return value; }"],
        ["left", "function left(x: number) { return leaf(x) + right(x); }"],
        ["right", "function right(x: number) { return leaf(x) + left(x); }"],
        ...["first", "second", "third", "fourth", "fifth", "sixth"].map(
          (name) => [
            name,
            `export function ${name}(x: number) { return left(x); }`,
          ],
        ),
        ["aliases", "function aliases(x: number) { return leaf(x); }"],
        [
          "outer",
          "export function outer(x: number) { return [x].map(y => (() => leaf(y))()); }",
        ],
        [
          "one",
          "export const one = (x: number) => leaf(x), two = (value: string) => leaf(value.length);",
        ],
        [
          "Public.hidden",
          "class Public { run(x: number) { return this.hidden(x); } private hidden(x: number) { return leaf(x); } }",
        ],
        ["factory", "export const factory = () => new Public();"],
      ];
      const filepath = "src/routes.ts";
      const text =
        definitions.map(([, code]) => code).join("\n") +
        "\nexport { aliases as a, aliases as b, aliases as c, aliases as d, aliases as e };\nexport default aliases;\n";
      fs.writeFileSync(path.join(projectRoot, filepath), text);
      const targets = definitions.map(([qualname], index) => ({
        unit_id: `u${index}`,
        filepath,
        qualname,
        start_line: index + 1,
        end_line: index + 1,
        kind: "function",
      }));
      targets.push({ ...targets[11], unit_id: "two", qualname: "two" });
      targets.push({ ...targets[0], unit_id: "repeated-leaf" });
      if (reverseTargets) targets.reverse();
      const expected = await formal("input/public_routes.mjs");
      const actual = publicTargetRoutes(projectRoot, targets);
      assert.deepEqual(
        actual,
        expected.publicTargetRoutes(projectRoot, targets),
      );
      assert.ok(
        actual.targets.some((target) => target.entrypoints.length === 4),
      );
      for (const [index, unit] of targets.entries()) {
        assert.deepEqual(publicTargetRoutes(projectRoot, [unit]).targets, [
          actual.targets[index],
        ]);
      }
    },
  );
}

for (const maxLines of [-1, 0, 1, 5, 90]) {
  test(
    `exact and traceback context matches formal: ${maxLines} lines`,
    { skip: !formalRoot },
    async (t) => {
      const projectRoot = fixture(t);
      const expected = await formal("prompt/context.mjs");
      const requests = [
        ["module_context", "src/counter.ts", ""],
        ["module_context", "src/counter.ts", "missing"],
        ["class_definition", "src/counter.ts", "Counter"],
        ...[
          "advance",
          "nested",
          "increment",
          "Counter.constructor",
          "Counter.step",
          "Counter.value",
          "factory",
        ].map((name) => ["function_definition", "src/counter.ts", name]),
        ...["LIMIT", "Options", "Amount", "State", "missing"].map((name) => [
          "symbol_definition",
          "src/counter.ts",
          name,
        ]),
        ...[
          "src/empty.ts",
          "src/missing.ts",
          "elsewhere.ts",
          "../outside.ts",
          "/absolute.ts",
          "",
        ].map((file) => ["module_context", file, ""]),
        ["symbol_definition", "src/typed.d.ts", "value"],
        ["module_context", "src/typed.d.ts", "value"],
        ["unsupported", "src/counter.ts", ""],
      ].map(([kind, filepath, qualname]) => ({
        kind,
        filepath,
        qualname,
        reason: "inspect",
      }));
      for (const request of requests) {
        const args = {
          projectRoot,
          sourceRoots: ["src"],
          requests: [request],
          maxModuleLines: maxLines,
        };
        assert.deepEqual(
          resolveContextRequests(args),
          expected.resolveContextRequests({ maxRequests: 1, ...args }),
        );
      }
      const batch = {
        projectRoot,
        sourceRoots: ["src"],
        requests,
        maxRequests: requests.length,
        maxTotalLines: maxLines,
      };
      assert.deepEqual(
        resolveContextRequests(batch),
        expected.resolveContextRequests(batch),
      );
      for (const line of [1, 6, 11, 13, 15, 25, 99]) {
        const args = {
          projectRoot,
          sourceRoots: ["src"],
          maxLines,
          failureText: `Error: fixture\n    at step (${projectRoot}/src/counter.ts:${line}:5)\n`,
        };
        assert.deepEqual(
          projectTracebackContext(args),
          expected.projectTracebackContext(args),
        );
      }
    },
  );
}
