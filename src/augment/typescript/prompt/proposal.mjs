import path from "node:path";

import { parseTypeScript } from "../typescript_ast.mjs";

const VI_METHODS = new Set([
  "clearAllMocks",
  "doMock",
  "doUnmock",
  "fn",
  "mock",
  "mocked",
  "resetAllMocks",
  "resetModules",
  "restoreAllMocks",
  "spyOn",
  "unmock",
]);
const NON_SINGLE_TEST_MODIFIERS = new Set([
  "each",
  "for",
  "runIf",
  "skip",
  "skipIf",
  "todo",
]);
const MAX_TEST_UNITS = 4;

function parseJsonObject(content, label = "proposal") {
  if (typeof content === "object" && content !== null) {
    return content;
  }
  let text = String(content ?? "").trim();
  if (text.startsWith("```")) {
    text = text.replace(/^```(?:json)?\s*/u, "").replace(/\s*```$/u, "");
  }
  const data = JSON.parse(text);
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error(`${label} must be a JSON object`);
  }
  return data;
}

function requireString(data, key) {
  const value = data[key];
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`proposal missing string field: ${key}`);
  }
  return value;
}

function optionalString(data, key) {
  return typeof data?.[key] === "string" ? data[key] : "";
}

function optionalPositiveInteger(data, key) {
  const value = Number(data?.[key]);
  return Number.isInteger(value) && value > 0 ? value : null;
}

function projectRelativePath(data, key) {
  const value = requireString(data, key).replace(/\\/gu, "/");
  const normalized = path.posix.normalize(value);
  if (
    path.posix.isAbsolute(value) ||
    value.includes("\0") ||
    /^[a-zA-Z]:\//u.test(value) ||
    normalized !== value ||
    normalized === ".." ||
    normalized.startsWith("../")
  ) {
    throw new Error(`proposal field must be a project-relative path: ${key}`);
  }
  return value;
}

function stringList(value, field) {
  if (value == null) {
    return [];
  }
  if (!Array.isArray(value)) {
    throw new Error(`proposal field must be a list: ${field}`);
  }
  return value.map((item) => String(item));
}

export function validateGeneratedTestPath(testFile, seedTestFile) {
  if (typeof testFile !== "string" || !testFile || testFile.includes("\0")) {
    throw new Error(`unsafe test_file: ${testFile}`);
  }
  const normalized = testFile.replace(/\\/gu, "/");
  const parsed = path.posix.normalize(normalized);
  if (
    path.posix.isAbsolute(normalized) ||
    /^[a-zA-Z]:\//u.test(normalized) ||
    parsed !== normalized ||
    parsed === ".." ||
    parsed.startsWith("../")
  ) {
    throw new Error(`unsafe test_file: ${testFile}`);
  }
  if (
    typeof seedTestFile !== "string" ||
    !seedTestFile ||
    seedTestFile.includes("\0")
  ) {
    throw new Error(`unsafe seed_test_file: ${seedTestFile}`);
  }
  const normalizedSeed = seedTestFile.replace(/\\/gu, "/");
  const seed = path.posix.normalize(normalizedSeed);
  if (
    !normalizedSeed ||
    path.posix.isAbsolute(normalizedSeed) ||
    /^[a-zA-Z]:\//u.test(normalizedSeed) ||
    seed !== normalizedSeed ||
    seed === ".." ||
    seed.startsWith("../")
  ) {
    throw new Error(`unsafe seed_test_file: ${seedTestFile}`);
  }
  if (
    parsed === seed ||
    path.posix.dirname(parsed) !== path.posix.dirname(seed)
  ) {
    throw new Error(
      `generated test must be a sibling of its seed test: ${testFile}`,
    );
  }
  if (!path.posix.basename(parsed).startsWith("test-augment-")) {
    throw new Error(
      `generated test must use the test-augment prefix: ${testFile}`,
    );
  }
  if (!/\.tsx?$/u.test(parsed)) {
    throw new Error(`generated test must be TypeScript: ${testFile}`);
  }
}

function stripCodeFence(code) {
  let text = String(code ?? "").trim();
  if (text.startsWith("```")) {
    text = text
      .replace(/^```(?:typescript|ts|javascript|js)?\s*/u, "")
      .replace(/\s*```$/u, "");
  }
  return text;
}

function rootIdentifier(typescript, expression) {
  let current = expression;
  while (
    typescript.isPropertyAccessExpression(current) ||
    typescript.isElementAccessExpression(current)
  ) {
    current = current.expression;
  }
  if (typescript.isCallExpression(current)) {
    return rootIdentifier(typescript, current.expression);
  }
  return typescript.isIdentifier(current) ? current.text : null;
}

function isTestRegistration(typescript, call) {
  if (
    typescript.isCallExpression(call.parent) &&
    call.parent.expression === call
  ) {
    return false;
  }
  const root = rootIdentifier(typescript, call.expression);
  if (root === "it" || root === "test") return true;
  if (!root?.startsWith("__testAugmentVitest_")) return false;

  let expression = call.expression;
  while (typescript.isCallExpression(expression)) {
    expression = expression.expression;
  }
  while (typescript.isPropertyAccessExpression(expression)) {
    if (expression.name.text === "it" || expression.name.text === "test") {
      return true;
    }
    expression = expression.expression;
  }
  return false;
}

function registrationModifier(typescript, expression, modifiers) {
  let current = expression;
  while (typescript.isCallExpression(current)) {
    current = current.expression;
  }
  while (typescript.isPropertyAccessExpression(current)) {
    if (modifiers.has(current.name.text)) return current.name.text;
    current = current.expression;
  }
  return null;
}

function validateTestSyntax(text, typescript, expectedNameSuffix) {
  if (!typescript) {
    throw new Error(
      "TypeScript compiler is required to validate generated tests",
    );
  }
  const sourceFile = parseTypeScript(typescript, "generated.test.ts", text);
  if (sourceFile.parseDiagnostics.length > 0) {
    const diagnostic = sourceFile.parseDiagnostics[0];
    const message = typescript.flattenDiagnosticMessageText(
      diagnostic.messageText,
      " ",
    );
    throw new Error(`proposal append_code is not valid TypeScript: ${message}`);
  }

  const statements = sourceFile.statements.filter(
    (statement) => !typescript.isEmptyStatement(statement),
  );
  const registration = statements[0];
  if (
    statements.length !== 1 ||
    !typescript.isExpressionStatement(registration) ||
    !typescript.isCallExpression(registration.expression) ||
    !isTestRegistration(typescript, registration.expression)
  ) {
    throw new Error(
      "proposal append_code must contain exactly one top-level it/test registration; keep mocks, fixtures, and helpers inside its callback",
    );
  }
  const title = registration.expression.arguments[0];
  if (!typescript.isStringLiteralLike(title)) {
    throw new Error("generated test name must be a static string literal");
  }
  const modifier = registrationModifier(
    typescript,
    registration.expression.expression,
    NON_SINGLE_TEST_MODIFIERS,
  );
  if (modifier) {
    throw new Error(
      `generated test must register one unconditional case; .${modifier} is not allowed`,
    );
  }
  if (expectedNameSuffix && !title.text.endsWith(expectedNameSuffix)) {
    throw new Error(
      `generated test name must end with ${expectedNameSuffix}: ${title.text}`,
    );
  }

  let testCalls = 0;
  let usesJest = false;
  let directViMethod = null;
  function visit(node) {
    if (
      typescript.isImportDeclaration(node) &&
      node.moduleSpecifier.text === "@jest/globals"
    ) {
      usesJest = true;
    }
    if (typescript.isIdentifier(node) && node.text === "jest") {
      usesJest = true;
    }
    if (
      typescript.isPropertyAccessExpression(node) &&
      typescript.isIdentifier(node.expression) &&
      node.expression.text.startsWith("__testAugmentVitest_") &&
      VI_METHODS.has(node.name.text)
    ) {
      directViMethod = node.name.text;
    }
    if (
      typescript.isCallExpression(node) &&
      isTestRegistration(typescript, node)
    ) {
      testCalls += 1;
    }
    typescript.forEachChild(node, visit);
  }
  visit(sourceFile);

  if (usesJest) {
    throw new Error(
      "proposal append_code uses Jest APIs; generated tests must use Vitest APIs",
    );
  }
  if (directViMethod) {
    throw new Error(
      `proposal must call Vitest mock API as namespace.vi.${directViMethod}`,
    );
  }
  if (testCalls !== 1) {
    throw new Error(
      `each generated TypeScript test unit must contain exactly one it/test call; found ${testCalls}`,
    );
  }
  return title.text;
}

function normalizeAppendCode(code, typescript, expectedNameSuffix) {
  const text = stripCodeFence(code);
  return {
    code: text,
    testName: validateTestSyntax(text, typescript, expectedNameSuffix),
  };
}

function parseTestUnit(item, index, typescript, expectedNameSuffix) {
  if (!item || typeof item !== "object" || Array.isArray(item)) {
    throw new Error(`test_units[${index}] must be an object`);
  }
  const normalized = normalizeAppendCode(
    requireString(item, "append_code"),
    typescript,
    expectedNameSuffix,
  );
  return {
    label: optionalString(item, "label") || `unit-${index + 1}`,
    append_code: normalized.code,
    test_name: normalized.testName,
    targeted_objective_ids: stringList(
      item.targeted_objective_ids,
      "targeted_objective_ids",
    ),
    targeted_lines: stringList(item.targeted_lines, "targeted_lines"),
    targeted_branch_slots: stringList(
      item.targeted_branch_slots,
      "targeted_branch_slots",
    ),
    mocking_strategy: optionalString(item, "mocking_strategy"),
    oracle: optionalString(item, "oracle"),
    risk_notes: stringList(item.risk_notes, "risk_notes"),
  };
}

export function parseProposalBatch(
  content,
  { typescript, expectedNameSuffix = "" } = {},
) {
  let data;
  try {
    data = parseJsonObject(content);
  } catch (error) {
    throw new Error(`proposal is not valid JSON: ${error.message}`);
  }

  const rawUnits = Array.isArray(data.test_units)
    ? data.test_units
    : [
        {
          label:
            optionalString(data, "label") ||
            path.basename(optionalString(data, "test_file") || "generated"),
          append_code: data.append_code,
          targeted_objective_ids: data.targeted_objective_ids,
          targeted_lines: data.targeted_lines,
          targeted_branch_slots: data.targeted_branch_slots,
          mocking_strategy: data.mocking_strategy,
          oracle: data.oracle,
          risk_notes: data.risk_notes,
        },
      ];
  if (rawUnits.length === 0) {
    throw new Error("proposal must contain at least one test unit");
  }
  if (rawUnits.length > MAX_TEST_UNITS) {
    throw new Error(`proposal must contain at most ${MAX_TEST_UNITS} test units`);
  }
  return {
    rationale: optionalString(data, "rationale"),
    suite_id: requireString(data, "suite_id"),
    test_units: rawUnits.map((item, index) =>
      parseTestUnit(item, index, typescript, expectedNameSuffix),
    ),
  };
}

export function parseContextRequestBatch(content) {
  let data;
  try {
    data = parseJsonObject(content, "context request batch");
  } catch (error) {
    throw new Error(
      `context request batch is not valid JSON: ${error.message}`,
    );
  }
  const requests = data.requests ?? data.context_requests ?? [];
  if (!Array.isArray(requests)) {
    throw new Error("context requests must be a list");
  }
  return requests.map((item, index) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) {
      throw new Error(`context request ${index} must be an object`);
    }
    const startLine = optionalPositiveInteger(item, "start_line");
    const endLine = optionalPositiveInteger(item, "end_line");
    if (startLine !== null && endLine !== null && endLine < startLine) {
      throw new Error("proposal field end_line must not precede start_line");
    }
    return {
      kind: requireString(item, "kind"),
      filepath: projectRelativePath(item, "filepath"),
      qualname: optionalString(item, "qualname"),
      reason: optionalString(item, "reason"),
      start_line: startLine,
      end_line: endLine,
    };
  });
}

/**
 * Parse one turn of the direct generation conversation.
 *
 * The model may request one deterministic context batch before returning a
 * normal proposal batch. Proposal syntax is validated later with the project
 * TypeScript compiler.
 */
export function parseModelResponse(content) {
  let data;
  try {
    data = parseJsonObject(content, "model response");
  } catch (error) {
    throw new Error(`model response is not valid JSON: ${error.message}`);
  }
  const action = requireString(data, "action");
  const diagnosis = optionalString(data, "diagnosis");
  if (action === "request_context") {
    const requests = parseContextRequestBatch(data);
    if (requests.length === 0) {
      throw new Error("context action must contain at least one request");
    }
    return { action, diagnosis, requests };
  }
  if (action === "propose_test") {
    const proposal =
      data.proposal &&
      typeof data.proposal === "object" &&
      !Array.isArray(data.proposal)
        ? data.proposal
        : Object.fromEntries(
            Object.entries(data).filter(
              ([key]) => !["action", "diagnosis"].includes(key),
            ),
          );
    return { action, diagnosis, proposal };
  }
  throw new Error(`unsupported model response action: ${action}`);
}
