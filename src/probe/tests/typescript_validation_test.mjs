import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import test from "node:test";
import { ensureProjectEnv, writeVitestConfigOverride } from "../typescript/runtime/vitest_config.mjs";
import { preparedValidation } from "../typescript/run/session.mjs";
import {
  formalRoot,
  formalPath,
  formalModule,
  sourceModule,
} from "./typescript_support.mjs";
const artifactFile = fileURLToPath(
  new URL("../typescript/runtime/validate.mjs", import.meta.url),
);
const testFile = "tests/generated/counter.test.ts";

test("validation environment preserves the caller's executable search path", (t) => {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), "probe-env-"));
  t.after(() => fs.rmSync(outDir, { recursive: true, force: true }));
  const base = {
    PATH: "/fixture/bin:/usr/bin",
    LANG: "C",
    OPENAI_API_KEY: "fixture-secret",
  };
  const { env, scratchPaths } = ensureProjectEnv(outDir, base);
  assert.deepEqual(env, {
    PATH: base.PATH,
    LANG: "C",
    HOME: path.join(outDir, "home"),
    TMPDIR: path.join(outDir, "tmp"),
    CI: "true",
    NO_COLOR: "1",
  });
  assert.deepEqual(scratchPaths, [env.HOME, env.TMPDIR]);
  for (const directory of scratchPaths) {
    assert.ok(fs.statSync(directory).isDirectory());
  }
  assert.equal(fs.existsSync(path.join(outDir, "bin")), false);
  assert.equal(Object.hasOwn(ensureProjectEnv(outDir, {}).env, "PATH"), false);
  assert.equal(base.OPENAI_API_KEY, "fixture-secret");
});

test("bundle config imports remain local paths for TypeScript transpilation", (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-bundle-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const original = path.join(root, "vitest.config.ts");
  const source = "const config: object = {}; export default config;\n";
  fs.writeFileSync(original, source);
  for (const flags of [["--configLoader=bundle"], ["--configLoader", "bundle"], ["--configLoader=runner"]]) {
    const outDir = path.join(root, "out");
    const wrapped = writeVitestConfigOverride({
      command: ["vitest", "--config", original, ...flags],
      projectRoot: root, outDir, testFile,
    });
    const text = fs.readFileSync(wrapped.override.generated_config_path, "utf8");
    const expected = flags.includes("--configLoader=runner") ? pathToFileURL(original).href : original;
    assert.ok(text.startsWith(`import baseConfig from ${JSON.stringify(expected)};`));
    assert.equal(fs.readFileSync(original, "utf8"), source);
  }
});

// Load the real modules with a scripted child process, retaining all configuration
// and evidence handling. Filesystem effects remain inside the test's temp folder.
async function validationModule(file, directory) {
  let { source, tree, ts } = sourceModule(file);
  for (const statement of [...tree.statements].reverse()) {
    if (!ts.isImportDeclaration(statement)) continue;
    const literal = statement.moduleSpecifier;
    if (!literal.text.startsWith(".")) continue;
    const replacement =
      literal.text === "./process.mjs"
        ? "let spawnManagedSync; export function setProcess(runner) { spawnManagedSync = runner; }"
        : statement
            .getText(tree)
            .replace(
              literal.getText(tree),
              JSON.stringify(
                pathToFileURL(path.resolve(path.dirname(file), literal.text))
                  .href,
              ),
            );
    source =
      source.slice(0, statement.getStart(tree)) +
      replacement +
      source.slice(statement.end);
  }
  source = source.replaceAll(
    "import.meta.url",
    JSON.stringify(pathToFileURL(file).href),
  );
  source +=
    "\nexport { sandboxedCommand, boundedLog, compactReporter, writeVitestConfigOverride };\n";
  if (file !== artifactFile) {
    source += "export { collectionEvidence, reporterFailures };\n";
  }
  const copied = path.join(
    directory,
    `${path.basename(path.dirname(file))}-${Math.random()}.mjs`,
  );
  fs.writeFileSync(copied, source);
  return import(pathToFileURL(copied));
}

function report(state = "passed") {
  return {
    schema: "test-augment-vitest-structured-report",
    modules: [
      {
        module_path: testFile,
        collected: true,
        started: true,
        state,
        errors: [],
        hooks: {},
      },
    ],
    tests: [
      {
        module_path: testFile,
        name: "increments",
        state,
        errors:
          state === "failed"
            ? [
                {
                  message: "expected 2",
                  stack: "AssertionError: expected 2",
                  is_assertion: true,
                },
              ]
            : [],
        hooks: {},
      },
    ],
    unhandled_errors: [],
  };
}

function assertDeferredInclude(actual, reference, target, previousInclude) {
  assert.equal(reference.force_exact_include, true);
  assert.equal(reference.exact_include, previousInclude);
  assert.equal(actual.exact_include, null);
  assert.equal(actual.exact_include_target, target);
  const expected = {
    ...reference,
    exact_include: null,
    exact_include_target: target,
  };
  assert.deepEqual(actual, expected);
  return expected;
}

test("revision-local Node is preserved across validation retries", {
  skip: !process.env.PROBE_TEST_NODE_MODULES,
}, async (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-node-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const module = await validationModule(artifactFile, root);
  const projectRoot = path.join(root, "checkout");
  const bin = path.join(projectRoot, "node_modules", ".bin");
  fs.mkdirSync(bin, { recursive: true });
  fs.writeFileSync(path.join(bin, "node"), "fixture executable");
  fs.writeFileSync(path.join(projectRoot, "vitest.config.mjs"), "export default {};\n");
  const base = { PATH: "/fixture/bin:/usr/bin" };
  const seen = [];
  module.setProcess((_executable, _args, options) => {
    seen.push(options.env.PATH);
    fs.writeFileSync(options.env.TEST_AUGMENT_VITEST_REPORT, JSON.stringify(
      seen.length === 1
        ? { schema: report().schema, modules: [], tests: [], unhandled_errors: [] }
        : report(),
    ));
    return { result: { status: seen.length === 1 ? 1 : 0, stdout: "", stderr: "" } };
  });
  const result = module.validateVitest({
    projectRoot, testFile, outDir: path.join(root, "out"), env: base,
  });
  assert.equal(result.status, "passed");
  assert.deepEqual(seen, Array(2).fill(`${bin}${path.delimiter}${base.PATH}`));
  assert.equal(base.PATH, "/fixture/bin:/usr/bin");
});

test("isolated paired execution uses each revision's Node executable", (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-node-pair-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const roots = {};
  for (const kind of ["buggy", "fixed"]) {
    roots[kind] = path.join(root, kind);
    const bin = path.join(roots[kind], "node_modules", ".bin");
    fs.mkdirSync(bin, { recursive: true });
    const executable = fs.realpathSync(
      kind === "buggy" && process.env.PROBE_TEST_NODE_BINARY
        ? process.env.PROBE_TEST_NODE_BINARY : process.execPath,
    );
    fs.symlinkSync(executable, path.join(bin, "node"));
    const launcher = path.join(bin, "vitest");
    fs.writeFileSync(launcher, `#!/usr/bin/env node
const fs = require('node:fs');
if (process.execPath !== ${JSON.stringify(executable)}) process.exit(2);
if (fs.realpathSync(process.env.PATH.split(require('node:path').delimiter)[0]) !== ${JSON.stringify(fs.realpathSync(bin))}) process.exit(3);
fs.writeFileSync(process.env.TEST_AUGMENT_VITEST_REPORT, JSON.stringify(${JSON.stringify(report())}));
`);
    fs.chmodSync(launcher, 0o755);
  }
  const runtime = {
    roots, caseData: { revisions: { buggy: "before", fixed: "after" } },
    packet: { test_command: ["pnpm", "exec", "vitest", "run", "<generated-test-file>"] },
    options: { timeoutSeconds: 30 }, env: { PATH: process.env.PATH },
  };
  // Repeat buggy after fixed to detect runtime leakage across replay calls.
  for (const [index, kind] of ["buggy", "fixed", "buggy"].entries()) {
    const assetDir = path.join(root, `attempt_${index}`);
    const result = preparedValidation({
      runtime, revisionKind: kind, assetDir,
      asset: { test_file: testFile, append_code: "// Runtime-selection fixture." },
    });
    assert.equal(result.summary.status, "passed", JSON.stringify(result.summary));
    assert.equal(result.materialized.cleanup.removed, true);
    assert.equal(fs.existsSync(path.join(roots[kind], testFile)), false);
  }
});

test(
  "generated Vitest configuration preserves source bytes and evaluated behavior",
  { skip: !formalRoot },
  async (t) => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-config-"));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const artifact = await validationModule(artifactFile, root);
    const formal = await validationModule(
      formalPath("runtime/validate.mjs"),
      root,
    );
    const projectRoot = path.join(root, "project with 'quoted' paths");
    const outDir = path.join(root, "result");
    fs.mkdirSync(projectRoot);
    fs.mkdirSync(outDir);
    const configs = [
      "null",
      "42",
      "{ root: '', test: { cache: false, experimental: null } }",
      "{ test: { include: ['other/**'], exclude: ['excluded/**'], cache: { enabled: true }, experimental: { retained: true } } }",
      "Promise.resolve({ root: 'custom-root', retained: true })",
      "(env) => ({ mode: env.mode, test: { retained: 42 } })",
      "async (env) => ({ mode: env.mode, test: { cache: {}, experimental: {} } })",
      "() => { throw new Error('fixture config error'); }",
    ];
    for (const [index, config] of configs.entries()) {
      const base = `vitest-${index}.mjs`;
      fs.writeFileSync(
        path.join(projectRoot, base),
        `export default ${config};\n`,
      );
      for (const forceExactInclude of [false, true]) {
        const observed = [];
        for (const [implementation, module] of [artifact, formal].entries()) {
          const metadata = module.writeVitestConfigOverride({
            command: [
              "vitest",
              "run",
              "--root",
              "src",
              "--config",
              base,
              testFile,
            ],
            projectRoot,
            outDir,
            testFile,
            forceExactInclude,
          });
          const file = metadata.override.generated_config_path;
          const url = pathToFileURL(file);
          url.searchParams.set("case", `${index}-${implementation}`);
          let value;
          try {
            const loaded = await import(url.href);
            value = await loaded.default({ mode: "fixture" });
          } catch (error) {
            value = { error: { name: error.name, message: error.message } };
          }
          assert.equal(
            fs.readFileSync(path.join(projectRoot, base), "utf8"),
            `export default ${config};\n`,
          );
          observed.push({ metadata, value });
        }
        const [actual, reference] = observed;
        const effectiveRoot = path.resolve(projectRoot, "src");
        const target = path.resolve(projectRoot, testFile);
        const exactInclude = path.relative(effectiveRoot, target).split(path.sep).join("/");
        if (forceExactInclude) {
          reference.metadata.override = assertDeferredInclude(
            actual.metadata.override, reference.metadata.override, target, exactInclude,
          );
        } else {
          assert.equal(actual.metadata.override.exact_include, "");
          assert.equal(Object.hasOwn(actual.metadata.override, "exact_include_target"), false);
        }
        if (!reference.value.error) {
          assert.equal(actual.value.root, effectiveRoot);
          if (forceExactInclude) {
            assert.deepEqual(actual.value.test.include, [exactInclude]);
            assert.deepEqual(actual.value.test.exclude, []);
          }
          // CLI root wins after normalization; every other evaluated field stays compared.
          reference.value = { ...reference.value, root: effectiveRoot };
        }
        assert.deepEqual(
          actual,
          reference,
          `config ${index}, exact ${forceExactInclude}`,
        );
      }
    }
  },
);

for (const count of [0, 1, 500, 501]) {
  test(
    `reporter lifecycle, updates and bounds match formal: ${count} tests`,
    { skip: !formalRoot },
    async (t) => {
      const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-reporter-"));
      t.after(() => fs.rmSync(root, { recursive: true, force: true }));
      const artifact = await import(
        "../typescript/runtime/vitest_structured_reporter.mjs"
      );
      const formal = await formalModule(
        "runtime/vitest_structured_reporter.mjs",
      );
      const reportPath = path.join(root, "report.json");
      const previous = process.env.TEST_AUGMENT_VITEST_REPORT;
      process.env.TEST_AUGMENT_VITEST_REPORT = reportPath;
      const outputs = [];
      try {
        for (const { default: Reporter } of [artifact, formal]) {
          const reporter = new Reporter();
          const modules = Array.from({ length: 101 }, (_, index) => ({
            id: `module-${index}`,
            moduleId: `src/counter-${index}.test.ts`,
            relativeModuleId: `src/counter-${index}.test.ts`,
            task: { result: { hooks: { beforeAll: "pass" } } },
            state: () => "passed",
            errors: () => [],
            children: { allTests: () => [] },
          }));
          const errors = [
            { name: "AssertionError", message: "changed result" },
          ];
          const tests = Array.from({ length: count }, (_, index) => ({
            id: `test-${index}`,
            module: modules[0],
            fullName: `case ${index}`,
            task: { result: { hooks: { beforeEach: "pass" } } },
            result: () => ({ state: "passed", errors: [] }),
          }));
          modules[0].children.allTests = () => tests;
          for (const module of modules) {
            reporter.onTestModuleQueued(module);
            reporter.onTestModuleCollected(module);
            reporter.onTestModuleStart(module);
            const hook = { entity: module, name: "afterAll" };
            reporter.onHookStart(hook);
            reporter.onHookEnd(hook);
          }
          for (const testCase of tests) reporter.onTestCaseResult(testCase);
          if (tests.length) {
            tests[0].result = () => ({ state: "failed", errors });
            reporter.onTestCaseResult(tests[0]);
            // The final callback must refresh existing records even at the cap.
            tests[0].result = () => ({ state: "skipped", errors: [] });
            reporter.onHookStart({ entity: tests[0], name: "afterEach" });
          }
          reporter.onTestRunEnd(modules, Array(21).fill(errors[0]), "finished");
          outputs.push(fs.readFileSync(reportPath, "utf8"));
        }
      } finally {
        if (previous === undefined)
          delete process.env.TEST_AUGMENT_VITEST_REPORT;
        else process.env.TEST_AUGMENT_VITEST_REPORT = previous;
      }
      assert.equal(outputs[0], outputs[1]);
      const result = JSON.parse(outputs[0]);
      assert.equal(result.test_count, count);
      assert.equal(result.tests.length, Math.min(count, 500));
      assert.equal(result.tests_truncated, count > 500);
      assert.equal(result.modules.length, 100);
      assert.equal(result.modules_truncated, true);
      assert.equal(result.unhandled_errors.length, 20);
      if (count) {
        assert.equal(result.tests[0].state, "skipped");
        assert.equal(result.tests[0].hooks.afterEach, "run");
      }
    },
  );
}

test(
  "bounded log and reporter storage match formal byte for byte",
  { skip: !formalRoot },
  async (t) => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-storage-"));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const artifact = await validationModule(artifactFile, root);
    const formal = await validationModule(
      formalPath("runtime/validate.mjs"),
      root,
    );
    const command = ["vitest", "run", "test/generated/\u4e2d.test.ts"];
    const prefixBytes = Buffer.byteLength(
      `$ ${command.join(" ")}${os.EOL}${os.EOL}`,
    );
    for (const length of [
      0,
      1,
      2 * 1024 * 1024 - prefixBytes - 1,
      2 * 1024 * 1024 - prefixBytes,
      2 * 1024 * 1024 - prefixBytes + 1,
      3 * 1024 * 1024,
    ]) {
      for (const character of ["x", "\u4e2d", "\u{1f600}"]) {
        const output = character.repeat(length);
        assert.deepEqual(
          artifact.boundedLog(command, output),
          formal.boundedLog(command, output),
        );
      }
    }
    const reporterPath = path.join(root, "reporter.json");
    for (const size of [
      null,
      0,
      12,
      4 * 1024 * 1024 - 1,
      4 * 1024 * 1024,
      4 * 1024 * 1024 + 1,
    ]) {
      const results = [];
      for (const module of [artifact, formal]) {
        fs.rmSync(reporterPath, { force: true });
        if (size !== null) fs.writeFileSync(reporterPath, "x".repeat(size));
        const record = module.compactReporter(
          reporterPath,
          { success: true },
          { total: 2 },
          ["failure"],
        );
        results.push({
          record,
          content: fs.existsSync(reporterPath)
            ? fs.readFileSync(reporterPath)
            : null,
        });
      }
      assert.deepEqual(results[0], results[1]);
      assert.equal(results[0].record.compacted, size > 4 * 1024 * 1024);
    }
  },
);

function scenarios() {
  const cases = [
    ["passed", report(), 0],
    ["assertion", report("failed"), 1],
    ["skipped", report("skipped"), 0],
    ["running", report("run"), 1],
    ["no reporter", null, 1],
    ["timeout", report(), 124, "SIGTERM"],
    ["bad exit", report(), null],
    [
      "old reporter",
      {
        numTotalTests: 1,
        numFailedTests: 1,
        testResults: [
          {
            name: testFile,
            message: "suite error",
            assertionResults: [
              {
                status: "failed",
                fullName: "increments",
                failureMessages: ["expected 2"],
              },
            ],
          },
        ],
      },
      1,
    ],
  ];
  for (const field of ["modules_truncated", "tests_truncated"])
    cases.push([field, { ...report(), [field]: true }, 1]);
  for (const scope of ["modules", "tests"]) {
    for (const hook of ["beforeEach", "afterEach"]) {
      const data = report("failed");
      data[scope][0].hooks[hook] = "fail";
      cases.push([`${scope} ${hook}`, data, 1]);
    }
  }
  for (const mutation of [
    (data) => {
      data.modules[0].started = false;
    },
    (data) => {
      data.modules[0].collected = false;
    },
    (data) => {
      data.modules.push({ ...data.modules[0] });
    },
    (data) => {
      data.tests[0].module_path = "tests/unrelated.test.ts";
    },
    (data) => {
      data.modules[0].errors = [{ message: "module failed" }];
    },
    (data) => {
      data.unhandled_errors = [{ message: "unhandled" }];
    },
    (data) => {
      data.unhandled_error_count = 1;
    },
    (data) => {
      data.tests[0].errors[0].is_assertion = false;
    },
    (data) => {
      data.tests[0].errors = [];
    },
    (data) => {
      data.tests.push({ ...report().tests[0], name: "another" });
    },
  ]) {
    const data = report("failed");
    mutation(data);
    cases.push([`evidence variant ${cases.length}`, data, 1]);
  }
  cases.push([
    "zero collection",
    { schema: report().schema, modules: [], tests: [], unhandled_errors: [] },
    1,
  ]);
  return cases;
}

test(
  "Vitest evidence, commands, retries, and retained records match formal",
  { skip: !formalRoot },
  async (t) => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-validation-"));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const artifact = await validationModule(artifactFile, root);
    const formal = await validationModule(
      formalPath("runtime/validate.mjs"),
      root,
    );
    const projectRoot = path.join(root, "project");
    fs.mkdirSync(projectRoot);
    fs.writeFileSync(
      path.join(projectRoot, "vitest.config.mjs"),
      "export default { test: {include: ['other/**']} };\n",
    );
    const outDir = path.join(root, "result");
    const commands = [
      undefined,
      [
        "pnpm",
        "exec",
        "vitest",
        "run",
        "--config",
        "vitest.config.mjs",
        "<generated-test-file>",
      ],
      ["vitest", "run", "-c", "missing.mjs"],
      ["vitest", "run", "--root=.", "--configLoader=runner"],
    ];
    for (const [label, data, exitCode, signal] of scenarios()) {
      for (const command of commands) {
        const observed = [];
        for (const module of [artifact, formal]) {
          fs.rmSync(outDir, { recursive: true, force: true });
          const calls = [];
          module.setProcess((executable, args, options) => {
            const payload =
              calls.length > 0 && label === "zero collection" ? report() : data;
            calls.push({ executable, args, ...options });
            if (payload)
              fs.writeFileSync(
                options.env.TEST_AUGMENT_VITEST_REPORT,
                JSON.stringify(payload),
              );
            return {
              result: {
                status: calls.length > 1 ? 0 : exitCode,
                signal,
                stdout: "fixture output\n",
                stderr: "FAIL tests/generated/counter.test.ts > increments\n",
              },
              process_group_cleanup: { attempted: true, signal_sent: true },
            };
          });
          const value = module.validateVitest({
            projectRoot,
            testFile,
            testCommand: command,
            outDir,
            env: {
              PATH: "/usr/bin",
              LANG: "C",
              OPENAI_API_KEY: "fixture-secret",
            },
          });
          const retained = {};
          for (const record of [value, value.collection_retry?.initial].filter(
            Boolean,
          )) {
            for (const key of ["reporter_json", "log_path"]) {
              if (record[key])
                retained[record[key]] = fs.readFileSync(record[key]);
            }
            if (module === formal) {
              const reporter = record.reporter_json
                ? JSON.parse(retained[record.reporter_json])
                : null;
              assert.deepEqual(
                record.collection,
                formal.collectionEvidence({
                  reporter,
                  counts: record.test_counts,
                  failures: formal.reporterFailures(reporter),
                  testFile,
                }),
              );
              delete record.collection;
            } else {
              assert.equal(Object.hasOwn(record, "collection"), false);
            }
          }
          // Disk-allocation census is omitted; per-path cleanup remains.
          value.scratch_cleanup = value.scratch_cleanup.map(
            ({ allocated_bytes, ...record }) => record,
          );
          if (module === formal) {
            // The artifact omits the unused executable directory; compare the
            // remaining command, environment, evidence and cleanup unchanged.
            const binDir = path.join(outDir, "bin");
            for (const call of calls) {
              assert.equal(call.env.PATH, `${binDir}:/usr/bin`);
              call.env.PATH = "/usr/bin";
            }
            assert.equal(
              value.scratch_cleanup.filter(record => record.path === binDir).length,
              1,
            );
            value.scratch_cleanup = value.scratch_cleanup.filter(
              record => record.path !== binDir,
            );
          }
          observed.push({ value, calls, retained });
        }
        for (const [actual, reference] of [
          [observed[0].value, observed[1].value],
          [observed[0].value.collection_retry?.initial, observed[1].value.collection_retry?.initial],
        ]) {
          if (reference?.vitest_config_override?.force_exact_include) {
            reference.vitest_config_override = assertDeferredInclude(
              actual.vitest_config_override, reference.vitest_config_override,
              path.resolve(projectRoot, testFile), testFile,
            );
          }
        }
        assert.deepEqual(observed[0], observed[1], `${label}: ${command}`);
        assert.equal(
          observed[0].calls.length,
          label === "zero collection" && !command?.includes("missing.mjs")
            ? 2
            : 1,
        );
      }
    }
  },
);

test(
  "sandbox ancestor rules preserve exact paths and order",
  { skip: !formalRoot },
  async (t) => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-sandbox-"));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const artifact = await validationModule(artifactFile, root);
    const formal = await validationModule(
      formalPath("runtime/validate.mjs"),
      root,
    );
    const paths = [
      root,
      os.homedir(),
      path.join(os.homedir(), "project", "nested"),
      path.join(os.homedir(), "another", "nested"),
      `${os.homedir()}-outside`,
      process.cwd(),
    ];
    for (const projectRoot of paths) {
      for (const outDir of paths) {
        const options = { projectRoot, outDir, testFile };
        assert.deepEqual(
          artifact.sandboxedCommand(["vitest", "run"], options),
          formal.sandboxedCommand(["vitest", "run"], options),
        );
      }
    }
  },
);
