import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

export function loadTypeScript(projectRoot = "") {
  const candidates = [
    projectRoot ? path.join(projectRoot, "package.json") : "",
    path.join(process.cwd(), "package.json"),
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (!fs.existsSync(candidate)) {
      continue;
    }
    try {
      return createRequire(candidate)("typescript");
    } catch {
      // Try the next installed compiler.
    }
  }
  return null;
}

export function scriptKindForPath(filepath, ts) {
  const ext = path.extname(filepath).toLowerCase();
  const kind = { ".tsx": "TSX", ".jsx": "JSX", ".js": "JS" }[ext] || "TS";
  return ts.ScriptKind[kind];
}

export function parseSource(ts, filepath, text) {
  return ts.createSourceFile(
    filepath,
    text,
    ts.ScriptTarget.Latest,
    true,
    scriptKindForPath(filepath, ts),
  );
}

/** Visit nodes in compiler order; returning false skips that node's children. */
export function walkAst(ts, root, visitor) {
  const visit = (node) => {
    if (visitor(node) !== false) ts.forEachChild(node, visit);
  };
  visit(root);
}

export function splitSourceLines(text) {
  const lines = text.split(/\r?\n/u);
  if (lines.at(-1) === "") {
    lines.pop();
  }
  return lines;
}

export function isFunctionValue(ts, node) {
  return ts.isArrowFunction(node) || ts.isFunctionExpression(node);
}

export function nodeRange(sourceFile, node) {
  return {
    start_line:
      sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile)).line +
      1,
    end_line: sourceFile.getLineAndCharacterOfPosition(node.getEnd()).line + 1,
  };
}

export function memberName(node) {
  return node?.name?.getText?.().replace(/^["']|["']$/gu, "") || "";
}

export function hasModifier(ts, node, kind) {
  const modifiers =
    typeof ts.canHaveModifiers === "function" && ts.canHaveModifiers(node)
      ? ts.getModifiers(node)
      : node.modifiers;
  return (modifiers || []).some((modifier) => modifier.kind === kind);
}

export function compactStatement(node, sourceFile, limit = 220) {
  return node.getText(sourceFile).replace(/\s+/gu, " ").slice(0, limit);
}

export function stringLiteralText(ts, node) {
  return node &&
    (ts.isStringLiteral(node) ||
      node.kind === ts.SyntaxKind.NoSubstitutionTemplateLiteral)
    ? node.text
    : "";
}

/** Return a module reference, empty for a computed specifier, or null otherwise. */
export function moduleReference(ts, node) {
  if (
    (ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) &&
    node.moduleSpecifier
  ) {
    return stringLiteralText(ts, node.moduleSpecifier);
  }
  if (
    ts.isCallExpression(node) &&
    (node.expression.kind === ts.SyntaxKind.ImportKeyword ||
      (ts.isIdentifier(node.expression) && node.expression.text === "require"))
  ) {
    return stringLiteralText(ts, node.arguments?.[0]);
  }
  return null;
}

export const SOURCE_EXTENSIONS = [".tsx", ".ts", ".jsx", ".js"];

export function stripSourceExtension(filepath) {
  const extension = SOURCE_EXTENSIONS.find((item) => filepath.endsWith(item));
  return extension ? filepath.slice(0, -extension.length) : filepath;
}
