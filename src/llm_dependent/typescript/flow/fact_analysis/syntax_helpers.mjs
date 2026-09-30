import { isFunctionLikeWithBody } from "../syntax.mjs";

/** Identify nested units analyzed through their own FunctionInfo records. */
export function isNestedUnit(ts, node) {
  return isFunctionLikeWithBody(ts, node) || ts.isClassDeclaration(node) || ts.isClassExpression(node);
}

/** Identify direct reads already represented by refs, requiring no child walk. */
export function isSimpleReadExpression(ts, node) {
  return (
    ts.isIdentifier(node) ||
    ts.isThis(node) ||
    ts.isSuperKeyword?.(node) ||
    ts.isPropertyAccessExpression(node) ||
    ts.isElementAccessExpression(node)
  );
}

/** Collect expression children within the current function/class scope. */
export function expressionChildren(ts, node) {
  const out = [];
  function visit(child) {
    if (isNestedUnit(ts, child)) return;
    if (ts.isExpressionNode?.(child) || isExpressionLike(ts, child)) out.push(child);
    else ts.forEachChild(child, visit);
  }
  ts.forEachChild(node, visit);
  return out;
}

/** Unwrap common TS expression wrappers before syntax classification. */
export function unwrapTsExpression(ts, expr) {
  let node = expr;
  while (
    node &&
    (ts.isParenthesizedExpression(node) ||
      ts.isAsExpression(node) ||
      ts.isTypeAssertionExpression(node) ||
      ts.isSatisfiesExpression?.(node) ||
      ts.isNonNullExpression?.(node))
  ) {
    node = node.expression;
  }
  return node;
}

/** Bound an emitted region before any nested function/class or control body.
 * Those bodies contribute their own statement regions.
 */
export function analysisSpanOf(ts, sourceFile, node) {
  const start = node.getStart(sourceFile);
  let end = node.getEnd();
  const cutStart = firstSpanCutStart(ts, sourceFile, node);
  if (cutStart !== null && cutStart > start) end = cutStart - 1;
  const startLine = sourceFile.getLineAndCharacterOfPosition(start).line + 1;
  const endLine = sourceFile.getLineAndCharacterOfPosition(Math.max(start, end)).line + 1;
  return { start: startLine, end: endLine };
}

/** Read a static member name; dynamic computed names return an empty string. */
export function classMemberName(ts, name) {
  if (!name) return "";
  if (ts.isIdentifier(name) || ts.isPrivateIdentifier?.(name)) return name.text;
  if (ts.isStringLiteralLike?.(name) || ts.isNumericLiteral(name)) return name.text;
  return "";
}

/** Supplement isExpressionNode on compiler versions with narrower detection. */
function isExpressionLike(ts, node) {
  return (
    ts.isIdentifier(node) ||
    ts.isPropertyAccessExpression(node) ||
    ts.isElementAccessExpression(node) ||
    ts.isCallExpression(node) ||
    ts.isNewExpression(node) ||
    ts.isAwaitExpression?.(node) ||
    ts.isBinaryExpression(node) ||
    ts.isConditionalExpression(node) ||
    ts.isObjectLiteralExpression(node) ||
    ts.isArrayLiteralExpression(node)
  );
}

/** Return the earliest child start that should not be owned by the outer span. */
function firstSpanCutStart(ts, sourceFile, node) {
  const starts = [
    firstControlBodyStart(ts, sourceFile, node),
    firstNestedUnitStart(ts, sourceFile, node),
  ].filter((value) => value !== null);
  return starts.length ? Math.min(...starts) : null;
}

/** Find the control-body boundary so the header retains only its own lines.
 * Body statements are analyzed under control_origin.
 */
function firstControlBodyStart(ts, sourceFile, node) {
  if (ts.isIfStatement(node)) return node.thenStatement.getStart(sourceFile);
  if (
    ts.isWhileStatement(node) ||
    ts.isForStatement(node) ||
    ts.isForOfStatement?.(node) ||
    ts.isForInStatement?.(node)
  ) {
    return node.statement.getStart(sourceFile);
  }
  if (ts.isSwitchStatement(node)) return node.caseBlock.getStart(sourceFile);
  return null;
}

/** Return the first nested function/class start position inside a node. */
function firstNestedUnitStart(ts, sourceFile, node) {
  let first = null;
  function visit(child) {
    if (child !== node && isNestedUnit(ts, child)) {
      const start = child.getStart(sourceFile);
      first = first === null ? start : Math.min(first, start);
      return;
    }
    ts.forEachChild(child, visit);
  }
  ts.forEachChild(node, visit);
  return first;
}
