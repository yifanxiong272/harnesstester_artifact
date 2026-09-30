import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { ensureDir, readJson, writeJson } from "../support/json.mjs";
import { spawnManagedSync } from "./process.mjs";
import { removeManagedPaths } from "../support/storage.mjs";
import {
  configuredCommand,
  resolveLocalLauncher,
  resolvedVitestConfig,
  writeVitestConfigOverride,
  ensureProjectEnv,
  sandboxedCommand,
} from "./vitest_config.mjs";
import {
  reporterCounts,
  reporterFailures,
  failureExcerpt,
  failedNodeids,
  validationOutcome,
  structuredDiagnostics,
} from "./vitest_evidence.mjs";

const MAX_PERSISTED_LOG_BYTES = 2 * 1024 * 1024;
const MAX_PERSISTED_REPORTER_BYTES = 4 * 1024 * 1024;
const STRUCTURED_REPORTER_SOURCE = fileURLToPath(
  new URL("./vitest_structured_reporter.mjs", import.meta.url),
);

function reporterData(reporterPath) {
  try {
    return readJson(reporterPath);
  } catch {
    return null;
  }
}

function boundedLog(command, output) {
  const prefix = `$ ${command.join(" ")}${os.EOL}${os.EOL}`;
  const full = `${prefix}${output}`;
  const buffer = Buffer.from(full);
  const originalBytes = buffer.length;
  const truncated = originalBytes > MAX_PERSISTED_LOG_BYTES;
  let text = full;
  if (truncated) {
    const head = buffer.subarray(0, 128 * 1024).toString("utf8");
    const marker = `${os.EOL}${os.EOL}[truncated ${originalBytes - MAX_PERSISTED_LOG_BYTES} bytes]${os.EOL}${os.EOL}`;
    const tailBudget =
      MAX_PERSISTED_LOG_BYTES -
      Buffer.byteLength(head) -
      Buffer.byteLength(marker);
    const tail = buffer.subarray(-Math.max(0, tailBudget)).toString("utf8");
    text = `${head}${marker}${tail}`;
  }
  return {
    text,
    original_bytes: originalBytes,
    persisted_bytes: truncated ? Buffer.byteLength(text) : originalBytes,
    truncated,
  };
}

function compactReporter(reporterPath, reporter, counts, failures) {
  const originalBytes = fs.existsSync(reporterPath)
    ? fs.statSync(reporterPath).size
    : 0;
  const compacted = originalBytes > MAX_PERSISTED_REPORTER_BYTES;
  if (compacted) {
    writeJson(reporterPath, {
      schema: "test-augment-ts-br-compacted-vitest-reporter-v1",
      original_bytes: originalBytes,
      test_counts: counts,
      failures,
      success: Boolean(reporter?.success),
    });
  }
  return {
    original_bytes: originalBytes,
    persisted_bytes: compacted ? fs.statSync(reporterPath).size : originalBytes,
    compacted,
  };
}

function runVitestAttempt({
  projectRoot,
  testFile,
  configuredCmd,
  outDir,
  reporterModulePath,
  timeoutSeconds,
  runEnv,
  forceExactInclude = false,
}) {
  const reporterPath = path.join(outDir, "reporter.json");
  const logPath = path.join(outDir, "vitest.log");
  const {
    command: validationConfiguredCmd,
    override: vitestConfigOverride,
    adjustment: vitestConfigAdjustment,
    scratchPaths,
  } = writeVitestConfigOverride({
    command: configuredCmd,
    projectRoot,
    outDir,
    testFile,
    forceExactInclude,
  });
  const hasConfigLoader = validationConfiguredCmd.some(
    (part) => part === "--configLoader" || part.startsWith("--configLoader="),
  );
  const requestedCmd = [
    ...resolveLocalLauncher(validationConfiguredCmd, projectRoot),
    "--no-cache",
    ...(hasConfigLoader ? [] : ["--configLoader=runner"]),
    "--no-file-parallelism",
    "--maxWorkers=1",
    "--reporter",
    reporterModulePath,
    "--outputFile",
    reporterPath,
  ];
  const {
    command: cmd,
    network_sandboxed: networkSandboxed,
    filesystem_sandboxed: filesystemSandboxed,
  } = sandboxedCommand(requestedCmd, { projectRoot, outDir, testFile });
  const managed = spawnManagedSync(cmd[0], cmd.slice(1), {
    cwd: projectRoot,
    env: { ...runEnv, TEST_AUGMENT_VITEST_REPORT: reporterPath },
    encoding: "utf8",
    timeout: timeoutSeconds * 1000,
    maxBuffer: 20 * 1024 * 1024,
  });
  const { result } = managed;
  const output = `${result.stdout || ""}${result.stderr || ""}`;
  const log = boundedLog(cmd, output);
  fs.writeFileSync(logPath, log.text);
  const timedOut =
    result.error?.code === "ETIMEDOUT" || result.signal === "SIGTERM";
  const exitCode =
    typeof result.status === "number" ? result.status : timedOut ? 124 : null;
  const reporter = reporterData(reporterPath);
  const counts = reporterCounts(reporter);
  const failures = reporterFailures(reporter);
  const classification = validationOutcome({
    exitCode,
    timedOut,
    reporter,
    testFile,
  });
  const status = classification.status;
  const excerpt = !reporter
    ? "Vitest did not produce a readable JSON reporter."
    : Number(counts.total || 0) === 0
      ? "No tests were collected for the generated test file."
      : failureExcerpt(output, failures);
  const reporterStorage = compactReporter(
    reporterPath,
    reporter,
    counts,
    failures,
  );
  return {
    reporter,
    scratchPaths,
    payload: {
      schema: "test-augment-ts-br-vitest-validation-v1",
      status,
      classification,
      cmd,
      configured_cmd: configuredCmd,
      requested_cmd: requestedCmd,
      vitest_config_override: vitestConfigOverride,
      vitest_config_adjustment: vitestConfigAdjustment,
      network_sandboxed: networkSandboxed,
      filesystem_sandboxed: filesystemSandboxed,
      cwd: projectRoot,
      exit_code: exitCode,
      signal: result.signal || "",
      timed_out: timedOut,
      test_file: testFile,
      test_counts: counts,
      reporter_json: fs.existsSync(reporterPath) ? reporterPath : "",
      reporter_storage: reporterStorage,
      log_path: logPath,
      log_storage: {
        original_bytes: log.original_bytes,
        persisted_bytes: log.persisted_bytes,
        truncated: log.truncated,
      },
      process_group_cleanup: managed.process_group_cleanup,
      output_tail: output.slice(-8000),
      evidence: {
        passed: status === "passed",
        status,
        classification_source: classification.source,
        classification_reason: classification.reason,
        failed_hooks: classification.failed_hooks || [],
        diagnostics: structuredDiagnostics(reporter),
        failed_nodeids:
          status === "passed" ? [] : failedNodeids(output, failures),
        failure_excerpt: status === "passed" ? "" : excerpt,
      },
    },
  };
}

function isUndiscoveredGeneratedTest(attempt) {
  const reporter = attempt.reporter;
  return (
    attempt.payload.classification.reason === "test_not_executed" &&
    reporter?.schema === "test-augment-vitest-structured-report" &&
    Number(reporter.module_count ?? reporter.modules?.length ?? 0) === 0 &&
    Number(reporter.test_count ?? reporter.tests?.length ?? 0) === 0 &&
    Number(
      reporter.unhandled_error_count ?? reporter.unhandled_errors?.length ?? 0,
    ) === 0
  );
}

function preserveInitialAttemptArtifacts(attempt, outDir) {
  const mappings = [
    [
      attempt.payload.reporter_json,
      path.join(outDir, "reporter.initial.json"),
      "reporter_json",
    ],
    [
      attempt.payload.log_path,
      path.join(outDir, "vitest.initial.log"),
      "log_path",
    ],
  ];
  for (const [source, destination, field] of mappings) {
    if (!source || !fs.existsSync(source)) {
      continue;
    }
    fs.renameSync(source, destination);
    attempt.payload[field] = destination;
  }
}

function collectionRetryRecord(initial) {
  return {
    attempted: true,
    trigger: "structured_zero_collection",
    initial: {
      status: initial.status,
      classification: initial.classification,
      cmd: initial.cmd,
      requested_cmd: initial.requested_cmd,
      vitest_config_override: initial.vitest_config_override,
      vitest_config_adjustment: initial.vitest_config_adjustment,
      exit_code: initial.exit_code,
      signal: initial.signal,
      timed_out: initial.timed_out,
      test_counts: initial.test_counts,
      reporter_json: initial.reporter_json,
      reporter_storage: initial.reporter_storage,
      log_path: initial.log_path,
      log_storage: initial.log_storage,
      process_group_cleanup: initial.process_group_cleanup,
      output_tail: initial.output_tail,
      evidence: initial.evidence,
    },
  };
}

export function validateVitest({
  projectRoot,
  testFile,
  testCommand,
  outDir,
  timeoutSeconds = 240,
  env = process.env,
}) {
  ensureDir(outDir);
  const { env: runEnv, scratchPaths } = ensureProjectEnv(outDir, env);
  const nodeBin = path.join(projectRoot, "node_modules", ".bin");
  if (fs.existsSync(path.join(nodeBin, "node"))) {
    runEnv.PATH = `${nodeBin}${path.delimiter}${runEnv.PATH || ""}`;
  }
  let payload = null;
  let validationScratchPaths = [];
  try {
    const configuredCmd = configuredCommand(testCommand, testFile);
    const reporterModulePath = path.join(
      outDir,
      "vitest.structured-reporter.mjs",
    );
    const reporterPackagePath = path.join(outDir, "package.json");
    fs.copyFileSync(STRUCTURED_REPORTER_SOURCE, reporterModulePath);
    fs.writeFileSync(
      reporterPackagePath,
      `${JSON.stringify({ type: "module" })}\n`,
    );
    validationScratchPaths.push(reporterModulePath, reporterPackagePath);
    const attemptOptions = {
      projectRoot,
      testFile,
      configuredCmd,
      outDir,
      reporterModulePath,
      timeoutSeconds,
      runEnv,
    };
    const initial = runVitestAttempt(attemptOptions);
    validationScratchPaths.push(...initial.scratchPaths);
    payload = initial.payload;

    const retryConfig = resolvedVitestConfig(configuredCmd, projectRoot, {
      discoverDefault: true,
    });
    if (
      isUndiscoveredGeneratedTest(initial) &&
      retryConfig &&
      fs.existsSync(retryConfig.path)
    ) {
      preserveInitialAttemptArtifacts(initial, outDir);
      const retry = runVitestAttempt({
        ...attemptOptions,
        forceExactInclude: true,
      });
      validationScratchPaths.push(...retry.scratchPaths);
      payload = retry.payload;
      payload.collection_retry = collectionRetryRecord(initial.payload);
    }
    return payload;
  } finally {
    const cleanup = removeManagedPaths([
      ...new Set([...scratchPaths, ...validationScratchPaths]),
    ]);
    if (payload) {
      payload.scratch_cleanup = cleanup;
    }
  }
}
