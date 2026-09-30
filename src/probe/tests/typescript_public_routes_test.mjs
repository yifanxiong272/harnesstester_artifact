/** Independent precision and retention checks for lightweight call bindings. */
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { publicTargetRoutes } from "../typescript/input/public_routes.mjs";
import { callResolver } from "../typescript/input/call_bindings.mjs";
import {
  loadTypeScript,
  parseSource,
  walkAst,
} from "../typescript/support/typescript.mjs";

const ready = { skip: !process.env.PROBE_TEST_NODE_MODULES };

function analyze(t, code, target = "hidden", line = 1) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-bindings-"));
  t.after(() => fs.rmSync(root, { recursive: true }));
  fs.writeFileSync(path.join(root, "package.json"), "{}");
  fs.symlinkSync(
    path.resolve(process.env.PROBE_TEST_NODE_MODULES),
    path.join(root, "node_modules"),
    "dir",
  );
  fs.writeFileSync(path.join(root, "subject.ts"), code);
  const routes = publicTargetRoutes(root, [
    {
      unit_id: "u1",
      filepath: "subject.ts",
      qualname: target,
      kind: "function",
      start_line: line,
      end_line: line,
    },
  ]);
  assert.equal(routes.available, true);
  return routes.targets[0].entrypoints;
}

const hidden = "function hidden() { return 1; }\n";
for (const definition of [
  "export function exposed(hidden: () => number) { return hidden(); }",
  "export function exposed({ hidden }: { hidden: () => number }) { return hidden(); }",
  "export function exposed(...hidden: any[]) { return hidden(); }",
  "export function exposed(hidden = () => 2) { return hidden(); }",
  "export function exposed() { const hidden = () => 2; return hidden(); }",
  "export function exposed() { function hidden() { return 2; } return hidden(); }",
  "export function exposed() { let hidden; return hidden(); }",
  "export function exposed() { { const hidden = () => 2; return hidden(); } }",
  "export function exposed(items: any[]) { for (const hidden of items) hidden(); }",
  "export function exposed() { try {} catch (hidden) { return hidden(); } }",
  "export function exposed(hidden: () => number) { return (() => hidden())(); }",
  "const other = { hidden() { return 2; } }; export function exposed() { return other.hidden(); }",
]) {
  test(
    `shadowed calls do not reach the module function: ${definition}`,
    ready,
    (t) => {
      assert.deepEqual(analyze(t, hidden + definition), []);
    },
  );
}

for (const definition of [
  "export function exposed() { return hidden(); }",
  "const alias = hidden; export function exposed() { return alias(); }",
  "const first = hidden; const alias = first; export function exposed() { return alias(); }",
  "export function exposed() { const alias = hidden; return alias(); }",
  "export function exposed() { return (hidden as (() => number))(); }",
  "export function exposed() { return hidden?.(); }",
  "const api = { hidden }; export function exposed() { return api.hidden(); }",
  "const api = { run: hidden }; export function exposed() { return api.run(); }",
  "const api = { hidden }; export function exposed() { return api['hidden'](); }",
  "const api = { hidden }; const key = 'hidden'; export function exposed() { return api[key](); }",
  "const api = { hidden }; const { hidden: alias } = api; export function exposed() { return alias(); }",
  "const api = { run() { return hidden(); } }; const alias = api.run; export function exposed() { return alias(); }",
  "class Agent { run() { return hidden(); } } const agent = new Agent(); export function exposed() { return agent.run(); }",
  "class Agent { static run() { return hidden(); } } const Alias = Agent; export function exposed() { return Alias.run(); }",
  "export function exposed(items: number[]) { return items.map(() => hidden()); }",
  "export function exposed() { { const hidden = () => 2; hidden(); } return hidden(); }",
  "export function exposed() { function nested() { return hidden(); } return nested(); }",
]) {
  test(
    `basic calls and aliases retain a public route: ${definition}`,
    ready,
    (t) => {
      assert.ok(
        analyze(t, hidden + definition).some(
          (route) => route.export_name === "exposed",
        ),
      );
    },
  );
}

for (const call of [
  "this.hidden()",
  "this['hidden']()",
  "(() => this.hidden())()",
  "const self = this; self.hidden()",
]) {
  test(`class receiver route: ${call}`, ready, (t) => {
    const routes = analyze(
      t,
      `export class Agent { private hidden() { return 1; } run() { ${call}; } }`,
      "Agent.hidden",
    );
    assert.ok(routes.some((route) => route.member_path.includes("run")));
  });
}

for (const declaration of [
  "export function exposed(other: any) { return other.hidden(); }",
  "interface Handler { hidden(): number; } export function exposed(other: Handler) { return other.hidden(); }",
  "export function exposed() { hidden = replacement; return hidden(); }",
]) {
  test(
    `uncertain calls retain existing candidates: ${declaration}`,
    ready,
    (t) => {
      assert.ok(
        analyze(t, hidden + declaration).some(
          (route) => route.export_name === "exposed",
        ),
      );
    },
  );
}

test("new aliases do not displace the four existing routes", ready, (t) => {
  const code =
    hidden +
    "const alias = hidden; export function added() { return alias(); }\n" +
    ["first", "second", "third", "fourth"]
      .map((name) => `export function ${name}() { return hidden(); }`)
      .join("\n");
  assert.deepEqual(
    analyze(t, code).map((route) => route.export_name),
    ["first", "second", "third", "fourth"],
  );
});

test(
  "an imported callable does not resolve to a same-named class method",
  ready,
  (t) => {
    const code =
      "class Other { hidden() { return 1; } }\n" +
      "import { remote as hidden } from './external'; export function exposed() { return hidden(); }";
    assert.deepEqual(analyze(t, code, "Other.hidden"), []);
  },
);

for (const factory of [
  "export function exposed(Agent: any) { return new Agent(); }",
  "export function exposed() { class Agent {} return new Agent(); }",
]) {
  test(
    `a shadowed constructor does not expose unrelated instance methods: ${factory}`,
    ready,
    (t) => {
      assert.deepEqual(
        analyze(
          t,
          "class Agent { run() { return 1; } }\n" + factory,
          "Agent.run",
        ),
        [],
      );
    },
  );
}

test(
  "factory aliases expose instance methods but not static methods",
  ready,
  (t) => {
    const code =
      "class Agent { run() { return 1; } static hidden() { return 2; } }\n" +
      "const Alias = Agent; export function exposed() { return new Alias(); }";
    assert.ok(
      analyze(t, code, "Agent.run").some(
        (route) => route.invocation_kind === "factory_method",
      ),
    );
    assert.deepEqual(analyze(t, code, "Agent.hidden"), []);
  },
);

for (const line of [1, 2, 3]) {
  test(`function overload retains the caller at line ${line}`, ready, (t) => {
    const code = [
      "function hidden(value: string): string;",
      "function hidden(value: number): number;",
      "function hidden(value: string | number) { return value; }",
      "export function exposed() { return hidden(1); }",
    ].join("\n");
    assert.ok(
      analyze(t, code, "hidden", line).some(
        (route) => route.export_name === "exposed",
      ),
    );
  });

  test(
    `private method overload retains the caller at line ${line + 1}`,
    ready,
    (t) => {
      const code = [
        "export class Agent {",
        "private hidden(value: string): string;",
        "private hidden(value: number): number;",
        "private hidden(value: string | number) { return value; }",
        "run() { return this.hidden(1); }",
        "}",
      ].join("\n");
      assert.ok(
        analyze(t, code, "Agent.hidden", line + 1).some((route) =>
          route.member_path.includes("run"),
        ),
      );
    },
  );
}

test(
  "resolution keeps ambiguous writes and alias cycles uncertain",
  ready,
  () => {
    const ts = loadTypeScript(
      path.dirname(process.env.PROBE_TEST_NODE_MODULES),
    );
    const source = parseSource(
      ts,
      "subject.ts",
      [
        "function first() {} function second() {}",
        "let alias = first; alias = second; alias();",
        "const cycleA = cycleB; const cycleB = cycleA; cycleA();",
      ].join("\n"),
    );
    const resolve = callResolver(ts, source);
    const values = [];
    walkAst(ts, source, (node) => {
      if (ts.isCallExpression(node)) values.push(resolve(node.expression));
    });
    assert.deepEqual(values, [undefined, undefined]);
  },
);
