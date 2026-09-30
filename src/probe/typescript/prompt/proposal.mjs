import path from "node:path";
import crypto from "node:crypto";

import {
  loadTypeScript,
  parseSource,
  walkAst,
  stringLiteralText,
  isFunctionValue,
  moduleReference,
} from "../support/typescript.mjs";

export const SUPPORTED_CONTEXT_REQUEST_KINDS = new Set([
  "module_context",
  "class_definition",
  "function_definition",
  "symbol_definition",
]);

const SAFE_ID_RE = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$/u;
const ORACLE_MODES = new Set(["assertion", "exception", "crash"]);
const FORBIDDEN_RUNTIME_IMPORTS = new Set([
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
]);
const FORBIDDEN_GLOBAL_CALLS = new Set(["eval", "fetch"]);
const FORBIDDEN_GLOBAL_CONSTRUCTORS = new Set([
  "EventSource",
  "Function",
  "WebSocket",
]);
const FORBIDDEN_GLOBAL_OBJECTS = new Set(["Bun", "Deno"]);
const FORBIDDEN_PROCESS_MEMBERS = new Set([
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
]);

export function extractJson(content, label = "proposal") {
  if (content && typeof content === "object" && !Array.isArray(content)) {
    return content;
  }
  let text = String(content ?? "").trim();
  const fence = /^```(?:json)?\s*([\s\S]*?)\s*```$/u.exec(text);
  if (fence) {
    text = fence[1].trim();
  }
  const data = JSON.parse(text);
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error(`${label} must be a JSON object`);
  }
  return data;
}

function stringField(data, key, { required = true } = {}) {
  const value = data?.[key];
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }
  if (required) {
    throw new Error(`missing required string field: ${key}`);
  }
  return "";
}

function enumField(data, key, allowed) {
  const value = stringField(data, key);
  if (!allowed.has(value)) {
    throw new Error(`${key} must be one of: ${[...allowed].join(", ")}`);
  }
  return value;
}

function objectField(data, key) {
  const value = data?.[key];
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`missing required object field: ${key}`);
  }
  return value;
}

function stringList(data, key, { required = false, coerce = false } = {}) {
  const value = data?.[key];
  if (value == null && !required) {
    return [];
  }
  if (coerce && typeof value === "string") {
    return value.trim() ? [value.trim()] : [];
  }
  if (!Array.isArray(value)) {
    throw new Error(`${key} must be a list of strings`);
  }
  if (!coerce && !value.every((item) => typeof item === "string")) {
    throw new Error(`${key} must be a list of strings`);
  }
  return value.map(normalizeStringListItem).filter(Boolean);
}

function normalizeStringListItem(item) {
  if (typeof item === "string") {
    return item.trim();
  }
  if (item == null) {
    return "";
  }
  if (typeof item === "number" || typeof item === "boolean") {
    return String(item);
  }
  try {
    return JSON.stringify(item);
  } catch {
    return String(item);
  }
}

function validateId(value, label) {
  if (!SAFE_ID_RE.test(value)) {
    throw new Error(`unsafe ${label}: ${value}`);
  }
  return value;
}

function validateProjectPath(value, label = "filepath") {
  const normalized = String(value || "").replace(/\\/gu, "/");
  const parsed = path.posix.normalize(normalized);
  if (
    !normalized ||
    path.isAbsolute(normalized) ||
    parsed !== normalized ||
    parsed.split("/").includes("..")
  ) {
    throw new Error(`unsafe ${label}: ${value}`);
  }
  return parsed;
}

function normalizedRoots(roots) {
  const values =
    Array.isArray(roots) && roots.length
      ? roots
      : ["test/generated/benchmarkbr"];
  return values.map(
    (root) => `${validateProjectPath(root).replace(/\/$/u, "")}/`,
  );
}

export function validateTestFile(
  testFile,
  { allowedRoots = ["test/generated/benchmarkbr"] } = {},
) {
  const parsed = validateProjectPath(testFile, "test_file");
  const roots = normalizedRoots(allowedRoots);
  if (!roots.some((root) => parsed.startsWith(root))) {
    throw new Error(
      `test_file must be under one generated test root (${roots.join(", ")}): ${testFile}`,
    );
  }
  if (!parsed.endsWith(".test.ts") && !parsed.endsWith(".test.tsx")) {
    throw new Error(
      `test_file must end with .test.ts or .test.tsx: ${testFile}`,
    );
  }
  return parsed;
}

function stripCodeFence(code) {
  let text = String(code ?? "").trim();
  const fence =
    /^```(?:typescript|ts|javascript|js)?\s*([\s\S]*?)\s*```$/u.exec(text);
  if (fence) {
    text = fence[1].trim();
  }
  return text;
}

function normalizeAppendCode(
  code,
  { projectRoot = "", testFile = "generated.test.ts" } = {},
) {
  const text = stripCodeFence(code);
  if (!text) {
    throw new Error("append_code must be non-empty");
  }
  validateAppendCodeAst(text, {
    projectRoot,
    testFile,
  });
  return `${text.trimEnd()}\n`;
}

function validateAppendCodeAst(code, { projectRoot, testFile }) {
  const ts = loadTypeScript(projectRoot);
  if (!ts) {
    return;
  }
  const sourceFile = parseSource(ts, testFile, code);
  if (sourceFile.parseDiagnostics.length > 0) {
    const message = ts.flattenDiagnosticMessageText(
      sourceFile.parseDiagnostics[0].messageText,
      " ",
    );
    throw new Error(`append_code has TypeScript syntax error: ${message}`);
  }
  const findings = scanAppendCodeAst(ts, sourceFile);
  if (findings.forbiddenImports.length > 0) {
    throw new Error(
      `append_code imports forbidden runtime modules: ${findings.forbiddenImports.join(", ")}`,
    );
  }
  if (findings.forbiddenRuntimeApis.length > 0) {
    throw new Error(
      `append_code uses forbidden runtime APIs: ${[...new Set(findings.forbiddenRuntimeApis)].join(", ")}`,
    );
  }
  if (findings.dynamicRuntimeImports > 0) {
    throw new Error(
      "append_code must not use computed dynamic import or require specifiers",
    );
  }
}

function vitestImportNames(ts, sourceFile) {
  const names = {
    testCallNames: new Set(),
    expectNames: new Set(),
    viNames: new Set(),
  };
  for (const statement of sourceFile.statements) {
    if (
      !ts.isImportDeclaration(statement) ||
      stringLiteralText(ts, statement.moduleSpecifier) !== "vitest"
    ) {
      continue;
    }
    const bindings = statement.importClause?.namedBindings;
    if (!bindings || !ts.isNamedImports(bindings)) {
      continue;
    }
    for (const specifier of bindings.elements) {
      const imported =
        specifier.propertyName?.text || specifier.name?.text || "";
      const local = specifier.name?.text || imported;
      if (imported === "it" || imported === "test") {
        names.testCallNames.add(local);
      } else if (imported === "expect") {
        names.expectNames.add(local);
      } else if (imported === "vi") {
        names.viNames.add(local);
      }
    }
  }
  return names;
}

function scanAppendCodeAst(ts, sourceFile) {
  const findings = {
    forbiddenImports: [],
    forbiddenRuntimeApis: [],
    dynamicRuntimeImports: 0,
  };
  walkAst(ts, sourceFile, (node) => {
    const call = ts.isCallExpression(node);
    if (
      (call || ts.isNewExpression(node)) &&
      ts.isIdentifier(node.expression) &&
      (FORBIDDEN_GLOBAL_CONSTRUCTORS.has(node.expression.text) ||
        (call && FORBIDDEN_GLOBAL_CALLS.has(node.expression.text)))
    ) {
      findings.forbiddenRuntimeApis.push(node.expression.text);
    }
    const propertyAccess = ts.isPropertyAccessExpression(node);
    if (propertyAccess || ts.isElementAccessExpression(node)) {
      const receiver = node.expression;
      const member = propertyAccess
        ? node.name.text
        : stringLiteralText(ts, node.argumentExpression);
      if (
        ts.isIdentifier(receiver) &&
        ((FORBIDDEN_GLOBAL_OBJECTS.has(receiver.text) &&
          (propertyAccess || member)) ||
          (receiver.text === "process" &&
            FORBIDDEN_PROCESS_MEMBERS.has(member)) ||
          (["global", "globalThis"].includes(receiver.text) &&
            ["fetch", "WebSocket", "EventSource"].includes(member)))
      ) {
        findings.forbiddenRuntimeApis.push(
          propertyAccess
            ? `${receiver.text}.${member}`
            : `${receiver.text}[${member}]`,
        );
      }
    }
    const specifier = moduleReference(ts, node);
    if (specifier) {
      if (FORBIDDEN_RUNTIME_IMPORTS.has(specifier.replace(/^node:/u, ""))) {
        findings.forbiddenImports.push(specifier);
      }
    } else if (specifier === "" && call) {
      findings.dynamicRuntimeImports += 1;
    }
  });
  return findings;
}

function isVitestMockStatement(ts, statement, viNames) {
  if (
    !ts.isExpressionStatement(statement) ||
    !ts.isCallExpression(statement.expression)
  ) {
    return false;
  }
  const callee = statement.expression.expression;
  return (
    ts.isPropertyAccessExpression(callee) &&
    ts.isIdentifier(callee.expression) &&
    viNames.has(callee.expression.text) &&
    ["mock", "doMock", "unmock", "doUnmock"].includes(callee.name.text)
  );
}

function assetIntentStructure(asset, projectRoot) {
  const ts = loadTypeScript(projectRoot);
  if (!ts) {
    throw new Error(
      "TypeScript compiler API is required for formal asset intent validation",
    );
  }
  const sourceFile = parseSource(ts, asset.test_file, asset.append_code);
  const printer = ts.createPrinter({ removeComments: true });
  const canonical = (node) =>
    printer.printNode(ts.EmitHint.Unspecified, node, sourceFile).trim();
  const imports = vitestImportNames(ts, sourceFile);
  const testCalls = [];
  const importStatements = [];
  const mockStatements = [];
  const protectedTopLevel = [];
  for (const statement of sourceFile.statements) {
    if (ts.isImportDeclaration(statement)) {
      importStatements.push(canonical(statement));
      continue;
    }
    if (isVitestMockStatement(ts, statement, imports.viNames)) {
      mockStatements.push(canonical(statement));
      continue;
    }
    const call =
      ts.isExpressionStatement(statement) &&
      ts.isCallExpression(statement.expression)
        ? statement.expression
        : null;
    if (
      call &&
      ts.isIdentifier(call.expression) &&
      imports.testCallNames.has(call.expression.text)
    ) {
      testCalls.push(call);
      continue;
    }
    protectedTopLevel.push(canonical(statement));
  }
  if (testCalls.length === 0) {
    throw new Error(
      "generated test must use a block callback so intent can be audited",
    );
  }
  const tests = testCalls.map((call) => {
    const callback = call.arguments[1];
    if (
      !callback ||
      !isFunctionValue(ts, callback) ||
      !ts.isBlock(callback.body)
    ) {
      throw new Error(
        "generated test must use a block callback so intent can be audited",
      );
    }
    // Compare the complete call envelope without its independently audited body.
    const body = ts.factory.createBlock([]);
    const signature = ts.isArrowFunction(callback)
      ? ts.factory.updateArrowFunction(
          callback,
          callback.modifiers,
          callback.typeParameters,
          callback.parameters,
          callback.type,
          callback.equalsGreaterThanToken,
          body,
        )
      : ts.factory.updateFunctionExpression(
          callback,
          callback.modifiers,
          callback.asteriskToken,
          callback.name,
          callback.typeParameters,
          callback.parameters,
          callback.type,
          body,
        );
    const header = canonical(
      ts.factory.updateCallExpression(
        call,
        call.expression,
        call.typeArguments,
        call.arguments.map((argument, index) =>
          index === 1 ? signature : argument,
        ),
      ),
    );
    const bodyStatements = [];
    const expectStatements = [];
    for (const statement of callback.body.statements) {
      const text = canonical(statement);
      bodyStatements.push(text);
      if (containsExpectCall(ts, statement, imports.expectNames)) {
        expectStatements.push(text);
      }
    }
    return { header, bodyStatements, expectStatements };
  });
  return {
    importStatements,
    mockStatements,
    protectedTopLevel,
    tests,
  };
}

function containsExpectCall(ts, node, expectNames) {
  let found = false;
  walkAst(ts, node, (current) => {
    if (
      ts.isCallExpression(current) &&
      ts.isIdentifier(current.expression) &&
      expectNames.has(current.expression.text)
    ) {
      found = true;
    }
    return !found;
  });
  return found;
}

export function validateMinimizedCodeIsSubset(
  original,
  minimized,
  { projectRoot },
) {
  const before = assetIntentStructure(original, projectRoot);
  const after = assetIntentStructure(minimized, projectRoot);
  for (const [key, label] of [
    ["importStatements", "imports"],
    ["mockStatements", "top-level mocks"],
    ["protectedTopLevel", "protected top-level behavior"],
  ]) {
    if (!isOrderedSubset(before[key], after[key])) {
      throw new Error(`minimization added or changed ${label}`);
    }
  }
  if (
    JSON.stringify(before.tests.map((test) => test.header)) !==
    JSON.stringify(after.tests.map((test) => test.header))
  ) {
    throw new Error(
      "minimization added, removed, or changed a test call or callback signature",
    );
  }
  for (const [index, test] of after.tests.entries()) {
    if (!isOrderedSubset(before.tests[index].bodyStatements, test.bodyStatements)) {
      throw new Error("minimization added or changed test-body behavior");
    }
    if (
      JSON.stringify(test.expectStatements) !==
      JSON.stringify(before.tests[index].expectStatements)
    ) {
      throw new Error("minimization changed the primary oracle assertion");
    }
  }
}

function isOrderedSubset(original, candidate) {
  let cursor = 0;
  for (const statement of candidate) {
    while (cursor < original.length && original[cursor] !== statement) {
      cursor += 1;
    }
    if (cursor >= original.length) {
      return false;
    }
    cursor += 1;
  }
  return true;
}

function parseBoundaryPlan(data) {
  const raw = data.boundary_plan || [];
  if (!Array.isArray(raw)) {
    throw new Error("boundary_plan must be a list");
  }
  const seen = new Set();
  return raw.map((item, index) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) {
      throw new Error(`boundary_plan item ${index + 1} must be an object`);
    }
    const boundaryId = validateId(
      stringField(item, "boundary_id", { required: false }) ||
        `boundary-${String(index + 1).padStart(3, "0")}`,
      "boundary_id",
    );
    if (seen.has(boundaryId)) {
      throw new Error(`duplicate boundary_id: ${boundaryId}`);
    }
    seen.add(boundaryId);
    const targetUnitIds = stringList(item, "target_unit_ids", {
      required: true,
    });
    if (
      targetUnitIds.length === 0 ||
      new Set(targetUnitIds).size !== targetUnitIds.length
    ) {
      throw new Error(
        `boundary ${boundaryId} target_unit_ids must be non-empty and unique`,
      );
    }
    const route = objectField(item, "route");
    const probe = objectField(item, "probe");
    const invariant = objectField(item, "invariant");
    const activationConditions = stringList(probe, "activation_conditions", {
      required: true,
      coerce: true,
    });
    if (activationConditions.length === 0) {
      throw new Error(
        `boundary ${boundaryId} activation_conditions must not be empty`,
      );
    }
    const independentOracle = stringField(invariant, "independent_oracle");
    return {
      boundary_id: boundaryId,
      target_unit_ids: targetUnitIds,
      route: {
        entrypoint_id: validateId(
          stringField(route, "entrypoint_id"),
          "entrypoint_id",
        ),
      },
      probe: {
        test_intent: stringField(probe, "test_intent"),
        activation_conditions: activationConditions,
      },
      invariant: {
        independent_oracle: independentOracle,
        supporting_evidence: stringField(invariant, "supporting_evidence"),
        expected_observation: stringField(invariant, "expected_observation"),
        oracle_mode: enumField(invariant, "oracle_mode", ORACLE_MODES),
      },
      oracle_family:
        stringField(item, "oracle_family", { required: false }) ||
        independentOracle,
      novelty_from_prior:
        stringField(item, "novelty_from_prior", { required: false }) ||
        "not_provided",
      bug_hypothesis: stringField(item, "bug_hypothesis"),
    };
  });
}

/** Bound both request phases, retaining planning's early path validation. */
export function parseRequestList(value, maxRequests, planning = false) {
  const raw = value == null ? [] : value;
  if (!Array.isArray(raw)) {
    throw new Error(
      planning
        ? "context_requests must be a list"
        : "context request payload must contain a requests list",
    );
  }
  const prefix = planning ? "context " : "";
  const errors = [];
  const recordError = (index, message, details = {}) => {
    errors.push({ index, ...details, message });
  };
  const limited = raw.slice(0, maxRequests);
  if (raw.length > maxRequests) {
    recordError(
      maxRequests + 1,
      `ignored ${raw.length - maxRequests} ${prefix}requests beyond maximum ${maxRequests}`,
    );
  }
  const requests = [];
  limited.forEach((item, index) => {
    if (
      planning &&
      (!item || typeof item !== "object" || Array.isArray(item))
    ) {
      recordError(index + 1, "context request must be a JSON object");
      return;
    }
    const kind = String(item?.kind || "").trim();
    let filepath = String(item?.filepath || "").trim();
    const qualname = String(item?.qualname || "").trim();
    if (!SUPPORTED_CONTEXT_REQUEST_KINDS.has(kind)) {
      recordError(index + 1, `unsupported ${prefix}request kind`, { kind });
      return;
    }
    if (planning) {
      try {
        filepath = validateProjectPath(filepath);
      } catch {
        recordError(index + 1, "unsafe filepath", { kind, filepath });
        return;
      }
    } else if (!filepath) {
      recordError(index + 1, "missing filepath", { kind });
      return;
    }
    if (kind !== "module_context" && !qualname) {
      recordError(index + 1, "missing qualname", { kind, filepath });
      return;
    }
    requests.push({
      kind,
      filepath,
      qualname,
      reason: String(item.reason || "").trim(),
    });
  });
  return { requests, errors };
}

export function parseProbePlan(content, { maxContextRequests = 1 } = {}) {
  const data = extractJson(content);
  const { requests, errors } = parseRequestList(
    data.context_requests,
    Math.max(0, maxContextRequests),
    true,
  );
  const boundaryPlan = parseBoundaryPlan(data);
  const exhaustedReason = stringField(data, "exhausted_reason", {
    required: false,
  });
  if (boundaryPlan.length === 0 && !exhaustedReason) {
    throw new Error("an empty boundary_plan requires exhausted_reason");
  }
  if (boundaryPlan.length === 0 && (data.context_requests || []).length > 0) {
    throw new Error("an exhausted plan cannot request context");
  }
  return {
    plan: {
      boundary_plan: boundaryPlan,
      context_requests: requests,
      exhausted_reason: boundaryPlan.length === 0 ? exhaustedReason : "",
    },
    errors,
  };
}

function parseAsset(
  data,
  index,
  { allowedTestRoots, projectRoot, canonicalPlan, publicEntrypoints },
) {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error(`asset ${index} must be an object`);
  }
  const assetId = validateId(
    stringField(data, "asset_id", { required: false }) ||
      `asset-${String(index).padStart(3, "0")}`,
    "asset_id",
  );
  const boundaryId = stringField(data, "boundary_id");
  const boundary = (canonicalPlan?.boundary_plan || []).find(
    (item) => item.boundary_id === boundaryId,
  );
  if (!boundary) {
    throw new Error(
      `asset ${assetId} references unknown boundary_id: ${boundaryId}`,
    );
  }
  const entrypoint = (publicEntrypoints || []).find(
    (item) => item.entrypoint_id === boundary.route.entrypoint_id,
  );
  if (!entrypoint) {
    throw new Error(
      `asset ${assetId} references unavailable public entrypoint: ${boundary.route.entrypoint_id}`,
    );
  }
  const testFile = stringField(data, "test_file");
  const oracleMode = boundary.invariant.oracle_mode;
  const appendCode = normalizeAppendCode(stringField(data, "append_code"), {
    projectRoot,
    testFile,
  });
  return {
    asset_id: assetId,
    boundary_id: boundaryId,
    target_unit_ids: [...boundary.target_unit_ids],
    public_entrypoint_id: boundary.route.entrypoint_id,
    test_intent: boundary.probe.test_intent,
    activation_conditions: [...boundary.probe.activation_conditions],
    independent_oracle: boundary.invariant.independent_oracle,
    supporting_evidence: boundary.invariant.supporting_evidence,
    expected_observation: boundary.invariant.expected_observation,
    oracle_family: boundary.oracle_family,
    novelty_from_prior: boundary.novelty_from_prior,
    bug_hypothesis: boundary.bug_hypothesis,
    input_construction: stringField(data, "input_construction"),
    observable_oracle: stringField(data, "observable_oracle"),
    primary_oracle: stringField(data, "primary_oracle"),
    oracle_mode: oracleMode,
    test_file: validateTestFile(testFile, { allowedRoots: allowedTestRoots }),
    append_code: appendCode,
    test_asset_sha256: crypto
      .createHash("sha256")
      .update(`${testFile}\0${appendCode}`)
      .digest("hex"),
    mocking_plan:
      stringField(data, "mocking_plan", { required: false }) ||
      stringField(data, "mocking_strategy", { required: false }),
  };
}

export function parseProposalPartial(
  content,
  {
    maxAssets = 5,
    allowedTestRoots = ["test/generated/benchmarkbr"],
    projectRoot = "",
    canonicalPlan = null,
    publicEntrypoints = [],
    allowEmptyAssets = false,
  } = {},
) {
  const data = extractJson(content);
  let rawAssets = data.assets;
  if (rawAssets == null) {
    rawAssets = [{ ...data, asset_id: data.asset_id || "asset-001" }];
  }
  if (
    !Array.isArray(rawAssets) ||
    (!allowEmptyAssets && rawAssets.length === 0)
  ) {
    throw new Error("proposal assets must be a non-empty list");
  }
  const errors = [];
  const recordError = (index, asset_id, message) => {
    errors.push({ index, asset_id, message });
  };
  if (rawAssets.length > maxAssets) {
    recordError(
      maxAssets + 1,
      "",
      `ignored ${rawAssets.length - maxAssets} assets beyond maximum ${maxAssets}`,
    );
    rawAssets = rawAssets.slice(0, maxAssets);
  }

  const assets = [];
  const seen = new Set();
  rawAssets.forEach((rawAsset, index) => {
    const rawAssetId = rawAsset?.asset_id || "";
    try {
      const asset = parseAsset(rawAsset, index + 1, {
        allowedTestRoots,
        projectRoot,
        canonicalPlan,
        publicEntrypoints,
      });
      if (seen.has(asset.asset_id)) {
        recordError(
          index + 1,
          asset.asset_id,
          `duplicate asset_id ignored: ${asset.asset_id}`,
        );
        return;
      }
      seen.add(asset.asset_id);
      assets.push(asset);
    } catch (error) {
      recordError(index + 1, String(rawAssetId), error.message);
    }
  });
  if (assets.length === 0 && !allowEmptyAssets) {
    throw new Error(
      `proposal has no valid assets: ${errors.map((error) => error.message).join("; ")}`,
    );
  }
  return {
    proposal: {
      assets,
      boundary_plan: canonicalPlan?.boundary_plan || [],
    },
    errors,
  };
}
