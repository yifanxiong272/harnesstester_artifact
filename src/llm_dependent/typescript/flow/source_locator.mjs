import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

/** Load the explicit source-file universe for one project run. */
export function loadFileList(args) {
  const root = path.resolve(args.root);
  if (!fs.existsSync(root) || !fs.statSync(root).isDirectory()) {
    throw new Error(`subject root is not a directory: ${root}`);
  }
  if (!args.sourceBase) {
    throw new Error("sourceBase is required for TypeScript LLM-dependent analysis");
  }
  const payload = JSON.parse(fs.readFileSync(args.sourceBase, "utf8"));
  const rawFiles = sourceFilesFromPayload(payload);
  for (const rel of rawFiles) {
    if (typeof rel !== "string" || !rel.trim()) {
      throw new Error("sourceBase entries must contain non-empty relative file paths");
    }
    const normalized = path.normalize(rel);
    if (path.isAbsolute(rel) || normalized === ".." || normalized.startsWith(`..${path.sep}`)) {
      throw new Error(`sourceBase path escapes the subject root: ${rel}`);
    }
  }
  const files = rawFiles.map((rel) => path.posix.normalize(rel)).filter(isTypeScriptLike);
  if (new Set(files).size !== files.length) {
    throw new Error("sourceBase contains duplicate source paths after normalization");
  }
  const missing = files.filter((rel) => !fs.existsSync(path.join(root, rel)));
  if (missing.length > 0) {
    const preview = missing.slice(0, 5).join(", ");
    const suffix = missing.length > 5 ? `, ... (${missing.length} missing)` : "";
    throw new Error(`sourceBase files are missing from the subject root: ${preview}${suffix}`);
  }
  if (files.length === 0) {
    throw new Error("sourceBase contains no analyzable TypeScript/JavaScript product files");
  }
  return {
    scanPolicy: "base_source_files",
    files,
  };
}

/** Load the TypeScript compiler API from an explicitly selected package root. */
export function loadTypeScript(root) {
  const packageRoot = path.resolve(root);
  const packageJson = path.join(packageRoot, "package.json");
  if (!fs.existsSync(packageJson)) {
    throw new Error(`TypeScript package root has no package.json: ${packageRoot}`);
  }
  try {
    const ts = createRequire(packageJson)("typescript");
    if (!ts || typeof ts.version !== "string") {
      throw new Error("resolved module does not expose a TypeScript version");
    }
    return ts;
  } catch (error) {
    throw new Error(
      `unable to load TypeScript from ${packageRoot}; install that checkout's dependencies or pass --typescript-root`,
      { cause: error },
    );
  }
}

/** Read either supported source-universe JSON shape. */
function sourceFilesFromPayload(payload) {
  if (!payload || typeof payload !== "object") {
    throw new Error("sourceBase must contain a JSON object");
  }
  if (Array.isArray(payload.files)) {
    return payload.files;
  }
  if (Array.isArray(payload.locations)) {
    return payload.locations.map((item) => item?.file);
  }
  throw new Error("sourceBase must contain a locations array or files array");
}

/** Return one-indexed line/column information for a source position. */
export function lineAndColumn(sourceFile, pos) {
  const lc = sourceFile.getLineAndCharacterOfPosition(pos);
  return { line: lc.line + 1, column: lc.character + 1 };
}

/** Return a one-indexed line span for an AST node. */
export function nodeSpan(sourceFile, node) {
  const start = lineAndColumn(sourceFile, node.getStart(sourceFile));
  const end = lineAndColumn(sourceFile, node.getEnd());
  return {
    start_line: start.line,
    start_column: start.column,
    end_line: end.line,
    end_column: end.column,
  };
}

/** Convert a static property/call expression into a dotted identity chain. */
export function propertyChain(ts, expr) {
  const node = unwrapExpression(ts, expr);
  if (!node) return [];
  if (ts.isIdentifier(node) || ts.isPrivateIdentifier?.(node)) return [node.text];
  if (ts.isThis(node)) return ["this"];
  if (node.kind === ts.SyntaxKind.SuperKeyword) return ["super"];
  if (ts.isPropertyAccessExpression(node)) {
    return [...propertyChain(ts, node.expression), node.name.text];
  }
  if (ts.isElementAccessExpression(node)) {
    const arg = node.argumentExpression;
    if (arg && ts.isStringLiteralLike(arg)) return [...propertyChain(ts, node.expression), arg.text];
    if (arg && ts.isNumericLiteral(arg)) return [...propertyChain(ts, node.expression), arg.text];
  }
  if (ts.isCallExpression(node)) return propertyChain(ts, node.expression);
  return [];
}

/** Remove TS expression wrappers that do not change runtime value identity. */
export function unwrapExpression(ts, expr) {
  let current = expr;
  while (
    current &&
    (ts.isAsExpression(current) ||
      ts.isTypeAssertionExpression(current) ||
      ts.isParenthesizedExpression(current) ||
      ts.isSatisfiesExpression?.(current) ||
      ts.isNonNullExpression?.(current))
  ) {
    current = current.expression;
  }
  return current;
}

function isTypeScriptLike(rel) {
  return /\.(?:ts|tsx|mts|cts|js|jsx|mjs|cjs)$/.test(rel);
}
