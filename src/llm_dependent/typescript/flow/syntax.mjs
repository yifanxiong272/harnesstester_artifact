import fs from "node:fs";
import path from "node:path";

import { nodeSpan, propertyChain, unwrapExpression } from "./source_locator.mjs";

/** Read one project-relative source file into the AST shape used by indexing.
 *
 * Called by: `indexing.mjs` while building the project-wide function/class
 * index. The caller owns the file universe; this helper only parses one file.
 */
export function readSourceFile(ts, root, rel) {
  const filePath = path.join(root, rel);
  const text = fs.readFileSync(filePath, "utf8");
  return {
    rel,
    path: filePath,
    text,
    lines: text.split(/\r?\n/),
    sourceFile: ts.createSourceFile(filePath, text, ts.ScriptTarget.Latest, true),
  };
}

/** Return source text for a node with the project source file context.
 *
 * Called by: indexing helpers when constructing stable names, annotations, and
 * heritage expressions.
 */
export function textOf(sourceFile, node) {
  return node.getText(sourceFile);
}

/** Return the line/column span format used in all output payloads.
 *
 * Called by: indexing and flow analysis when turning AST nodes into regions.
 */
export function spanOf(sourceFile, node) {
  const span = nodeSpan(sourceFile, node);
  return {
    start: span.start_line,
    end: span.end_line,
    start_column: span.start_column,
    end_column: span.end_column,
  };
}

/** Test whether an AST node is a function-like unit with executable body.
 *
 * Called by: indexing, assignment collection, and inline callback analysis to
 * keep nested executable scopes separated.
 */
export function isFunctionLikeWithBody(ts, node) {
  return (
    (ts.isFunctionDeclaration(node) ||
      ts.isFunctionExpression(node) ||
      ts.isArrowFunction(node) ||
      ts.isMethodDeclaration(node) ||
      ts.isGetAccessorDeclaration(node) ||
      ts.isSetAccessorDeclaration(node) ||
      ts.isConstructorDeclaration(node)) &&
    Boolean(node.body)
  );
}

/** Return identifier parameters for a function-like node.
 *
 * Called by: function indexing and callback activation. Destructured
 * parameters are handled by `targetRefs` at flow time when they are explicitly
 * assigned or seeded; this list keeps only named locals that can be addressed
 * as ordinary `localRef`s.
 */
export function functionParams(ts, node, sourceFile) {
  return Array.from(node.parameters || [])
    .map((param) => {
      if (!ts.isIdentifier(param.name)) return null;
      return {
        name: param.name.text,
        annotation: param.type ? textOf(sourceFile, param.type) : "",
        initializer: param.initializer || null,
      };
    })
    .filter(Boolean);
}

/** Convert a static expression into a dotted local path.
 *
 * Called by: resolver, provider matching, assignment indexing, and flow
 * transfer. Literal element access is normalized to property form
 * (`obj["x"] -> obj.x`); dynamic element access falls back to the container
 * path (`obj[key] -> obj`) for conservative may-analysis.
 */
export function exprPath(ts, node) {
  if (!node) return "";
  const unwrapped = unwrapExpression(ts, node);
  if (unwrapped !== node) return exprPath(ts, unwrapped);
  if (ts.isIdentifier(node) || ts.isPrivateIdentifier?.(node)) return node.text;
  if (ts.isThis(node)) return "this";
  if (node.kind === ts.SyntaxKind.SuperKeyword) return "super";
  if (ts.isPropertyAccessExpression(node)) {
    const base = exprPath(ts, node.expression);
    return base ? `${base}.${node.name.text}` : node.name.text;
  }
  if (ts.isElementAccessExpression(node)) {
    const base = exprPath(ts, node.expression);
    if (!base) return "";
    const arg = unwrapExpression(ts, node.argumentExpression);
    if (arg && ts.isStringLiteralLike(arg)) return `${base}.${arg.text}`;
    if (arg && ts.isNumericLiteral(arg)) return `${base}.${arg.text}`;
    return base;
  }
  if (ts.isCallExpression(node)) return propertyChain(ts, node.expression).join(".");
  return "";
}
