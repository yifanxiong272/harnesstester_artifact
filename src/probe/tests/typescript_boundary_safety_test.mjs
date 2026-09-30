import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { resolveContextRequests, projectTracebackContext } from "../typescript/prompt/context.mjs";
import { promptPacket } from "../typescript/prompt/prompts.mjs";
import { parseProposalPartial, validateMinimizedCodeIsSubset } from "../typescript/prompt/proposal.mjs";
import { validateMinimizedMetadata } from "../typescript/run/repair.mjs";
import { validateVitest } from "../typescript/runtime/validate.mjs";

const dependencies = process.env.PROBE_TEST_NODE_MODULES;
const requiresCompiler = { skip: !dependencies };

function project(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "probe-boundary-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const root = path.join(directory, "checkout");
  fs.mkdirSync(path.join(root, "src/nested"), { recursive: true });
  fs.symlinkSync(path.resolve(dependencies), path.join(root, "node_modules"), "dir");
  return { directory, root };
}

const source = (marker) => `export const FLAG = "${marker}";
export function marker() {
  return FLAG;
}
export class Holder { read() { return FLAG; } }
`;

const contextCases = [
  ["regular", "src/target.ts", ["src"], "found"],
  ["internal file", "src/link.ts", ["src"], "found"],
  ["internal directory", "src/linked/target.ts", ["src"], "found"],
  ["internal chain", "src/chain.ts", ["src"], "found"],
  ["cross-source-root link", "src/cross.ts", ["src", "lib"], "found"],
  ["internal source-root alias", "source-alias/target.ts", ["source-alias"], "found"],
  ["checkout alias", "src/link.ts", ["src"], "found"],
  ["dot source root", "src/link.ts", ["."], "found"],
  ["normalized source root", "src/link.ts", ["./src/"], "found"],
  ["outside file", "src/outside.ts", ["src"], "invalid"],
  ["outside directory", "src/outside-dir/secret.ts", ["src"], "invalid"],
  ["outside chain", "src/outside-chain.ts", ["src"], "invalid"],
  ["outside declared source root", "outside-root/secret.ts", ["outside-root"], "invalid"],
  ["non-source file", "src/private.ts", ["src"], "invalid"],
  ["non-source directory", "src/private-dir/secret.ts", ["src"], "invalid"],
  ["source-prefix sibling", "src/prefix.ts", ["src"], "invalid"],
  ["unapproved cross-root link", "src/cross.ts", ["src"], "invalid"],
  ["out-of-scope alias to source", "aux/source.ts", ["src"], "invalid"],
  ["missing file", "src/missing.ts", ["src"], "not_found"],
  ["broken link", "src/broken.ts", ["src"], "not_found"],
];

for (const [name, filepath, sourceRoots, expected] of contextCases) {
  test(`context real-path boundary: ${name}`, requiresCompiler, (t) => {
    const { directory, root } = project(t);
    const files = {
      "src/target.ts": "ALLOWED_SOURCE",
      "src/nested/target.ts": "ALLOWED_NESTED",
      "lib/target.ts": "CROSS_SOURCE",
      "private/secret.ts": "FORBIDDEN_PRIVATE",
      "src-neighbor/secret.ts": "FORBIDDEN_PREFIX",
    };
    for (const [file, marker] of Object.entries(files)) {
      fs.mkdirSync(path.dirname(path.join(root, file)), { recursive: true });
      fs.writeFileSync(path.join(root, file), source(marker));
    }
    const outside = path.join(directory, "outside");
    fs.mkdirSync(outside);
    fs.mkdirSync(path.join(root, "aux"));
    fs.writeFileSync(path.join(outside, "secret.ts"), source("FORBIDDEN_OUTSIDE"));
    for (const [link, target] of [
      ["src/link.ts", "target.ts"], ["src/linked", "nested"],
      ["src/chain.ts", "link.ts"], ["src/cross.ts", "../lib/target.ts"],
      ["source-alias", "src"], ["src/outside.ts", "../../outside/secret.ts"],
      ["src/outside-dir", "../../outside"], ["src/outside-chain.ts", "outside.ts"],
      ["outside-root", "../outside"], ["src/private.ts", "../private/secret.ts"],
      ["src/private-dir", "../private"], ["src/prefix.ts", "../src-neighbor/secret.ts"],
      ["src/broken.ts", "absent.ts"],
      ["aux/source.ts", "../src/target.ts"],
    ]) fs.symlinkSync(target, path.join(root, link));
    let projectRoot = root;
    if (name === "checkout alias") {
      projectRoot = path.join(directory, "checkout-alias");
      fs.symlinkSync(root, projectRoot, "dir");
    }

    // Fail at the read boundary, including indexing, not just at prompt filtering.
    const forbidden = new Set([
      path.join(outside, "secret.ts"),
      ...(!sourceRoots.includes(".") ? [
        path.join(root, "private/secret.ts"), path.join(root, "src-neighbor/secret.ts"),
      ] : []),
      ...(name === "unapproved cross-root link" ? [path.join(root, "lib/target.ts")] : []),
      ...(name === "out-of-scope alias to source" ? [path.join(root, "src/target.ts")] : []),
    ].map((file) => fs.realpathSync(file)));
    const originalRead = fs.readFileSync;
    t.mock.method(fs, "readFileSync", function (file, ...args) {
      const filename = file instanceof URL ? fileURLToPath(file) : file;
      if (typeof filename === "string" && fs.existsSync(filename)) {
        assert.ok(!forbidden.has(fs.realpathSync(filename)), `unexpected outside read: ${filename}`);
      }
      return originalRead.call(this, file, ...args);
    });
    const requests = [
      ["module_context", ""], ["function_definition", "marker"],
      ["symbol_definition", "FLAG"], ["class_definition", "Holder"],
    ].map(([kind, qualname]) => ({ kind, filepath, qualname, reason: "fixture" }));
    const context = resolveContextRequests({
      projectRoot, sourceRoots, requests, maxRequests: requests.length,
    });
    assert.deepEqual(context.requests.map((request) => request.status), requests.map(() => expected));
    assert.ok(!JSON.stringify(promptPacket({
      strategy: "target_probe_ldh", retrieved_context: context,
    })).includes("FORBIDDEN_"));
    if (expected === "found") {
      assert.ok(context.requests.every((request) => request.code.length > 0));
      assert.equal(context.requests[1].filepath, filepath);
    }
    const frames = projectTracebackContext({
      projectRoot, sourceRoots,
      failureText: `Error: fixture\n    at marker (${path.join(projectRoot, filepath)}:3:1)`,
    });
    assert.equal(frames.length, expected === "found" ? 1 : 0);
    if (frames.length) assert.equal(frames[0].qualname, "marker");
  });
}

for (const mode of ["omitted", "undefined", "empty"]) {
  test(`context source-root defaults: ${mode}`, requiresCompiler, (t) => {
    const { root: projectRoot, directory } = project(t);
    fs.writeFileSync(path.join(projectRoot, "src/target.ts"), source("ALLOWED"));
    fs.writeFileSync(path.join(directory, "outside.ts"), source("FORBIDDEN"));
    fs.symlinkSync("../../outside.ts", path.join(projectRoot, "src/outside.ts"));
    const options = mode === "omitted" ? {} : { sourceRoots: mode === "empty" ? [] : undefined };
    const context = resolveContextRequests({
      projectRoot, ...options, maxRequests: 2,
      requests: ["src/target.ts", "src/outside.ts"].map((filepath) => ({ kind: "module_context", filepath })),
    });
    assert.deepEqual(context.requests.map((item) => item.status), ["found", "invalid"]);
    for (const filename of ["target", "outside"]) {
      const frames = projectTracebackContext({
        projectRoot, ...options,
        failureText: `Error: fixture\n    at marker (${projectRoot}/src/${filename}.ts:3:1)`,
      });
      // The shared frame parser already treats an explicit [] as no source roots.
      assert.equal(frames.length, filename === "target" && mode !== "empty" ? 1 : 0);
    }
  });
}

test("context boundary does not disguise unexpected I/O failures", requiresCompiler, (t) => {
  const { root: projectRoot } = project(t);
  fs.writeFileSync(path.join(projectRoot, "src/target.ts"), source("ALLOWED"));
  const denied = Object.assign(new Error("fixture permission error"), { code: "EACCES" });
  const realpath = fs.realpathSync;
  t.mock.method(fs, "realpathSync", function (filename, ...args) {
    if (String(filename).endsWith("/src/target.ts")) throw denied;
    return realpath.call(this, filename, ...args);
  });
  assert.throws(() => resolveContextRequests({
    projectRoot, sourceRoots: ["src"], requests: [{ kind: "module_context", filepath: "src/target.ts" }],
  }), (error) => error === denied);
});

const imports = 'import { test as check, expect as verify } from "vitest";\n';
const first = `check("first", () => {
  const unusedFirst = 1;
  const value = 1;
  verify(value).toBe(2);
});\n`;
const second = `check("second", async () => {
  const unusedSecond = 2;
  verify(2).toBe(2);
});\n`;
const baseline = imports + first + second;
const asset = (append_code) => ({ test_file: "test/multiple.test.ts", append_code });

for (const [name, original, minimized] of [
  ["unchanged multiple tests", baseline, baseline],
  ["delete setup in each test", baseline, baseline.replace("  const unusedFirst = 1;\n", "").replace("  const unusedSecond = 2;\n", "")],
  ["single test still works", imports + first, imports + first.replace("  const unusedFirst = 1;\n", "")],
  ["duplicate titles matched in order", baseline.replace('"second"', '"first"'), baseline.replace('"second"', '"first"').replace("  const unusedFirst = 1;\n", "")],
  ["function callbacks", baseline.replaceAll("() =>", "function ()"), baseline.replaceAll("() =>", "function ()").replace("  const unusedSecond = 2;\n", "")],
  ["comments do not affect matching", baseline, baseline.replace("  const value", "  // kept input\n  const value")],
]) {
  test(`multi-test minimization permits ${name}`, requiresCompiler, (t) => {
    const { root: projectRoot } = project(t);
    assert.doesNotThrow(() => validateMinimizedCodeIsSubset(asset(original), asset(minimized), { projectRoot }));
  });
}

for (const [name, minimized] of [
  ["prepended test", imports + 'check("added", () => { verify(0).toBe(999); });\n' + first + second],
  ["appended test", baseline + 'check("added", () => { verify(0).toBe(999); });\n'],
  ["removed earlier test", imports + second],
  ["removed last test", imports + first],
  ["changed earlier oracle", baseline.replace("verify(value).toBe(2)", "verify(value).toBe(999)")],
  ["deleted earlier oracle", baseline.replace("  verify(value).toBe(2);\n", "")],
  ["changed earlier input", baseline.replace("const value = 1", "const value = 0")],
  ["added earlier body behavior", baseline.replace("  const value", "  const newBehavior = 3;\n  const value")],
  ["reordered tests", imports + second + first],
  ["renamed test", baseline.replace('"first"', '"different"')],
  ["callback default initializer", baseline.replace('"first", ()', '"first", (value = verify(false).toBe(true))')],
  ["callback kind change", baseline.replace('"first", () =>', '"first", function ()')],
  ["callback async change", baseline.replace('"first", ()', '"first", async ()')],
  ["extra call argument", baseline.replace("  verify(value).toBe(2);\n});", "  verify(value).toBe(2);\n}, verify(false).toBe(true));")],
  ["earlier non-block callback", imports + 'check("first", () => verify(0).toBe(999));\n' + second],
]) {
  test(`multi-test minimization rejects ${name}`, requiresCompiler, (t) => {
    const { root: projectRoot } = project(t);
    assert.throws(() => validateMinimizedCodeIsSubset(asset(baseline), asset(minimized), { projectRoot }));
  });
}

test("parsed multi-test minimization retains both real Vitest outcomes", requiresCompiler, (t) => {
  const { root: projectRoot, directory } = project(t);
  fs.mkdirSync(path.join(projectRoot, "test"));
  fs.writeFileSync(path.join(projectRoot, "package.json"), '{"type":"module"}\n');
  fs.writeFileSync(path.join(projectRoot, "vitest.config.ts"), 'export default { test: { include: ["test/**/*.test.ts"] } };\n');
  const boundary = {
    boundary_id: "boundary-001", target_unit_ids: ["u1"], route: { entrypoint_id: "entry-001" },
    probe: { test_intent: "arithmetic", activation_conditions: ["fixture"] },
    invariant: { independent_oracle: "arithmetic", supporting_evidence: "fixture", expected_observation: "two", oracle_mode: "assertion" },
    oracle_family: "arithmetic", novelty_from_prior: "first", bug_hypothesis: "wrong increment",
  };
  const parse = (code) => parseProposalPartial({ assets: [{
    ...asset(code), asset_id: "asset-001", boundary_id: boundary.boundary_id,
    input_construction: "fixture", observable_oracle: "equality", primary_oracle: "two", mocking_plan: "none",
  }] }, {
    projectRoot, allowedTestRoots: ["test"], canonicalPlan: { boundary_plan: [boundary] },
    publicEntrypoints: [{ entrypoint_id: "entry-001" }],
  }).proposal.assets[0];
  const before = parse(baseline);
  const after = parse(baseline.replace("  const unusedFirst = 1;\n", "").replace("  const unusedSecond = 2;\n", ""));
  validateMinimizedMetadata(before, after);
  validateMinimizedCodeIsSubset(before, after, { projectRoot });
  for (const [index, candidate] of [before, after].entries()) {
    fs.writeFileSync(path.join(projectRoot, candidate.test_file), candidate.append_code);
    const result = validateVitest({
      projectRoot, testFile: candidate.test_file,
      testCommand: ["vitest", "run", "--config", "vitest.config.ts"],
      outDir: path.join(directory, `validation-${index}`), timeoutSeconds: 15,
    });
    assert.equal(result.status, "assertion_failed", JSON.stringify(result));
    assert.deepEqual(result.test_counts, { total: 2, passed: 1, failed: 1, skipped: 0 });
    assert.ok(result.evidence.failed_nodeids.every((nodeid) => nodeid.endsWith(" > first")));
  }
  const changed = parse(baseline.replace("verify(value).toBe(2)", "verify(value).toBe(999)"));
  validateMinimizedMetadata(before, changed);
  assert.throws(() => validateMinimizedCodeIsSubset(before, changed, { projectRoot }));
});
