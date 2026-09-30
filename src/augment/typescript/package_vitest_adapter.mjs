import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { sanitizeEnvForSubprocess } from "./run/client.mjs";
import { ensureDir, readJson } from "./json.mjs";
import { packageForFile } from "./test_seed.mjs";

const PROCESS_TREE_RUNNER = fileURLToPath(
  new URL("./process_tree_runner.mjs", import.meta.url),
);

const SOURCE_EXCLUDES = [
  "--coverage.exclude",
  "**/*.test.ts",
  "--coverage.exclude",
  "**/*.test.tsx",
  "--coverage.exclude",
  "**/*.spec.ts",
  "--coverage.exclude",
  "**/*.spec.tsx",
  "--coverage.exclude",
  "**/*.d.ts",
  "--coverage.exclude",
  "**/node_modules/**",
  "--coverage.exclude",
  "**/dist/**",
  "--coverage.exclude",
  "**/out/**",
  "--coverage.exclude",
  "**/build/**",
  "--coverage.exclude",
  "**/coverage/**",
  "--coverage.exclude",
  "**/__tests__/**",
  "--coverage.exclude",
  "**/__mocks__/**",
  "--coverage.exclude",
  "**/__fixtures__/**",
];

function reporterCounts(reporterPath) {
  if (!fs.existsSync(reporterPath)) {
    return null;
  }
  try {
    const data = readJson(reporterPath);
    return {
      total: Number(data.numTotalTests ?? 0),
      passed: Number(data.numPassedTests ?? 0),
      failed: Number(data.numFailedTests ?? 0),
      skipped: Number(data.numPendingTests ?? 0),
    };
  } catch {
    return null;
  }
}

function statusFromRun({ exitCode, timedOut, coveragePath, counts }) {
  if (timedOut) {
    return "timeout";
  }
  if (exitCode !== 0 || Number(counts?.failed ?? 0) > 0) {
    return "failed";
  }
  if (!counts) {
    return "missing_reporter";
  }
  if (Number(counts.passed ?? 0) < 1) {
    return "no_tests";
  }
  if (!fs.existsSync(coveragePath)) {
    return "missing_coverage";
  }
  return "passed";
}

function exactTestPattern(testName) {
  const name = String(testName ?? "");
  if (!name) {
    throw new Error("generated test name is required");
  }
  return `${name.replace(/[.*+?^${}()|[\]\\]/gu, "\\$&")}$`;
}

function coverageArgs(pkg, coverageDir, filterArgs) {
  return [
    "--coverage",
    `--coverage.provider=${pkg.coverageProvider ?? "v8"}`,
    "--coverage.all=false",
    "--coverage.reporter=json",
    "--coverage.reporter=json-summary",
    "--coverage.reportOnFailure",
    "--coverage.reportsDirectory",
    coverageDir,
    "--coverage.thresholds.lines=0",
    "--coverage.thresholds.functions=0",
    "--coverage.thresholds.branches=0",
    "--coverage.thresholds.statements=0",
    ...filterArgs,
  ];
}

function ensurePackageNodeModules({
  sourceProjectRoot,
  runtimeProjectRoot,
  pkg,
}) {
  const source = path.join(sourceProjectRoot, pkg.cwd, "node_modules");
  const target = path.join(runtimeProjectRoot, pkg.cwd, "node_modules");
  if (!fs.existsSync(source) || fs.existsSync(target)) {
    return;
  }
  fs.symlinkSync(fs.realpathSync(source), target, "dir");
}

export function createPackageVitestAdapter({
  packages,
  launcher = ["pnpm", "exec", "vitest"],
  coverageFilterArgs = SOURCE_EXCLUDES,
  teardownTimeoutMs = null,
}) {
  function runTestFile({
    projectRoot,
    sourceProjectRoot,
    testFile,
    testName = "",
    outDir,
    timeoutSeconds = 600,
    env = process.env,
  }) {
    if (!projectRoot || !sourceProjectRoot) {
      throw new Error("projectRoot and sourceProjectRoot are required");
    }
    ensureDir(outDir);
    const pkg = packageForFile(packages, testFile);
    if (!pkg) {
      throw new Error(`no Vitest package for test file: ${testFile}`);
    }
    const packageRoot = path.join(projectRoot, pkg.cwd);
    ensurePackageNodeModules({
      sourceProjectRoot,
      runtimeProjectRoot: projectRoot,
      pkg,
    });
    const testArg = path
      .relative(packageRoot, path.join(projectRoot, testFile))
      .split(path.sep)
      .join("/");
    const coverageDir = path.join(outDir, "coverage");
    const reporterPath = path.join(outDir, "reporter.json");
    fs.rmSync(coverageDir, { recursive: true, force: true });
    fs.rmSync(reporterPath, { force: true });
    ensureDir(coverageDir);

    const runEnv = sanitizeEnvForSubprocess(env);
    runEnv.CI = runEnv.CI || "true";
    const command =
      typeof launcher === "function" ? launcher(runEnv) : launcher;
    if (!Array.isArray(command) || command.length === 0) {
      throw new Error("Vitest launcher must be a non-empty command array");
    }
    const cmd = [...command, "run"];
    if (pkg.config) {
      cmd.push("--config", pkg.config);
    }
    cmd.push(
      ...coverageArgs(pkg, coverageDir, coverageFilterArgs),
      "--reporter=json",
      "--outputFile",
      reporterPath,
    );
    if (testName) {
      cmd.push("--testNamePattern", exactTestPattern(testName));
    }
    if (teardownTimeoutMs !== null) {
      cmd.push(`--teardownTimeout=${Math.max(1, Math.floor(teardownTimeoutMs))}`);
    }
    cmd.push(testArg);

    let result;
    try {
      result = spawnSync(process.execPath, [PROCESS_TREE_RUNNER, ...cmd], {
        cwd: packageRoot,
        env: runEnv,
        encoding: "utf8",
        timeout: Math.max(1, Math.floor(timeoutSeconds * 1000)),
        maxBuffer: 20 * 1024 * 1024,
        detached: process.platform !== "win32",
      });
    } finally {
      // The supervisor exits even if descendants ignore TERM or retain pipes.
      if (process.platform !== "win32" && result?.pid > 0) {
        try {
          process.kill(-result.pid, "SIGKILL");
        } catch (error) {
          if (error.code !== "ESRCH") throw error;
        }
      }
    }
    const output = `${result.stdout ?? ""}${result.stderr ?? ""}`;

    const coveragePath = path.join(coverageDir, "coverage-final.json");
    const counts = reporterCounts(reporterPath);
    const timedOut = result.error?.code === "ETIMEDOUT";
    const exitCode =
      typeof result.status === "number" ? result.status : timedOut ? 124 : null;
    const status = statusFromRun({ exitCode, timedOut, coveragePath, counts });
    return {
      status,
      cmd,
      cwd: packageRoot,
      exit_code: exitCode,
      timed_out: timedOut,
      test_file: testFile,
      test_files: [testFile],
      test_name: testName,
      test_names: testName ? [testName] : [],
      coverage_json: fs.existsSync(coveragePath) ? coveragePath : "",
      reporter_json: fs.existsSync(reporterPath) ? reporterPath : "",
      test_counts: counts,
      output_tail: output.slice(-12000),
    };
  }

  const validateGeneratedTest = (request) => runTestFile(request);
  const measureTestFileCoverage = (request) => runTestFile(request);
  return {
    measureTestFileCoverage,
    validateGeneratedTest,
  };
}
