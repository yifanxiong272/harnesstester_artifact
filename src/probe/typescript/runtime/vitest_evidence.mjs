/** Classify structured Vitest evidence and retain failure diagnostics. */
import { normalizePath } from "../support/path_safety.mjs";

export function reporterCounts(data) {
  if (!data) {
    return {};
  }
  if (data.schema === "test-augment-vitest-structured-report") {
    const tests = Array.isArray(data.tests) ? data.tests : [];
    return {
      total: tests.length,
      passed: tests.filter((test) => test.state === "passed").length,
      failed: tests.filter((test) => test.state === "failed").length,
      skipped: tests.filter((test) => test.state === "skipped").length,
    };
  }
  return {
    total: Number(data.numTotalTests ?? 0),
    passed: Number(data.numPassedTests ?? 0),
    failed: Number(data.numFailedTests ?? 0),
    skipped: Number(data.numPendingTests ?? 0),
  };
}

export function reporterFailures(data) {
  const failures = [];
  const appendErrors = (nodeid, errors) => {
    for (const error of errors || []) {
      failures.push({
        nodeid,
        ...error,
        message: String(error.stack || error.message || ""),
      });
    }
  };
  if (data?.schema === "test-augment-vitest-structured-report") {
    for (const module of data.modules || []) {
      appendErrors(
        String(module.module_path || module.module_id || ""),
        module.errors,
      );
    }
    for (const test of data.tests || []) {
      appendErrors(
        [test.module_path || test.module_id, test.name]
          .filter(Boolean)
          .join(" > "),
        test.errors,
      );
    }
    appendErrors("<unhandled>", data.unhandled_errors);
    return failures.filter((item) => item.message || item.nodeid);
  }
  for (const suite of data?.testResults || []) {
    const suiteName = String(suite.name || suite.testFilePath || "");
    if (suite.message) {
      failures.push({ nodeid: suiteName, message: String(suite.message) });
    }
    for (const assertion of suite.assertionResults || []) {
      if (assertion.status !== "failed") {
        continue;
      }
      const name = [suiteName, assertion.fullName || assertion.title]
        .filter(Boolean)
        .join(" > ");
      const message = Array.isArray(assertion.failureMessages)
        ? assertion.failureMessages.join("\n")
        : String(assertion.failureMessages || assertion.failureMessage || "");
      failures.push({ nodeid: name, message });
    }
  }
  return failures.filter((item) => item.message || item.nodeid);
}

export function failureExcerpt(output, failures, limit = 2400) {
  const reporterText = failures
    .map((item) => item.message)
    .filter(Boolean)
    .join("\n\n");
  if (reporterText) {
    return reporterText.slice(0, limit).trim();
  }
  const text = String(output || "");
  for (const marker of [
    " FAIL ",
    " FAILURES ",
    "Error:",
    "AssertionError",
    "TypeError",
    "ReferenceError",
    "No test files found",
  ]) {
    const index = text.indexOf(marker);
    if (index >= 0) {
      return text.slice(index, index + limit).trim();
    }
  }
  return text.slice(-limit).trim();
}

export function failedNodeids(output, failures) {
  const ids = new Set();
  for (const failure of failures) {
    if (failure.nodeid) {
      ids.add(failure.nodeid);
    }
  }
  for (const line of String(output || "").split(/\r?\n/u)) {
    const match =
      /(?:FAIL|FAILED)\s+([^\s]+\.test\.[tj]sx?(?:\s*>\s*.+)?)/u.exec(
        line.trim(),
      );
    if (match) {
      ids.add(match[1]);
    }
  }
  return [...ids].sort();
}

function nodeidMatchesTestFile(nodeid, testFile) {
  const normalized = normalizePath(nodeid);
  const expected = normalizePath(testFile);
  return (
    normalized === expected ||
    normalized.includes(`/${expected}`) ||
    normalized.startsWith(`${expected} >`)
  );
}

function failedHooks(record) {
  return Object.entries(record?.hooks || {})
    .filter(
      ([, state]) => state === "run" || state === "fail" || state === "failed",
    )
    .map(([name]) => name)
    .sort();
}

function recordsForTest(records, testFile) {
  return (records || []).filter(
    (record) =>
      nodeidMatchesTestFile(record.module_path, testFile) ||
      nodeidMatchesTestFile(record.module_id, testFile),
  );
}

function outcome(
  reason,
  status = "needs_repair",
  source = "structured_reporter",
) {
  return { status, source, reason };
}

export function validationOutcome({ exitCode, timedOut, reporter, testFile }) {
  if (timedOut) {
    return outcome("timeout", "needs_repair", "process");
  }
  if (reporter?.schema !== "test-augment-vitest-structured-report") {
    return outcome("structured_report_unavailable", "needs_repair", "process");
  }
  if (reporter.modules_truncated || reporter.tests_truncated) {
    return outcome("structured_report_truncated");
  }
  const modules = recordsForTest(reporter.modules, testFile);
  const module = modules.length === 1 ? modules[0] : null;
  const tests = recordsForTest(reporter.tests, testFile);
  if (!module || tests.length === 0 || !module.collected || !module.started) {
    return outcome("test_not_executed");
  }
  const moduleErrors = module.errors || [];
  const unhandledErrors = reporter.unhandled_errors || [];
  const unhandledErrorCount = Number(
    reporter.unhandled_error_count ?? unhandledErrors.length,
  );
  const failedHookNames = [
    ...new Set([
      ...failedHooks(module),
      ...tests.flatMap((test) => failedHooks(test)),
    ]),
  ].sort();
  const cleanExecution =
    moduleErrors.length === 0 &&
    unhandledErrorCount === 0 &&
    failedHookNames.length === 0;
  if (
    exitCode === 0 &&
    tests.every((test) => test.state === "passed") &&
    cleanExecution
  ) {
    return outcome("completed_pass", "passed");
  }
  const failedTests = tests.filter((test) => test.state === "failed");
  if (
    exitCode === 1 &&
    failedTests.length > 0 &&
    tests.every((test) => ["passed", "failed"].includes(test.state)) &&
    failedTests.every(
      (test) =>
        (test.errors || []).length > 0 &&
        (test.errors || []).every((error) => error.is_assertion === true),
    ) &&
    cleanExecution
  ) {
    return outcome("call_assertion_only", "assertion_failed");
  }
  return {
    ...outcome("non_assertion_or_incomplete_execution"),
    failed_hooks: failedHookNames,
  };
}

export function structuredDiagnostics(reporter) {
  if (reporter?.schema !== "test-augment-vitest-structured-report") {
    return {};
  }
  return {
    module_count: Number(
      reporter.module_count ?? (reporter.modules || []).length,
    ),
    modules_truncated: Boolean(reporter.modules_truncated),
    test_count: Number(reporter.test_count ?? (reporter.tests || []).length),
    tests_truncated: Boolean(reporter.tests_truncated),
    modules: (reporter.modules || []).map((module) => ({
      module_path: module.module_path || module.module_id || "",
      state: module.state || "",
      collected: Boolean(module.collected),
      started: Boolean(module.started),
      hooks: module.hooks || {},
      errors: module.errors || [],
    })),
    tests: (reporter.tests || []).map((test) => ({
      nodeid: [test.module_path || test.module_id, test.name]
        .filter(Boolean)
        .join(" > "),
      state: test.state || "",
      hooks: test.hooks || {},
      errors: test.errors || [],
    })),
    unhandled_error_count: Number(
      reporter.unhandled_error_count ?? reporter.unhandled_errors?.length ?? 0,
    ),
    unhandled_errors: reporter.unhandled_errors || [],
  };
}
