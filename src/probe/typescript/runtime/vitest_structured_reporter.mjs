import fs from "node:fs";
import path from "node:path";

const REPORT_PATH_ENV = "TEST_AUGMENT_VITEST_REPORT";
const MAX_MESSAGE_CHARS = 4_000;
const MAX_STACK_CHARS = 12_000;
const MAX_UNHANDLED_ERRORS = 20;
const MAX_MODULE_RECORDS = 100;
const MAX_TEST_RECORDS = 500;

function boundedText(value, limit) {
  const text = String(value || "");
  return text.length <= limit ? text : `${text.slice(0, limit - 3)}...`;
}

function errorRecord(error) {
  const name = String(error?.name || error?.constructor?.name || "");
  return {
    name,
    message: boundedText(error?.message || error, MAX_MESSAGE_CHARS),
    stack: boundedText(error?.stack, MAX_STACK_CHARS),
    is_assertion: name === "AssertionError",
  };
}

function hookStates(task) {
  const hooks = task?.result?.hooks;
  if (!hooks || typeof hooks !== "object") {
    return {};
  }
  return Object.fromEntries(
    Object.entries(hooks).map(([name, state]) => [name, String(state || "")]),
  );
}

function mergedHookStates(records, entity) {
  return {
    ...hookStates(entity.task),
    ...(records.get(entity.id) || {}),
  };
}

function testRecord(testCase, hookRecords) {
  const result = testCase.result();
  return {
    id: testCase.id,
    module_id: testCase.module.moduleId,
    module_path: testCase.module.relativeModuleId,
    name: testCase.fullName,
    state: result.state,
    ready: true,
    hooks: mergedHookStates(hookRecords, testCase),
    errors: (result.errors || []).map(errorRecord),
  };
}

function moduleRecord(testModule, lifecycle, hookRecords) {
  return {
    module_id: testModule.moduleId,
    module_path: testModule.relativeModuleId,
    state: testModule.state(),
    queued: lifecycle.queued.has(testModule.moduleId),
    collected: lifecycle.collected.has(testModule.moduleId),
    started: lifecycle.started.has(testModule.moduleId),
    hooks: mergedHookStates(hookRecords, testModule),
    errors: testModule.errors().map(errorRecord),
  };
}

function writeReport(payload) {
  const reportPath = process.env[REPORT_PATH_ENV];
  if (!reportPath) {
    return;
  }
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  const temporaryPath = `${reportPath}.tmp-${process.pid}`;
  fs.writeFileSync(temporaryPath, `${JSON.stringify(payload, null, 2)}\n`);
  fs.renameSync(temporaryPath, reportPath);
}

export default class TestAugmentReporter {
  lifecycle = {
    queued: new Set(),
    collected: new Set(),
    started: new Set(),
  };

  tests = new Map();

  observedTestIds = new Set();

  hooks = new Map();

  recordHook(hook, fallbackState) {
    const current = this.hooks.get(hook.entity.id) || {};
    const state = hookStates(hook.entity.task)[hook.name] || fallbackState;
    this.hooks.set(hook.entity.id, { ...current, [hook.name]: state });
  }

  onTestModuleQueued(testModule) {
    this.lifecycle.queued.add(testModule.moduleId);
  }

  onTestModuleCollected(testModule) {
    this.lifecycle.collected.add(testModule.moduleId);
  }

  onTestModuleStart(testModule) {
    this.lifecycle.started.add(testModule.moduleId);
  }

  onTestCaseResult(testCase) {
    this.observedTestIds.add(testCase.id);
    if (this.tests.has(testCase.id) || this.tests.size < MAX_TEST_RECORDS) {
      this.tests.set(testCase.id, testRecord(testCase, this.hooks));
    }
  }

  onHookStart(hook) {
    this.recordHook(hook, "run");
  }

  onHookEnd(hook) {
    this.recordHook(hook, "pass");
  }

  onTestRunEnd(testModules, unhandledErrors, reason) {
    for (const testModule of testModules) {
      for (const testCase of testModule.children.allTests()) {
        this.onTestCaseResult(testCase);
      }
    }
    const modules = testModules.slice(0, MAX_MODULE_RECORDS);
    writeReport({
      schema: "test-augment-vitest-structured-report",
      reason,
      module_count: testModules.length,
      modules_truncated: testModules.length > modules.length,
      modules: modules.map((testModule) =>
        moduleRecord(testModule, this.lifecycle, this.hooks),
      ),
      test_count: this.observedTestIds.size,
      tests_truncated: this.observedTestIds.size > this.tests.size,
      tests: [...this.tests.values()],
      unhandled_error_count: unhandledErrors.length,
      unhandled_errors: unhandledErrors
        .slice(0, MAX_UNHANDLED_ERRORS)
        .map(errorRecord),
    });
  }
}
