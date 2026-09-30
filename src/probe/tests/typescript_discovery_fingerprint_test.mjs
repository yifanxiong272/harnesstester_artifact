/** Failure identity across disposable checkouts, without model calls. */
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import {
  confirmFailure, failureFingerprint, isDiscoveryFailure,
} from "../typescript/run/discovery.mjs";
import { preparedValidation } from "../typescript/run/session.mjs";

function summary(nodeid = "tests/a/probe.test.ts > suite > test value[a/b:12]", changes = {}) {
  return {
    status: "assertion_failed", passed: false, timed_out: false,
    classification_source: "structured_reporter",
    classification_reason: "non_assertion_or_incomplete_execution",
    failed_nodeids: [nodeid], failed_hooks: [],
    failure_excerpt: "AssertionError: expected /api/v1/value:12",
    ...changes,
  };
}

for (const uri of [false, true]) {
  test(`normalize recorded checkout before compaction; file URI=${uri}`, () => {
    const fingerprints = ["/tmp/validation-short/checkout", `/tmp/${"long-".repeat(50)}/checkout`].map(copyRoot => {
      const prefix = `${uri ? "file://" : ""}${copyRoot}`;
      return failureFingerprint(summary(`${prefix}/tests/a/probe.test.ts > suite > test value[a/b:12]`, {
        failure_excerpt: `Error: "${prefix}/src/value.ts:12:3" ${"detail ".repeat(80)}`,
      }), { copyRoot });
    });
    assert.equal(...fingerprints);
  });
}

for (const nodeid of [
  "tests/b/probe.test.ts > suite > test value[a/b:12]",
  "tests/a/probe.test.ts > other suite > test value[a/b:12]",
  "tests/a/probe.test.ts > suite > other test[a/b:12]",
  "tests/a/probe.test.ts > suite > test value[a/b:13]",
]) {
  test(`preserve full test identity: ${nodeid}`, () => {
    assert.notEqual(failureFingerprint(summary()), failureFingerprint(summary(nodeid)));
  });
}

for (const [first, second] of [
  ["expected /api/v1/a", "expected /api/v1/b"],
  ["endpoint http://host:123/api", "endpoint http://host:456/api"],
  ["value:12:3", "value:12:4"],
  ["at /tmp/validation-one/checkout/src/a.ts:10", "at /tmp/validation-two/checkout/src/a.ts:10"],
  ["at /fixture/checkout/src/a.ts:10", "at /fixture/checkout/src/b.ts:10"],
  ["at /fixture/checkout/src/a.ts:10", "at /fixture/checkout/src/a.ts:11"],
  ["at /fixture/checkout-other/a", "at /fixture/checkout-another/a"],
  ["at /prefix/fixture/checkout/a", "at /different/fixture/checkout/a"],
]) {
  test(`preserve semantic value: ${second}`, () => {
    const fingerprint = failure_excerpt => failureFingerprint(summary(undefined, { failure_excerpt }), { copyRoot: "/fixture/checkout" });
    assert.notEqual(fingerprint(first), fingerprint(second));
  });
}

test("keep identity values and ignore nodeid ordering", () => {
  assert.equal(
    failureFingerprint(summary("/fixture/checkout/tests/a/probe.test.ts > suite > test value[a/b:12]"), { copyRoot: "/fixture/checkout" }),
    failureFingerprint(summary()),
  );
  assert.notEqual(
    failureFingerprint(summary("tests/probe.ts > /fixture/checkout/a"), { copyRoot: "/fixture/checkout" }),
    failureFingerprint(summary("tests/probe.ts > /another/checkout/a"), { copyRoot: "/another/checkout" }),
  );
  const ids = ["tests/b.ts > test b", "tests/a.ts > test a"];
  assert.equal(
    failureFingerprint(summary(undefined, { failed_nodeids: ids })),
    failureFingerprint(summary(undefined, { failed_nodeids: [...ids].reverse() })),
  );
});

function temporary(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-fingerprint-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return root;
}

test("deleted checkout resolves surviving symlink ancestor", t => {
  const directory = temporary(t);
  const real = path.join(directory, "real");
  const alias = path.join(directory, "alias");
  fs.mkdirSync(real);
  fs.symlinkSync(real, alias, "dir");
  const fingerprints = ["first", "second"].map(name => {
    const copyRoot = path.join(alias, name, "checkout");
    const canonical = path.join(fs.realpathSync(real), name, "checkout");
    assert.equal(fs.existsSync(copyRoot), false);
    return failureFingerprint(summary(`${canonical}/tests/probe.test.ts > identity`, {
      failure_excerpt: `Error: ${canonical}/src/a.ts:12:3`,
    }), { copyRoot });
  });
  assert.equal(...fingerprints);
});

for (const status of ["assertion_failed", "needs_repair"]) {
  for (const drift of [false, true]) {
    test(`confirmation uses each materialized root: ${status}, drift=${drift}`, t => {
      const observation = (root, name) => ({
        materialized: { copy_root: root },
        summary: summary(`${root}/tests/probe.test.ts > ${name}`, {
          status, failure_excerpt: `Error: ${root}/src/a.ts:10`,
        }),
      });
      const first = observation("/tmp/validation-first/checkout", "a");
      const queued = [observation("/tmp/validation-second/checkout", drift ? "b" : "a")];
      const result = confirmFailure({ options: {
        revealConfirmationRuns: 1, validationRunner: () => queued.shift(),
      } }, { buggy: first, asset: {}, sampleDir: temporary(t) }, "base");
      assert.equal(result.stable, !drift);
      assert.equal(result.runs[0].passed, !drift);
    });
  }
}

for (const changes of [
  { timed_out: true }, { classification_source: "text" },
  { classification_reason: "collection_error" }, { failed_nodeids: [] },
  { failed_hooks: ["beforeEach"] }, { failed_hooks: ["afterEach"] },
]) {
  test(`nonassertion eligibility unchanged: ${JSON.stringify(changes)}`, () => {
    assert.equal(isDiscoveryFailure(summary(undefined, { status: "needs_repair", ...changes })), false);
  });
}

function realFixture(t, code) {
  const dependencies = process.env.PROBE_TEST_NODE_MODULES;
  assert.ok(dependencies, "Set PROBE_TEST_NODE_MODULES to the local Vitest dependencies");
  const directory = temporary(t);
  const root = path.join(directory, "prepared");
  fs.mkdirSync(root);
  fs.symlinkSync(path.resolve(dependencies), path.join(root, "node_modules"), "dir");
  fs.writeFileSync(path.join(root, "package.json"), '{"type":"module"}\n');
  fs.writeFileSync(path.join(root, "vitest.config.ts"), 'export default { test: { include: ["test/**/*.test.ts"] } };\n');
  const asset = { test_file: "test/identity.test.ts", append_code: code };
  const runtime = {
    caseData: { revisions: { latest: "fixture" } }, roots: { latest: root }, env: {},
    packet: { test_command: ["vitest", "run", "--config", "vitest.config.ts"] },
    options: { revealConfirmationRuns: 2, timeoutSeconds: 15, validationRunner: preparedValidation },
  };
  const sampleDir = path.join(directory, "sample");
  const initial = () => preparedValidation({ runtime, revisionKind: "latest", asset, assetDir: sampleDir });
  return { root, runtime, asset, sampleDir, initial };
}

for (const assertion of [true, false]) {
  test(`real Vitest is stable across checkout copies: assertion=${assertion}`, t => {
    const code = 'import { it, expect } from "vitest";\n' + (assertion
      ? 'it("identity", () => { expect(import.meta.url).toBe("expected"); });\n'
      : 'it("identity", () => { throw new Error(import.meta.url); });\n');
    const fixture = realFixture(t, code);
    const first = fixture.initial();
    assert.equal(isDiscoveryFailure(first.summary), true, JSON.stringify(first.summary));
    assert.equal(first.materialized.cleanup.removed, true);
    const result = confirmFailure(fixture.runtime, { ...fixture, buggy: first }, "base");
    assert.equal(result.stable, true, JSON.stringify(result));
    assert.ok(new Set([first.summary.failure_excerpt, ...result.runs.map(run => run.latest.failure_excerpt)]).size > 1);
    const position = evidence => evidence.failure_excerpt.match(/\/test\/identity\.test\.ts:(\d+):(\d+)/u)?.slice(1);
    assert.ok(position(first.summary));
    for (const run of result.runs) assert.deepEqual(position(run.latest), position(first.summary));
  });
}

test("real Vitest changing failed test with identical source/error is unstable", t => {
  const code = 'import { it, expect } from "vitest";\nimport { readFileSync } from "node:fs";\n'
    + 'const selected = JSON.parse(readFileSync(new URL("../selector.json", import.meta.url), "utf8"));\n'
    + 'for (const name of ["A", "B"]) it(name, () => { expect(name === selected ? 1 : 2).toBe(2); });\n';
  const fixture = realFixture(t, code);
  fs.writeFileSync(path.join(fixture.root, "selector.json"), '"A"');
  const first = fixture.initial();
  assert.equal(first.summary.status, "assertion_failed");
  fs.writeFileSync(path.join(fixture.root, "selector.json"), '"B"');
  const result = confirmFailure(fixture.runtime, { ...fixture, buggy: first }, "base");
  assert.equal(result.stable, false);
  assert.ok(result.runs.every(run => run.latest.status === "assertion_failed" && !run.passed));
  assert.ok(first.summary.failed_nodeids.some(id => id.endsWith(" > A")));
  assert.ok(result.runs.every(run => run.latest.failed_nodeids.some(id => id.endsWith(" > B"))));
});
