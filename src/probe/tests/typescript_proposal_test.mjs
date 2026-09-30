import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { formalRoot, formalModule } from "./typescript_support.mjs";
import {
  parseProposalPartial,
  parseProbePlan,
  validateMinimizedCodeIsSubset,
} from "../typescript/prompt/proposal.mjs";
import {
  parseContextRequests,
  parseHarnessRepairDecision,
} from "../typescript/prompt/context.mjs";

test(
  "JSON response decoding preserves phase-specific errors",
  { skip: !formalRoot },
  async () => {
    const formalContext = await formalModule("prompt/context.mjs");
    const formalProposal = await formalModule("prompt/proposal.mjs");
    const capture = (parse, value) => {
      try {
        return { result: parse(value) };
      } catch (error) {
        return { error: [error.name, error.message] };
      }
    };
    for (const [actual, expected] of [
      [parseProbePlan, formalProposal.parseProbePlan],
      [parseProposalPartial, formalProposal.parseProposalPartial],
      [parseContextRequests, formalContext.parseContextRequests],
      [parseHarnessRepairDecision, formalContext.parseHarnessRepairDecision],
    ]) {
      for (const value of [
        undefined,
        null,
        false,
        0,
        [],
        {},
        { action: "retain_original" },
        { boundary_plan: [], exhausted_reason: "fixture" },
      ]) {
        const encoded = JSON.stringify(value);
        for (const wire of [
          value,
          encoded,
          `\`\`\`json\n${encoded}\n\`\`\``,
          `\`\`\`\n${encoded}\n\`\`\``,
        ]) {
          assert.deepEqual(capture(actual, wire), capture(expected, wire));
        }
      }
      for (const wire of [
        "",
        "{",
        "[]",
        '"text"',
        "null",
        "true",
        "```JSON\n{}\n```",
        "prefix {} suffix",
      ]) {
        assert.deepEqual(capture(actual, wire), capture(expected, wire));
      }
    }
  },
);

for (const phase of ["plan", "repair"]) {
  for (const limit of [0, 1, 2, 20]) {
    test(
      `context request parsing matches formal: ${phase}, limit ${limit}`,
      { skip: !formalRoot },
      async () => {
        const formal = await formalModule(
          `prompt/${phase === "plan" ? "proposal" : "context"}.mjs`,
        );
        const variants = [null, false, 0, "", "invalid", {}, []];
        const items = [null, false, 1, "request", [], {}, { kind: "unknown" }];
        for (const kind of [
          "module_context",
          "class_definition",
          "function_definition",
          "symbol_definition",
        ]) {
          for (const filepath of [
            null,
            "",
            "src/counter.ts",
            "../outside.ts",
            "/tmp/x.ts",
            "src\\counter.ts",
          ])
            items.push({ kind, filepath });
          items.push(
            { kind, filepath: " src/counter.ts ", qualname: " Counter " },
            { kind, filepath: 12, qualname: 3, reason: true },
          );
        }
        variants.push(
          ...items.map((item) => [item]),
          items,
          items.toReversed(),
        );
        const boundary = {
          boundary_id: "boundary-001",
          target_unit_ids: ["u1"],
          route: { entrypoint_id: "entrypoint-001" },
          probe: {
            test_intent: "advance once",
            activation_conditions: ["input is zero"],
          },
          invariant: {
            independent_oracle: "increments once",
            supporting_evidence: "arithmetic",
            expected_observation: "one",
            oracle_mode: "assertion",
          },
          bug_hypothesis: "increment differs",
        };
        const capture = (parse, value) => {
          try {
            return { result: parse(value) };
          } catch (error) {
            return { error: [error.name, error.message] };
          }
        };
        for (const value of variants) {
          const payload =
            phase === "plan"
              ? { boundary_plan: [boundary], context_requests: value }
              : { requests: value };
          const options =
            phase === "plan"
              ? { maxContextRequests: limit }
              : { maxRequests: limit };
          const actual =
            phase === "plan" ? parseProbePlan : parseContextRequests;
          const expected =
            phase === "plan"
              ? formal.parseProbePlan
              : formal.parseContextRequests;
          for (const wire of [
            payload,
            JSON.stringify(payload),
            `\`\`\`json\n${JSON.stringify(payload)}\n\`\`\``,
          ])
            assert.deepEqual(
              capture((data) => actual(data, options), wire),
              capture((data) => expected(data, options), wire),
            );
          if (phase === "repair") {
            payload.action = "request_context";
            assert.deepEqual(
              capture(
                (data) => parseHarnessRepairDecision(data, options),
                payload,
              ),
              capture(
                (data) => formal.parseHarnessRepairDecision(data, options),
                payload,
              ),
            );
          }
        }
      },
    );
  }
}

test(
  "minimization canonicalization and diagnostics match formal",
  { skip: !formalRoot },
  async (t) => {
    const formal = await formalModule("prompt/proposal.mjs");
    const projectRoot = fs.mkdtempSync(path.join(os.tmpdir(), "probe-intent-"));
    t.after(() => fs.rmSync(projectRoot, { recursive: true, force: true }));
    fs.symlinkSync(
      process.env.PROBE_TEST_NODE_MODULES,
      path.join(projectRoot, "node_modules"),
      "dir",
    );
    const source = `import { test as check, expect as verify, vi as mocks } from "vitest";
import type { Value } from "./types.js";
mocks.mock("./counter.js", () => ({ value: 2 }));
function helper(value: number) { return value + 1; }
check("counter", async () => {
  // A comment does not change canonical behavior.
  const unused = /counter/i;
  const value: number = helper(1);
  const text = \`value=\${value}\`;
  for (const expected of [2]) { verify(value).toBe(expected); }
  verify(text).toBe("value=2");
});
`;
    const variants = [
      source,
      source.replace(
        "  // A comment does not change canonical behavior.\n",
        "",
      ),
      source.replace("  const unused = /counter/i;\n", ""),
      source.replace('import type { Value } from "./types.js";\n', ""),
      source.replace('mocks.mock("./counter.js", () => ({ value: 2 }));\n', ""),
      source.replace("helper(1)", "helper(2)"),
      source.replace(
        'verify(text).toBe("value=2");',
        'verify(text).toBe("value=3");',
      ),
      source.replace('  verify(text).toBe("value=2");\n', ""),
      source.replace(
        "for (const expected of [2])",
        "for (const expected of [3])",
      ),
      source.replace("return value + 1;", "return value + 2;"),
      source.replace("  const unused", "  const added = 1;\n  const unused"),
      'import { test } from "vitest"; test("counter", () => 2);',
    ];
    const asset = (append_code) => ({
      test_file: "counter.test.ts",
      append_code,
    });
    const capture = (validate, candidate) => {
      try {
        validate(asset(source), asset(candidate), { projectRoot });
        return null;
      } catch (error) {
        return error.message;
      }
    };
    for (const candidate of variants) {
      assert.equal(
        capture(validateMinimizedCodeIsSubset, candidate),
        capture(formal.validateMinimizedCodeIsSubset, candidate),
        candidate,
      );
    }
    assert.equal(capture(validateMinimizedCodeIsSubset, variants[2]), null);
    assert.ok(capture(validateMinimizedCodeIsSubset, variants[5]));

    // The approved call-envelope guard intentionally strengthens the reference.
    const changedCallback = source.replace(
      'check("counter", async () => {', 'check("counter", async function () {',
    );
    assert.equal(capture(formal.validateMinimizedCodeIsSubset, changedCallback), null);
    assert.match(capture(validateMinimizedCodeIsSubset, changedCallback), /callback signature/u);

    const changes = [
      ["imports", (text) => `import { extra } from "./extra.js";\n${text}`],
      ["top-level mocks", (text) => text.replace("value: 2", "value: 3")],
      [
        "protected top-level behavior",
        (text) => text.replace("return value + 1;", "return value + 2;"),
      ],
      [
        "test-body behavior",
        (text) =>
          text.replace("  const unused", "  const added = 1;\n  const unused"),
      ],
      [null, (text) => text.replace('  verify(text).toBe("value=2");\n', "")],
    ];
    for (let index = 0; index < changes.length; index += 1) {
      const candidate = changes
        .slice(index)
        .reduce((text, [, change]) => change(text), source);
      const label = changes[index][0];
      const expected = label
        ? `minimization added or changed ${label}`
        : "minimization changed the primary oracle assertion";
      for (const validate of [
        validateMinimizedCodeIsSubset,
        formal.validateMinimizedCodeIsSubset,
      ]) {
        assert.equal(capture(validate, candidate), expected);
      }
    }
  },
);

function cases() {
  const groups = { imports: [], members: [], calls: [], precedence: [] };
  const modules = [
    "child_process",
    "cluster",
    "dgram",
    "http",
    "http2",
    "https",
    "net",
    "tls",
    "worker_threads",
    "module",
    "os",
    "process",
    "vm",
    "path",
    "fs",
    "vitest",
    "./counter",
  ];
  for (const module of modules) {
    for (const prefix of ["", "node:", "node:node:"]) {
      const literal = JSON.stringify(prefix + module);
      groups.imports.push(
        `import value from ${literal};`,
        `export * from ${literal};`,
        `import(${literal});`,
        `require(${literal});`,
      );
    }
  }
  for (const receiver of [
    "Bun",
    "Deno",
    "process",
    "global",
    "globalThis",
    "local",
  ]) {
    for (const member of [
      "abort",
      "argv",
      "argv0",
      "chdir",
      "cwd",
      "env",
      "execArgv",
      "exit",
      "getegid",
      "geteuid",
      "getgid",
      "getgroups",
      "getuid",
      "kill",
      "memoryUsage",
      "pid",
      "ppid",
      "resourceUsage",
      "setegid",
      "seteuid",
      "setgid",
      "setgroups",
      "setuid",
      "title",
      "uptime",
      "fetch",
      "WebSocket",
      "EventSource",
      "version",
      "unknown",
    ]) {
      groups.members.push(
        `${receiver}.${member};`,
        `${receiver}[${JSON.stringify(member)}];`,
      );
    }
    groups.members.push(
      `${receiver}[name];`,
      `${receiver}[""];`,
      `${receiver}[0];`,
    );
  }
  for (const callee of [
    "eval",
    "fetch",
    "Function",
    "EventSource",
    "WebSocket",
    "local",
  ]) {
    groups.calls.push(
      `${callee}();`,
      `new ${callee}();`,
      `object.${callee}();`,
    );
  }
  groups.calls.push(
    "import(name);",
    "require(name);",
    "require();",
    'import("");',
    'require("");',
    "import(`./counter`);",
    "require(`./counter`);",
    "import(`./${name}`);",
    "require(`./${name}`);",
    'object.require("./counter");',
    'import type { Counter } from "./counter";',
    'export type { Counter } from "./counter";',
    'import counter = require("./counter");',
    'import ""; export * from "";',
  );
  groups.precedence.push(
    'fetch(); process.env; import("http"); import(name);',
    'process.env; process["env"]; process.env; require(name);',
    'require("net"); import("http"); require("net");',
    'import value from "http"; const = ;',
    "const value = { fetch() {} }; value.fetch();",
  );
  return groups;
}

// Compare parsing and diagnostics only; none of these source fixtures is executed.
for (const [group, sources] of Object.entries(cases())) {
  test(
    `proposal ${group}: acceptance and rejection order match formal`,
    { skip: !formalRoot },
    async (t) => {
      const formal = await formalModule("prompt/proposal.mjs");
      const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-proposal-"));
      t.after(() => fs.rmSync(root, { recursive: true, force: true }));
      fs.symlinkSync(
        process.env.PROBE_TEST_NODE_MODULES,
        path.join(root, "node_modules"),
        "dir",
      );
      const canonicalPlan = {
        boundary_plan: [
          {
            boundary_id: "b1",
            target_unit_ids: ["u1"],
            route: { entrypoint_id: "e1" },
            probe: {
              test_intent: "count",
              activation_conditions: ["zero input"],
            },
            invariant: {
              independent_oracle: "two",
              supporting_evidence: "docstring",
              expected_observation: "two",
              oracle_mode: "assertion",
            },
            oracle_family: "arithmetic",
            novelty_from_prior: "first",
            bug_hypothesis: "increment",
          },
        ],
      };
      const base = {
        asset_id: "a1",
        boundary_id: "b1",
        test_file: "test/generated/benchmarkbr/counter.test.ts",
        input_construction: "zero",
        observable_oracle: "return",
        primary_oracle: "equals two",
      };
      const options = {
        projectRoot: root,
        canonicalPlan,
        publicEntrypoints: [{ entrypoint_id: "e1" }],
      };
      const capture = (parse, content, limits = {}) => {
        try {
          return parse(content, { ...options, ...limits });
        } catch (error) {
          return { error: error.message };
        }
      };
      for (const source of sources) {
        const candidate = { ...base, append_code: source };
        for (const assets of [
          [candidate],
          [
            candidate,
            { ...base, asset_id: "a2", append_code: "const value = 2;" },
          ],
        ]) {
          assert.deepEqual(
            capture(parseProposalPartial, { assets }),
            capture(formal.parseProposalPartial, { assets }),
            source,
          );
        }
      }
      if (group === "precedence") {
        const asset = { ...base, append_code: "const value = 2;" };
        const mixed = [
          asset,
          null,
          asset,
          { ...asset, asset_id: "bad", append_code: "const = ;" },
          { ...asset, asset_id: "a2" },
        ];
        for (const assets of [[], mixed, mixed.toReversed()]) {
          const content = { assets };
          const before = structuredClone(content);
          for (const maxAssets of [-1, 0, 1, 3, 20]) {
            for (const allowEmptyAssets of [false, true]) {
              const limits = { maxAssets, allowEmptyAssets };
              assert.equal(
                JSON.stringify(capture(parseProposalPartial, content, limits)),
                JSON.stringify(
                  capture(formal.parseProposalPartial, content, limits),
                ),
              );
              assert.deepEqual(content, before);
            }
          }
        }
      }
    },
  );
}
