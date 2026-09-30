import crypto from "node:crypto";
import path from "node:path";

import { parseTypeScript } from "./typescript_ast.mjs";

export const TOP_LEVEL_SUITE_ID = "top-level";

const TEST_REGISTRATION_NAMES = new Set(["it", "test"]);
const HARNESS_REGISTRATION_NAMES = new Set([
  "afterAll",
  "afterEach",
  "beforeAll",
  "beforeEach",
  "describe",
  "expect",
  "vi",
]);
const UNSUITABLE_SUITE_MODIFIERS = new Set([
  "each",
  "for",
  "runIf",
  "skip",
  "skipIf",
  "todo",
]);

const MODULE_EXTENSIONS = new Set([
  ".cjs",
  ".cts",
  ".js",
  ".jsx",
  ".mjs",
  ".mts",
  ".ts",
  ".tsx",
]);

function normalizedPath(value) {
  return String(value ?? "").replace(/\\/gu, "/");
}

function moduleIdentity(filepath) {
  const normalized = path.posix.normalize(normalizedPath(filepath));
  const extension = path.posix.extname(normalized);
  return MODULE_EXTENSIONS.has(extension)
    ? normalized.slice(0, -extension.length)
    : normalized;
}

/** Compare equivalent relative module specifiers across TS/JS extensions. */
export function sameModuleSpecifier(left, right) {
  if (
    !String(left ?? "").startsWith(".") ||
    !String(right ?? "").startsWith(".")
  ) {
    return left === right;
  }
  return moduleIdentity(left) === moduleIdentity(right);
}

function importedModuleIdentity(seedFile, specifier) {
  if (!String(specifier ?? "").startsWith(".")) return null;
  return moduleIdentity(
    path.posix.join(path.posix.dirname(normalizedPath(seedFile)), specifier),
  );
}

function dynamicImportSpecifier(typescript, expression) {
  if (!expression) return null;
  let current = expression;
  while (
    typescript.isAwaitExpression(current) ||
    typescript.isParenthesizedExpression(current)
  ) {
    current = current.expression;
  }
  if (
    !typescript.isCallExpression(current) ||
    current.expression.kind !== typescript.SyntaxKind.ImportKeyword ||
    !typescript.isStringLiteralLike(current.arguments[0])
  ) {
    return null;
  }
  return current.arguments[0].text;
}

function dynamicImportBindings(typescript, name) {
  if (typescript.isIdentifier(name)) {
    return [{ kind: "namespace", imported: "*", local: name.text }];
  }
  if (!typescript.isObjectBindingPattern(name)) return [];
  return name.elements.flatMap((element) => {
    if (element.dotDotDotToken || !typescript.isIdentifier(element.name)) {
      return [];
    }
    const imported = element.propertyName;
    if (
      imported &&
      !typescript.isIdentifier(imported) &&
      !typescript.isStringLiteralLike(imported)
    ) {
      return [];
    }
    return [
      {
        kind: "named",
        imported: imported?.text ?? element.name.text,
        local: element.name.text,
      },
    ];
  });
}

/** Return runtime bindings imported directly from the selected source file. */
export function targetBindingsForSeed(
  typescript,
  seedFile,
  targetFile,
  source,
) {
  const target = moduleIdentity(targetFile);
  const sourceFile = parseTypeScript(typescript, seedFile, source);
  const bindings = [];
  for (const statement of sourceFile.statements) {
    if (typescript.isVariableStatement(statement)) {
      for (const declaration of statement.declarationList.declarations) {
        const specifier = dynamicImportSpecifier(
          typescript,
          declaration.initializer,
        );
        if (importedModuleIdentity(seedFile, specifier) === target) {
          bindings.push(...dynamicImportBindings(typescript, declaration.name));
        }
      }
      continue;
    }
    if (!typescript.isImportDeclaration(statement)) continue;
    if (
      importedModuleIdentity(seedFile, statement.moduleSpecifier.text) !==
      target
    ) {
      continue;
    }
    const clause = statement.importClause;
    if (!clause || clause.isTypeOnly) continue;
    if (clause.name) {
      bindings.push({
        kind: "default",
        imported: "default",
        local: clause.name.text,
      });
    }
    const named = clause.namedBindings;
    if (named && typescript.isNamespaceImport(named)) {
      bindings.push({
        kind: "namespace",
        imported: "*",
        local: named.name.text,
      });
    } else if (named && typescript.isNamedImports(named)) {
      for (const element of named.elements) {
        if (element.isTypeOnly) continue;
        bindings.push({
          kind: "named",
          imported: element.propertyName?.text ?? element.name.text,
          local: element.name.text,
        });
      }
    }
  }
  return bindings;
}

/** Return the most specific configured test package containing a file. */
export function packageForFile(packages, filepath) {
  const relative = normalizedPath(filepath);
  return (
    packages
      .filter(
        (item) =>
          item.cwd === "." ||
          relative === item.cwd ||
          relative.startsWith(`${item.cwd}/`),
      )
      .sort(
        (left, right) =>
          right.cwd.length - left.cwd.length ||
          left.cwd.localeCompare(right.cwd),
      )[0] ?? null
  );
}

function rankedCandidates(candidates) {
  return candidates
    .map((candidate) => ({
      test_file: normalizedPath(candidate.test_file),
      score: Number(candidate.score ?? 0),
    }))
    .filter(
      (candidate) =>
        candidate.test_file &&
        Number.isFinite(candidate.score) &&
        candidate.score > 0,
    )
    .sort(
      (left, right) =>
        right.score - left.score ||
        left.test_file.localeCompare(right.test_file),
    );
}

/** Select the same-package reverse-coverage seed used by Qodo. */
export function selectExistingTest(packages, sourceFile, candidates) {
  const sourcePackage = packageForFile(packages, sourceFile);
  if (!sourcePackage) return null;
  if (candidates !== undefined && !Array.isArray(candidates)) {
    throw new Error(`test candidates must be an array: ${sourceFile}`);
  }
  return (
    rankedCandidates(candidates ?? []).find((candidate) => {
      const testPackage = packageForFile(packages, candidate.test_file);
      return testPackage?.cwd === sourcePackage.cwd;
    }) ?? null
  );
}

export function generatedTestSuffix(testFile) {
  for (const suffix of [".spec.tsx", ".test.tsx", ".spec.ts", ".test.ts"]) {
    if (testFile.endsWith(suffix)) return suffix;
  }
  return testFile.endsWith(".tsx") ? ".tsx" : ".ts";
}

/** Build a unique sibling path so seed-relative imports remain valid. */
export function siblingGeneratedTest(seedTestFile, filename) {
  return path.posix.join(
    path.posix.dirname(normalizedPath(seedTestFile)),
    `${filename}${generatedTestSuffix(seedTestFile)}`,
  );
}

/** Return a stable collision-resistant namespace for injected Vitest APIs. */
export function vitestNamespace(seedTest) {
  const identity = `${normalizedPath(seedTest?.test_file)}\0${String(seedTest?.sha256 ?? "")}`;
  const digest = crypto.createHash("sha1").update(identity).digest("hex");
  return `__testAugmentVitest_${digest.slice(0, 12)}`;
}

/** Return the stable helper name used to import an unmocked target module. */
export function targetLoader(seedTest, targetImport) {
  const identity = `${normalizedPath(seedTest?.test_file)}\0${String(seedTest?.sha256 ?? "")}\0${normalizedPath(targetImport)}`;
  const digest = crypto.createHash("sha1").update(identity).digest("hex");
  return `__testAugmentLoadTarget_${digest.slice(0, 12)}`;
}

/** Return the stable namespace used for direct access to target exports. */
export function targetBinding(seedTest, targetImport) {
  const identity = `${normalizedPath(seedTest?.test_file)}\0${String(seedTest?.sha256 ?? "")}\0${normalizedPath(targetImport)}`;
  const digest = crypto.createHash("sha1").update(identity).digest("hex");
  return `__testAugmentTarget_${digest.slice(0, 12)}`;
}

function vitestBindings(typescript, sourceFile, importedNames) {
  const direct = new Set(importedNames);
  const namespaces = new Set();
  for (const statement of sourceFile.statements) {
    if (
      !typescript.isImportDeclaration(statement) ||
      statement.moduleSpecifier.text !== "vitest"
    ) {
      continue;
    }
    const bindings = statement.importClause?.namedBindings;
    if (bindings && typescript.isNamespaceImport(bindings)) {
      namespaces.add(bindings.name.text);
    } else if (bindings && typescript.isNamedImports(bindings)) {
      for (const element of bindings.elements) {
        if (
          importedNames.has(element.propertyName?.text ?? element.name.text)
        ) {
          direct.add(element.name.text);
        }
      }
    }
  }
  return { direct, namespaces };
}

function rootIdentifier(typescript, expression) {
  let current = expression;
  while (typescript.isCallExpression(current)) {
    current = current.expression;
  }
  while (
    typescript.isPropertyAccessExpression(current) ||
    typescript.isElementAccessExpression(current)
  ) {
    current = current.expression;
  }
  return typescript.isIdentifier(current) ? current.text : null;
}

function isVitestRegistration(
  typescript,
  expression,
  bindings,
  registrationNames,
) {
  if (bindings.direct.has(rootIdentifier(typescript, expression))) {
    return true;
  }

  let current = expression;
  while (typescript.isCallExpression(current)) {
    current = current.expression;
  }
  while (typescript.isPropertyAccessExpression(current)) {
    if (
      registrationNames.has(current.name.text) &&
      typescript.isIdentifier(current.expression) &&
      bindings.namespaces.has(current.expression.text)
    ) {
      return true;
    }
    current = current.expression;
  }
  return false;
}

function hasRegistrationModifier(typescript, expression, modifiers) {
  let current = expression;
  while (typescript.isCallExpression(current)) {
    current = current.expression;
  }
  while (typescript.isPropertyAccessExpression(current)) {
    if (modifiers.has(current.name.text)) return true;
    current = current.expression;
  }
  return false;
}

function statementRange(source, sourceFile, statement) {
  let start = statement.getStart(sourceFile);
  let end = statement.end;
  const lineStart = source.lastIndexOf("\n", start - 1) + 1;
  if (!source.slice(lineStart, start).trim()) {
    start = lineStart;
  }
  const nextLine = source.indexOf("\n", end);
  if (nextLine >= 0 && !source.slice(end, nextLine).trim()) {
    end = nextLine + 1;
  }
  return { start, end };
}

/** Remove matching call statements without revisiting their nested contents. */
function removeCallStatements(typescript, sourceFile, source, shouldRemove) {
  const ranges = [];
  function visit(node) {
    if (
      typescript.isExpressionStatement(node) &&
      typescript.isCallExpression(node.expression) &&
      shouldRemove(node)
    ) {
      ranges.push(statementRange(source, sourceFile, node));
      return;
    }
    typescript.forEachChild(node, visit);
  }
  visit(sourceFile);
  for (const range of ranges.sort((left, right) => right.start - left.start)) {
    source = `${source.slice(0, range.start)}${source.slice(range.end)}`;
  }
  return { source, removed_count: ranges.length };
}

/** Remove seed cases and suite-level calls that may register cases indirectly. */
export function withoutSeedTestRegistrations(typescript, filepath, source) {
  const sourceFile = parseTypeScript(typescript, filepath, source);
  const testBindings = vitestBindings(
    typescript,
    sourceFile,
    TEST_REGISTRATION_NAMES,
  );
  const harnessBindings = vitestBindings(
    typescript,
    sourceFile,
    HARNESS_REGISTRATION_NAMES,
  );
  const suiteBindings = vitestBindings(
    typescript,
    sourceFile,
    new Set(["describe"]),
  );
  const suiteStatements = new Set();
  let removedSuiteCallCount = 0;

  function indexSuites(node) {
    if (
      typescript.isCallExpression(node) &&
      isVitestRegistration(
        typescript,
        node.expression,
        suiteBindings,
        new Set(["describe"]),
      )
    ) {
      const callback = suiteCallback(typescript, node);
      for (const statement of callback?.body.statements ?? []) {
        suiteStatements.add(statement);
      }
    }
    typescript.forEachChild(node, indexSuites);
  }
  indexSuites(sourceFile);

  const result = removeCallStatements(typescript, sourceFile, source, (node) => {
    if (
      isVitestRegistration(
        typescript,
        node.expression,
        testBindings,
        TEST_REGISTRATION_NAMES,
      )
    ) {
      return true;
    }
    if (
      suiteStatements.has(node) &&
      !isVitestRegistration(
        typescript,
        node.expression,
        harnessBindings,
        HARNESS_REGISTRATION_NAMES,
      )
    ) {
      removedSuiteCallCount += 1;
      return true;
    }
    return false;
  });
  return {
    source: result.source,
    removed_count: result.removed_count - removedSuiteCallCount,
    removed_suite_call_count: removedSuiteCallCount,
  };
}

/** Remove suites left empty after seed cases are stripped. */
export function withoutEmptyTestSuites(typescript, filepath, source) {
  const sourceFile = parseTypeScript(typescript, filepath, source);
  const testBindings = vitestBindings(
    typescript,
    sourceFile,
    TEST_REGISTRATION_NAMES,
  );
  const describeNames = new Set(["describe"]);
  const suiteBindings = vitestBindings(
    typescript,
    sourceFile,
    describeNames,
  );
  function containsTest(node) {
    return (
      (typescript.isCallExpression(node) &&
        isVitestRegistration(
          typescript,
          node.expression,
          testBindings,
          TEST_REGISTRATION_NAMES,
        )) ||
      Boolean(typescript.forEachChild(node, containsTest))
    );
  }

  return removeCallStatements(typescript, sourceFile, source, (node) => {
    if (
      isVitestRegistration(
        typescript,
        node.expression.expression,
        suiteBindings,
        describeNames,
      )
    ) {
      const callback = suiteCallback(typescript, node.expression);
      return callback && !containsTest(callback.body);
    }
    return false;
  }).source;
}

function suiteCallback(typescript, call) {
  return [...call.arguments]
    .reverse()
    .find(
      (argument) =>
        (typescript.isArrowFunction(argument) ||
          typescript.isFunctionExpression(argument)) &&
        typescript.isBlock(argument.body),
    );
}

function suiteTitle(typescript, call) {
  const title = call.arguments.find((argument) =>
    typescript.isStringLiteralLike(argument),
  );
  return title?.text ?? "";
}

/** Index parser-confirmed Vitest suites in deterministic source order. */
export function testSuites(typescript, filepath, source) {
  const sourceFile = parseTypeScript(typescript, filepath, source);
  const describeNames = new Set(["describe"]);
  const bindings = vitestBindings(typescript, sourceFile, describeNames);
  const suites = [];

  function visit(node, disabledByParent = false) {
    if (
      typescript.isCallExpression(node) &&
      isVitestRegistration(typescript, node.expression, bindings, describeNames)
    ) {
      const callback = suiteCallback(typescript, node);
      const disabled =
        disabledByParent ||
        hasRegistrationModifier(
          typescript,
          node.expression,
          UNSUITABLE_SUITE_MODIFIERS,
        );
      if (callback && !disabled) {
        const start = sourceFile.getLineAndCharacterOfPosition(
          node.getStart(sourceFile),
        ).line;
        const end = sourceFile.getLineAndCharacterOfPosition(node.end).line;
        suites.push({
          suite_id: `suite-${String(suites.length + 1).padStart(3, "0")}`,
          title: suiteTitle(typescript, node),
          start_line: start + 1,
          end_line: end + 1,
          insertion_offset: callback.body.getEnd() - 1,
        });
      }
      typescript.forEachChild(node, (child) => visit(child, disabled));
      return;
    }
    typescript.forEachChild(node, (child) => visit(child, disabledByParent));
  }
  visit(sourceFile);
  return suites;
}
