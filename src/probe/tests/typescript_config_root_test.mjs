import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import test from "node:test";
import { resolveLocalLauncher, writeVitestConfigOverride } from "../typescript/runtime/vitest_config.mjs";
import { validateVitest } from "../typescript/runtime/validate.mjs";

function fixture(t, expression) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "probe-config-root-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const projectRoot = path.join(directory, "checkout with spaces");
  fs.mkdirSync(projectRoot);
  const original = path.join(projectRoot, "vitest.config.mjs");
  const source = `export default ${expression};\n`;
  fs.writeFileSync(original, source);
  return { directory, projectRoot, original, source };
}

const cases = [
  ["default", "{}", [], "."],
  ["relative", "{ root: './service/../package' }", [], "package"],
  ["promise", "Promise.resolve({ root: 'package' })", [], "package"],
  ["function", "env => ({ root: env.mode === 'test' ? 'package' : 'wrong' })", [], "package"],
  ["async function", "async env => ({ root: env.mode === 'test' ? 'package' : 'wrong' })", [], "package"],
  ["CLI split priority", "{ root: 'wrong' }", ["--root", "package"], "package"],
  ["CLI inline priority", "{ root: 'wrong' }", ["--root=./service/../package"], "package"],
  ["CLI short priority", "{ root: 'wrong' }", ["-r", "package"], "package"],
  ["test root", "{ root: 'wrong', test: { root: 'package' } }", [], "package"],
  ["CLI over test root", "{ root: 'wrong', test: { root: 'also-wrong' } }", ["--root", "package"], "package"],
];

for (const [name, expression, flags, relativeRoot] of cases) {
  test(`retry uses normalized effective root: ${name}`, async (t) => {
    const context = fixture(t, expression);
    const testFile = path.posix.join(relativeRoot, "tests/generated.test.ts");
    const wrapped = writeVitestConfigOverride({
      command: ["vitest", "run", "--config", context.original, ...flags, testFile],
      projectRoot: context.projectRoot, outDir: path.join(context.directory, "out"),
      testFile, forceExactInclude: true,
    });
    const loaded = await import(pathToFileURL(wrapped.override.generated_config_path));
    const config = await loaded.default({ mode: "test" });
    assert.equal(config.root, path.resolve(context.projectRoot, relativeRoot));
    assert.deepEqual(config.test.include, ["tests/generated.test.ts"]);
    assert.deepEqual(config.test.exclude, []);
    assert.equal(wrapped.override.exact_include, null);
    assert.equal(wrapped.override.exact_include_target, path.resolve(context.projectRoot, testFile));
    assert.equal(fs.readFileSync(context.original, "utf8"), context.source);
  });
}

test("absolute config root and non-retry test settings are preserved", async (t) => {
  const context = fixture(t, "{}");
  const effectiveRoot = path.join(context.projectRoot, "package");
  const source = `export default { root: ${JSON.stringify(effectiveRoot)}, test: { include: ['original/**'], exclude: ['excluded/**'], setupFiles: ['setup.ts'] } };\n`;
  fs.writeFileSync(context.original, source);
  for (const forceExactInclude of [false, true]) {
    const wrapped = writeVitestConfigOverride({
      command: ["vitest", "run", "--config", context.original],
      projectRoot: context.projectRoot, outDir: path.join(context.directory, String(forceExactInclude)),
      testFile: "package/tests/generated.test.ts", forceExactInclude,
    });
    const loaded = await import(pathToFileURL(wrapped.override.generated_config_path));
    const config = await loaded.default({ mode: "test" });
    assert.equal(config.root, effectiveRoot);
    assert.deepEqual(config.test.include, forceExactInclude ? ["tests/generated.test.ts"] : ["original/**"]);
    assert.deepEqual(config.test.exclude, forceExactInclude ? [] : ["excluded/**"]);
    assert.deepEqual(config.test.setupFiles, ["setup.ts"]);
  }
  assert.equal(fs.readFileSync(context.original, "utf8"), source);
});

test("retry discovers the original default config and resolves its promised root", async (t) => {
  const context = fixture(t, "Promise.resolve({ root: 'package' })");
  const wrapped = writeVitestConfigOverride({
    command: ["vitest", "run", "package/tests/generated.test.ts"],
    projectRoot: context.projectRoot, outDir: path.join(context.directory, "out"),
    testFile: "package/tests/generated.test.ts", forceExactInclude: true,
  });
  assert.equal(wrapped.override.config_source, "default");
  const loaded = await import(pathToFileURL(wrapped.override.generated_config_path));
  const config = await loaded.default({ mode: "test" });
  assert.equal(config.root, path.join(context.projectRoot, "package"));
  assert.deepEqual(config.test.include, ["tests/generated.test.ts"]);
});

for (const flags of [["--root", "package"], ["--root=package"], ["-r", "package"]]) {
  test(`local launcher lookup shares root parsing: ${flags.join(" ")}`, (t) => {
    const context = fixture(t, "{}");
    const launcher = path.join(context.projectRoot, "package/node_modules/.bin/vitest");
    fs.mkdirSync(path.dirname(launcher), { recursive: true });
    fs.writeFileSync(launcher, "fixture");
    const command = ["pnpm", "exec", "vitest", "run", ...flags, "test.ts"];
    assert.deepEqual(resolveLocalLauncher(command, context.projectRoot), [launcher, ...command.slice(3)]);
  });
}

const dependencies = process.env.PROBE_TEST_NODE_MODULES && path.resolve(process.env.PROBE_TEST_NODE_MODULES);
const vitest = dependencies && path.join(dependencies, "vitest/vitest.mjs");
for (const cliRoot of [false, true]) {
  test(`real Vitest collects only the generated test with ${cliRoot ? "CLI" : "async config"} root`, {
    skip: !vitest || !fs.existsSync(vitest), timeout: 30000,
  }, (t) => {
    const context = fixture(t, `async () => ({ root: ${JSON.stringify(cliRoot ? "wrong" : "package")}, test: { include: ['existing/**/*.test.ts'] } })`);
    fs.symlinkSync(dependencies, path.join(context.projectRoot, "node_modules"), "dir");
    const testFile = "package/tests/generated.test.ts";
    fs.mkdirSync(path.join(context.projectRoot, "package/tests"), { recursive: true });
    fs.mkdirSync(path.join(context.projectRoot, "package/existing"), { recursive: true });
    fs.writeFileSync(path.join(context.projectRoot, testFile), 'import { it, expect } from "vitest"; it("generated", () => expect(2 + 2).toBe(4));\n');
    fs.writeFileSync(path.join(context.projectRoot, "package/existing/unrelated.test.ts"), 'throw new Error("unrelated tests must not run");\n');
    const command = [process.execPath, vitest, "run", "--config", context.original,
      ...(cliRoot ? ["--root=package"] : []), testFile];
    const wrapped = writeVitestConfigOverride({
      command, projectRoot: context.projectRoot, outDir: path.join(context.directory, "out"),
      testFile, forceExactInclude: true,
    });
    const report = path.join(context.directory, "report.json");
    const result = spawnSync(wrapped.command[0], [
      ...wrapped.command.slice(1), "--configLoader=runner", "--no-file-parallelism",
      "--maxWorkers=1", "--reporter=json", "--outputFile", report,
    ], { cwd: context.projectRoot, encoding: "utf8", timeout: 20000,
      env: { ...process.env, CI: "true", NO_COLOR: "1" } });
    assert.equal(result.status, 0, `${result.error || ""}\n${result.stdout}\n${result.stderr}`);
    const data = JSON.parse(fs.readFileSync(report, "utf8"));
    assert.equal(data.numTotalTests, 1);
    assert.equal(data.numPassedTests, 1);
    assert.deepEqual(data.testResults.map(item => fs.realpathSync(item.name)), [
      fs.realpathSync(path.join(context.projectRoot, testFile)),
    ]);
    assert.equal(fs.readFileSync(context.original, "utf8"), context.source);
    const validation = validateVitest({
      projectRoot: context.projectRoot, testFile, testCommand: command,
      outDir: path.join(context.directory, "validation"), timeoutSeconds: 20,
    });
    assert.equal(validation.status, "passed", JSON.stringify(validation));
    assert.equal(validation.collection_retry?.attempted, true);
    assert.equal(validation.collection_retry.initial.test_counts.total, 0);
    assert.equal(validation.test_counts.total, 1);
  });
}
